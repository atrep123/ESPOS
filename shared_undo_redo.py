# Shared Undo/Redo System for Collaborative Editing
#
# Features:
# - Operation-based undo/redo
# - Collaborative history synchronization
# - Conflict-free concurrent edits (OT-inspired)
# - History persistence and replay

import copy
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class OperationType(Enum):
    """Types of operations that can be undone/redone"""

    ADD_WIDGET = "add_widget"
    DELETE_WIDGET = "delete_widget"
    MOVE_WIDGET = "move_widget"
    RESIZE_WIDGET = "resize_widget"
    MODIFY_PROPERTY = "modify_property"
    REORDER_WIDGET = "reorder_widget"
    GROUP_WIDGETS = "group_widgets"
    UNGROUP_WIDGETS = "ungroup_widgets"


@dataclass
class Operation:
    """Represents a single undoable operation"""

    type: OperationType
    timestamp: float
    user_id: str
    widget_id: str
    data: Dict[str, Any]
    session_id: str = ""

    # For collaborative sync
    version: int = 0
    parent_version: int = -1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result["type"] = self.type.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Operation":
        """Create from dictionary"""
        data_copy = data.copy()
        data_copy["type"] = OperationType(data_copy["type"])
        return cls(**data_copy)


@dataclass
class HistoryState:
    """Complete history state for persistence"""

    operations: List[Dict[str, Any]] = field(default_factory=list)
    current_index: int = -1
    session_id: str = ""
    version: int = 0


class UndoRedoManager:
    """Manages undo/redo operations"""

    def __init__(self, max_history: int = 50, user_id: str = "local"):
        self.max_history = max_history
        self.user_id = user_id
        self.session_id = datetime.now().isoformat()

        # History stack
        self.operations: List[Operation] = []
        self.current_index = -1

        # Version tracking for collaborative sync
        self.version = 0

        # Callbacks
        self.on_operation: Optional[Callable[[Operation], None]] = None
        self.on_undo: Optional[Callable[[Operation], None]] = None
        self.on_redo: Optional[Callable[[Operation], None]] = None

    def execute(self, op: Operation) -> bool:
        """Execute and record an operation"""
        # Discard any operations after current index (new branch)
        self.operations = self.operations[: self.current_index + 1]

        # Set operation metadata
        op.timestamp = datetime.now().timestamp()
        op.user_id = self.user_id
        op.session_id = self.session_id
        op.version = self.version
        op.parent_version = self.version - 1 if self.version > 0 else -1

        # Add to history
        self.operations.append(op)
        self.current_index += 1
        self.version += 1

        # Trim history if needed
        if len(self.operations) > self.max_history:
            remove_count = len(self.operations) - self.max_history
            self.operations = self.operations[remove_count:]
            self.current_index -= remove_count

        # Notify callback
        if self.on_operation:
            self.on_operation(op)

        return True

    def can_undo(self) -> bool:
        """Check if undo is available"""
        return self.current_index >= 0

    def can_redo(self) -> bool:
        """Check if redo is available"""
        return self.current_index < len(self.operations) - 1

    def undo(self) -> Optional[Operation]:
        """Undo last operation"""
        if not self.can_undo():
            return None

        op = self.operations[self.current_index]
        self.current_index -= 1

        # Notify callback
        if self.on_undo:
            self.on_undo(op)

        return op

    def redo(self) -> Optional[Operation]:
        """Redo next operation"""
        if not self.can_redo():
            return None

        self.current_index += 1
        op = self.operations[self.current_index]

        # Notify callback
        if self.on_redo:
            self.on_redo(op)

        return op

    def get_history(self) -> List[Operation]:
        """Get all operations up to current index"""
        return self.operations[: self.current_index + 1]

    def clear(self):
        """Clear all history"""
        self.operations = []
        self.current_index = -1
        self.version = 0

    def save_state(self, path: str):
        """Save history state to file"""
        state = HistoryState(
            operations=[op.to_dict() for op in self.operations],
            current_index=self.current_index,
            session_id=self.session_id,
            version=self.version,
        )

        with open(path, "w") as f:
            json.dump(asdict(state), f, indent=2)

    def load_state(self, path: str):
        """Load history state from file"""
        with open(path) as f:
            data = json.load(f)

        state = HistoryState(**data)
        self.operations = [Operation.from_dict(op) for op in state.operations]
        self.current_index = state.current_index
        self.session_id = state.session_id
        self.version = state.version

    def get_operation_description(self, op: Operation) -> str:
        """Get human-readable operation description"""
        descriptions = {
            OperationType.ADD_WIDGET: f"Add {op.data.get('type', 'widget')}",
            OperationType.DELETE_WIDGET: f"Delete widget {op.widget_id}",
            OperationType.MOVE_WIDGET: f"Move widget to ({op.data.get('x')}, {op.data.get('y')})",
            OperationType.RESIZE_WIDGET: f"Resize to {op.data.get('width')}x{op.data.get('height')}",
            OperationType.MODIFY_PROPERTY: f"Change {op.data.get('property')} to {op.data.get('new_value')}",
            OperationType.REORDER_WIDGET: f"Reorder to z-index {op.data.get('new_index')}",
            OperationType.GROUP_WIDGETS: f"Group {len(op.data.get('widget_ids', []))} widgets",
            OperationType.UNGROUP_WIDGETS: "Ungroup widgets",
        }
        return descriptions.get(op.type, str(op.type))


class CollaborativeUndoRedo:
    """Collaborative undo/redo with conflict resolution"""

    def __init__(self, user_id: str, max_history: int = 50):
        self.local_manager = UndoRedoManager(max_history, user_id)
        self.remote_operations: Dict[str, List[Operation]] = {}  # user_id -> operations

        # Callbacks for sync
        self.on_broadcast: Optional[Callable[[Operation], None]] = None

    def execute_local(self, op: Operation) -> bool:
        """Execute local operation and broadcast"""
        success = self.local_manager.execute(op)

        if success and self.on_broadcast:
            # Broadcast to other users
            self.on_broadcast(op)

        return success

    def receive_remote(self, op: Operation):
        """Receive operation from remote user"""
        # Store in remote operations
        if op.user_id not in self.remote_operations:
            self.remote_operations[op.user_id] = []

        self.remote_operations[op.user_id].append(op)

        # Transform against local operations if needed
        transformed_op = self._transform(op)

        # Apply transformed operation
        return transformed_op

    def _transform(self, remote_op: Operation) -> Operation:
        """Transform remote operation against local operations (OT-inspired)"""
        # Get concurrent local operations
        local_ops = [
            op
            for op in self.local_manager.get_history()
            if op.timestamp > remote_op.timestamp and op.user_id == self.local_manager.user_id
        ]

        if not local_ops:
            return remote_op

        # Simple transformation rules
        transformed = copy.deepcopy(remote_op)

        for local_op in local_ops:
            if local_op.widget_id == remote_op.widget_id:
                # Same widget - resolve conflict
                if (
                    remote_op.type == OperationType.MOVE_WIDGET
                    and local_op.type == OperationType.MOVE_WIDGET
                ):
                    # Both moved - prefer remote (last writer wins)
                    pass
                elif remote_op.type == OperationType.DELETE_WIDGET:
                    # Remote deleted - discard local moves/resizes
                    transformed.data["deleted"] = True
                elif local_op.type == OperationType.DELETE_WIDGET:
                    # Local deleted - mark remote as no-op
                    transformed.data["no_op"] = True

        return transformed

    def merge_history(self, remote_history: List[Operation]):
        """Merge remote history with local history"""
        for op in remote_history:
            if op.user_id != self.local_manager.user_id:
                self.receive_remote(op)

    def get_all_operations(self) -> List[Operation]:
        """Get all operations (local + remote) sorted by timestamp"""
        all_ops = self.local_manager.get_history()

        for user_ops in self.remote_operations.values():
            all_ops.extend(user_ops)

        return sorted(all_ops, key=lambda op: op.timestamp)


class OperationBuilder:
    """Helper to build common operations"""

    @staticmethod
    def add_widget(
        widget_id: str, widget_type: str, x: int, y: int, width: int, height: int, **kwargs
    ) -> Operation:
        """Create add widget operation"""
        return Operation(
            type=OperationType.ADD_WIDGET,
            timestamp=0,  # Will be set by manager
            user_id="",
            widget_id=widget_id,
            data={"type": widget_type, "x": x, "y": y, "width": width, "height": height, **kwargs},
        )

    @staticmethod
    def delete_widget(widget_id: str, widget_state: Dict[str, Any]) -> Operation:
        """Create delete widget operation"""
        return Operation(
            type=OperationType.DELETE_WIDGET,
            timestamp=0,
            user_id="",
            widget_id=widget_id,
            data={"state": widget_state},  # Save state for undo
        )

    @staticmethod
    def move_widget(widget_id: str, old_x: int, old_y: int, new_x: int, new_y: int) -> Operation:
        """Create move widget operation"""
        return Operation(
            type=OperationType.MOVE_WIDGET,
            timestamp=0,
            user_id="",
            widget_id=widget_id,
            data={"old_x": old_x, "old_y": old_y, "x": new_x, "y": new_y},
        )

    @staticmethod
    def resize_widget(
        widget_id: str, old_width: int, old_height: int, new_width: int, new_height: int
    ) -> Operation:
        """Create resize widget operation"""
        return Operation(
            type=OperationType.RESIZE_WIDGET,
            timestamp=0,
            user_id="",
            widget_id=widget_id,
            data={
                "old_width": old_width,
                "old_height": old_height,
                "width": new_width,
                "height": new_height,
            },
        )

    @staticmethod
    def modify_property(
        widget_id: str, property_name: str, old_value: Any, new_value: Any
    ) -> Operation:
        """Create modify property operation"""
        return Operation(
            type=OperationType.MODIFY_PROPERTY,
            timestamp=0,
            user_id="",
            widget_id=widget_id,
            data={"property": property_name, "old_value": old_value, "new_value": new_value},
        )

    @staticmethod
    def group_widgets(group_id: str, widget_ids: List[str]) -> Operation:
        """Create group widgets operation"""
        return Operation(
            type=OperationType.GROUP_WIDGETS,
            timestamp=0,
            user_id="",
            widget_id=group_id,
            data={"widget_ids": widget_ids},
        )


def demo():
    """Demo of undo/redo system"""
    # Create manager
    manager = UndoRedoManager(user_id="user1")

    # Track operations
    def on_op(op):
        print(f"✓ {manager.get_operation_description(op)}")

    def on_undo(op):
        print(f"⟲ Undo: {manager.get_operation_description(op)}")

    def on_redo(op):
        print(f"⟳ Redo: {manager.get_operation_description(op)}")

    manager.on_operation = on_op
    manager.on_undo = on_undo
    manager.on_redo = on_redo

    # Execute operations
    print("=== Executing Operations ===")
    manager.execute(OperationBuilder.add_widget("btn1", "button", 10, 20, 100, 30, text="Click me"))
    manager.execute(OperationBuilder.add_widget("lbl1", "label", 50, 60, 80, 20, text="Hello"))
    manager.execute(OperationBuilder.move_widget("btn1", 10, 20, 30, 40))
    manager.execute(OperationBuilder.modify_property("btn1", "text", "Click me", "Press here"))

    print(f"\nHistory: {len(manager.operations)} operations")
    print(f"Can undo: {manager.can_undo()}, Can redo: {manager.can_redo()}")

    # Undo
    print("\n=== Undo ===")
    manager.undo()
    manager.undo()

    print(f"Can undo: {manager.can_undo()}, Can redo: {manager.can_redo()}")

    # Redo
    print("\n=== Redo ===")
    manager.redo()

    # Save state
    print("\n=== Save State ===")
    manager.save_state("undo_history.json")
    print("Saved to undo_history.json")

    # Collaborative demo
    print("\n=== Collaborative Undo/Redo ===")
    collab = CollaborativeUndoRedo("user2")

    def broadcast(op):
        print(f"→ Broadcast: {collab.local_manager.get_operation_description(op)}")

    collab.on_broadcast = broadcast

    collab.execute_local(OperationBuilder.add_widget("btn2", "button", 100, 100, 120, 40))

    # Simulate receiving remote operation
    remote_op = OperationBuilder.move_widget("btn2", 100, 100, 150, 150)
    remote_op.user_id = "user3"
    remote_op.timestamp = datetime.now().timestamp()

    transformed = collab.receive_remote(remote_op)
    print(f"← Received from user3: {collab.local_manager.get_operation_description(transformed)}")


if __name__ == "__main__":
    demo()
