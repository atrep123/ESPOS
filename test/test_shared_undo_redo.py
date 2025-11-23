"""Tests for shared_undo_redo.py - collaborative undo/redo system"""

import os
import tempfile
from datetime import datetime

import pytest

from shared_undo_redo import (
    CollaborativeUndoRedo,
    Operation,
    OperationBuilder,
    OperationType,
    UndoRedoManager,
)


class TestOperation:
    """Test Operation dataclass"""
    
    def test_operation_creation(self):
        """Test creating an operation"""
        op = Operation(
            type=OperationType.ADD_WIDGET,
            timestamp=datetime.now().timestamp(),
            user_id="user1",
            widget_id="btn1",
            data={'type': 'button', 'x': 10, 'y': 20}
        )
        
        assert op.type == OperationType.ADD_WIDGET
        assert op.user_id == "user1"
        assert op.widget_id == "btn1"
        assert op.data['x'] == 10
    
    def test_operation_serialization(self):
        """Test operation to/from dict"""
        op = Operation(
            type=OperationType.MOVE_WIDGET,
            timestamp=123.456,
            user_id="user2",
            widget_id="lbl1",
            data={'x': 100, 'y': 200}
        )
        
        # To dict
        d = op.to_dict()
        assert d['type'] == 'move_widget'
        assert d['user_id'] == 'user2'
        
        # From dict
        op2 = Operation.from_dict(d)
        assert op2.type == OperationType.MOVE_WIDGET
        assert op2.user_id == "user2"
        assert op2.data['x'] == 100


class TestUndoRedoManager:
    """Test UndoRedoManager"""
    
    def test_manager_init(self):
        """Test manager initialization"""
        manager = UndoRedoManager(max_history=20, user_id="test_user")
        assert manager.max_history == 20
        assert manager.user_id == "test_user"
        assert len(manager.operations) == 0
        assert manager.current_index == -1
    
    def test_execute_operation(self):
        """Test executing an operation"""
        manager = UndoRedoManager(user_id="user1")
        
        op = OperationBuilder.add_widget("btn1", "button", 10, 20, 100, 30)
        result = manager.execute(op)
        
        assert result is True
        assert len(manager.operations) == 1
        assert manager.current_index == 0
        assert manager.version == 1
    
    def test_can_undo_redo(self):
        """Test undo/redo availability"""
        manager = UndoRedoManager()
        
        # Initially can't undo or redo
        assert manager.can_undo() is False
        assert manager.can_redo() is False
        
        # Add operation
        manager.execute(OperationBuilder.add_widget("w1", "label", 0, 0, 50, 20))
        
        assert manager.can_undo() is True
        assert manager.can_redo() is False
        
        # Undo
        manager.undo()
        assert manager.can_undo() is False
        assert manager.can_redo() is True
    
    def test_undo(self):
        """Test undo operation"""
        manager = UndoRedoManager()
        undone_ops = []
        
        manager.on_undo = lambda op: undone_ops.append(op)
        
        # Execute two operations
        op1 = OperationBuilder.add_widget("w1", "button", 10, 10, 50, 30)
        op2 = OperationBuilder.move_widget("w1", 10, 10, 20, 20)
        manager.execute(op1)
        manager.execute(op2)
        
        # Undo last operation
        result = manager.undo()
        assert result is not None
        assert result.type == OperationType.MOVE_WIDGET
        assert len(undone_ops) == 1
        assert manager.current_index == 0
    
    def test_redo(self):
        """Test redo operation"""
        manager = UndoRedoManager()
        redone_ops = []
        
        manager.on_redo = lambda op: redone_ops.append(op)
        
        # Execute and undo
        manager.execute(OperationBuilder.add_widget("w1", "label", 5, 5, 40, 15))
        manager.undo()
        
        # Redo
        result = manager.redo()
        assert result is not None
        assert result.type == OperationType.ADD_WIDGET
        assert len(redone_ops) == 1
        assert manager.current_index == 0
    
    def test_new_branch_after_undo(self):
        """Test that new operations create a new branch"""
        manager = UndoRedoManager()
        
        # Execute three operations
        manager.execute(OperationBuilder.add_widget("w1", "button", 0, 0, 50, 20))
        manager.execute(OperationBuilder.move_widget("w1", 0, 0, 10, 10))
        manager.execute(OperationBuilder.resize_widget("w1", 50, 20, 60, 25))
        
        assert len(manager.operations) == 3
        
        # Undo twice
        manager.undo()
        manager.undo()
        
        # Execute new operation - should discard future operations
        manager.execute(OperationBuilder.delete_widget("w1", {'type': 'button'}))
        
        assert len(manager.operations) == 2
        assert manager.operations[1].type == OperationType.DELETE_WIDGET
    
    def test_max_history_limit(self):
        """Test history size limit"""
        manager = UndoRedoManager(max_history=3)
        
        # Add 5 operations
        for i in range(5):
            manager.execute(OperationBuilder.add_widget(f"w{i}", "label", i*10, i*10, 50, 20))
        
        # Should only keep last 3
        assert len(manager.operations) == 3
        assert manager.operations[0].widget_id == "w2"
        assert manager.operations[2].widget_id == "w4"
    
    def test_get_history(self):
        """Test getting operation history"""
        manager = UndoRedoManager()
        
        # Execute operations
        manager.execute(OperationBuilder.add_widget("w1", "button", 0, 0, 50, 20))
        manager.execute(OperationBuilder.add_widget("w2", "label", 10, 10, 60, 15))
        manager.execute(OperationBuilder.move_widget("w1", 0, 0, 5, 5))
        
        # Undo one
        manager.undo()
        
        # Get history (should be 2 operations)
        history = manager.get_history()
        assert len(history) == 2
        assert history[0].widget_id == "w1"
        assert history[1].widget_id == "w2"
    
    def test_clear(self):
        """Test clearing history"""
        manager = UndoRedoManager()
        
        manager.execute(OperationBuilder.add_widget("w1", "button", 0, 0, 50, 20))
        manager.execute(OperationBuilder.move_widget("w1", 0, 0, 10, 10))
        
        manager.clear()
        
        assert len(manager.operations) == 0
        assert manager.current_index == -1
        assert manager.version == 0
    
    def test_operation_callback(self):
        """Test operation execution callback"""
        manager = UndoRedoManager()
        executed_ops = []
        
        manager.on_operation = lambda op: executed_ops.append(op)
        
        manager.execute(OperationBuilder.add_widget("w1", "button", 0, 0, 50, 20))
        manager.execute(OperationBuilder.move_widget("w1", 0, 0, 10, 10))
        
        assert len(executed_ops) == 2
        assert executed_ops[0].type == OperationType.ADD_WIDGET
        assert executed_ops[1].type == OperationType.MOVE_WIDGET
    
    def test_operation_descriptions(self):
        """Test human-readable operation descriptions"""
        manager = UndoRedoManager()
        
        ops = [
            OperationBuilder.add_widget("w1", "button", 0, 0, 50, 20),
            OperationBuilder.delete_widget("w1", {}),
            OperationBuilder.move_widget("w2", 0, 0, 10, 20),
            OperationBuilder.resize_widget("w2", 50, 20, 60, 25),
            OperationBuilder.modify_property("w2", "text", "old", "new"),
            OperationBuilder.group_widgets("g1", ["w1", "w2", "w3"])
        ]
        
        for op in ops:
            desc = manager.get_operation_description(op)
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestPersistence:
    """Test history persistence"""
    
    def test_save_and_load_state(self):
        """Test saving and loading history state"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # Create manager and execute operations
            manager = UndoRedoManager(user_id="test_user")
            manager.execute(OperationBuilder.add_widget("w1", "button", 10, 20, 50, 30))
            manager.execute(OperationBuilder.move_widget("w1", 10, 20, 30, 40))
            manager.undo()
            
            # Save state
            manager.save_state(temp_path)
            
            # Load in new manager
            manager2 = UndoRedoManager()
            manager2.load_state(temp_path)
            
            # Verify
            assert len(manager2.operations) == 2
            assert manager2.current_index == 0
            assert manager2.operations[0].widget_id == "w1"
            assert manager2.operations[0].type == OperationType.ADD_WIDGET
        finally:
            os.unlink(temp_path)


class TestCollaborativeUndoRedo:
    """Test collaborative undo/redo"""
    
    def test_collaborative_init(self):
        """Test collaborative manager initialization"""
        collab = CollaborativeUndoRedo("user1")
        assert collab.local_manager.user_id == "user1"
        assert len(collab.remote_operations) == 0
    
    def test_execute_local(self):
        """Test executing local operation"""
        collab = CollaborativeUndoRedo("user1")
        broadcasts = []
        
        collab.on_broadcast = lambda op: broadcasts.append(op)
        
        op = OperationBuilder.add_widget("w1", "button", 0, 0, 50, 20)
        result = collab.execute_local(op)
        
        assert result is True
        assert len(collab.local_manager.operations) == 1
        assert len(broadcasts) == 1
    
    def test_receive_remote_operation(self):
        """Test receiving remote operation"""
        collab = CollaborativeUndoRedo("user1")
        
        # Create remote operation
        remote_op = OperationBuilder.add_widget("w2", "label", 10, 10, 60, 20)
        remote_op.user_id = "user2"
        remote_op.timestamp = datetime.now().timestamp()
        
        # Receive
        transformed = collab.receive_remote(remote_op)
        
        assert transformed is not None
        assert "user2" in collab.remote_operations
        assert len(collab.remote_operations["user2"]) == 1
    
    def test_transform_concurrent_move(self):
        """Test transformation of concurrent move operations"""
        collab = CollaborativeUndoRedo("user1")
        
        # Local moves widget
        local_op = OperationBuilder.move_widget("w1", 0, 0, 10, 10)
        collab.execute_local(local_op)
        
        # Remote also moves same widget (later timestamp)
        remote_op = OperationBuilder.move_widget("w1", 0, 0, 20, 20)
        remote_op.user_id = "user2"
        remote_op.timestamp = datetime.now().timestamp() + 1
        
        # Transform (should prefer remote - last writer wins)
        transformed = collab.receive_remote(remote_op)
        assert transformed.data['x'] == 20
        assert transformed.data['y'] == 20
    
    def test_transform_delete_conflict(self):
        """Test transformation when widget is deleted"""
        collab = CollaborativeUndoRedo("user1")
        
        # Local deletes widget
        local_op = OperationBuilder.delete_widget("w1", {})
        collab.execute_local(local_op)
        
        # Remote tries to move deleted widget
        remote_op = OperationBuilder.move_widget("w1", 0, 0, 10, 10)
        remote_op.user_id = "user2"
        remote_op.timestamp = datetime.now().timestamp() - 1  # Before delete
        
        # Transform (should mark as no-op)
        transformed = collab.receive_remote(remote_op)
        assert transformed.data.get('no_op') is True
    
    def test_merge_history(self):
        """Test merging remote history"""
        collab = CollaborativeUndoRedo("user1")
        
        # Local operations
        collab.execute_local(OperationBuilder.add_widget("w1", "button", 0, 0, 50, 20))
        
        # Remote history
        remote_ops = [
            OperationBuilder.add_widget("w2", "label", 10, 10, 60, 15),
            OperationBuilder.move_widget("w2", 10, 10, 20, 20)
        ]
        for op in remote_ops:
            op.user_id = "user2"
            op.timestamp = datetime.now().timestamp()
        
        # Merge
        collab.merge_history(remote_ops)
        
        # Check remote operations stored
        assert "user2" in collab.remote_operations
        assert len(collab.remote_operations["user2"]) == 2
    
    def test_get_all_operations_sorted(self):
        """Test getting all operations sorted by timestamp"""
        collab = CollaborativeUndoRedo("user1")
        
        import time
        
        # Local operation at t0
        op1 = OperationBuilder.add_widget("w1", "button", 0, 0, 50, 20)
        collab.execute_local(op1)
        
        time.sleep(0.01)
        
        # Remote operation at t1
        op2 = OperationBuilder.add_widget("w2", "label", 10, 10, 60, 15)
        op2.user_id = "user2"
        op2.timestamp = datetime.now().timestamp()
        collab.receive_remote(op2)
        
        time.sleep(0.01)
        
        # Another local at t2
        op3 = OperationBuilder.move_widget("w1", 0, 0, 5, 5)
        collab.execute_local(op3)
        
        # Get all sorted
        all_ops = collab.get_all_operations()
        assert len(all_ops) == 3
        # Should be sorted by timestamp
        assert all_ops[0].timestamp <= all_ops[1].timestamp <= all_ops[2].timestamp


class TestOperationBuilder:
    """Test OperationBuilder helpers"""
    
    def test_build_add_widget(self):
        """Test building add widget operation"""
        op = OperationBuilder.add_widget("btn1", "button", 10, 20, 100, 30, text="Click")
        
        assert op.type == OperationType.ADD_WIDGET
        assert op.widget_id == "btn1"
        assert op.data['type'] == "button"
        assert op.data['x'] == 10
        assert op.data['y'] == 20
        assert op.data['width'] == 100
        assert op.data['height'] == 30
        assert op.data['text'] == "Click"
    
    def test_build_delete_widget(self):
        """Test building delete widget operation"""
        state = {'type': 'button', 'x': 10, 'y': 20}
        op = OperationBuilder.delete_widget("btn1", state)
        
        assert op.type == OperationType.DELETE_WIDGET
        assert op.widget_id == "btn1"
        assert op.data['state'] == state
    
    def test_build_move_widget(self):
        """Test building move widget operation"""
        op = OperationBuilder.move_widget("w1", 10, 20, 30, 40)
        
        assert op.type == OperationType.MOVE_WIDGET
        assert op.data['old_x'] == 10
        assert op.data['old_y'] == 20
        assert op.data['x'] == 30
        assert op.data['y'] == 40
    
    def test_build_resize_widget(self):
        """Test building resize widget operation"""
        op = OperationBuilder.resize_widget("w1", 50, 20, 60, 25)
        
        assert op.type == OperationType.RESIZE_WIDGET
        assert op.data['old_width'] == 50
        assert op.data['old_height'] == 20
        assert op.data['width'] == 60
        assert op.data['height'] == 25
    
    def test_build_modify_property(self):
        """Test building modify property operation"""
        op = OperationBuilder.modify_property("btn1", "text", "Old", "New")
        
        assert op.type == OperationType.MODIFY_PROPERTY
        assert op.data['property'] == "text"
        assert op.data['old_value'] == "Old"
        assert op.data['new_value'] == "New"
    
    def test_build_group_widgets(self):
        """Test building group widgets operation"""
        op = OperationBuilder.group_widgets("g1", ["w1", "w2", "w3"])
        
        assert op.type == OperationType.GROUP_WIDGETS
        assert op.widget_id == "g1"
        assert op.data['widget_ids'] == ["w1", "w2", "w3"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
