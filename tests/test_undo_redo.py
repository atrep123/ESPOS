"""Tests for shared_undo_redo — UndoRedoManager, CollaborativeUndoRedo,
OperationBuilder, and Operation serialization."""

import json

from shared_undo_redo import (
    CollaborativeUndoRedo,
    Operation,
    OperationBuilder,
    OperationType,
    UndoRedoManager,
)

# ---------------------------------------------------------------------------
# Operation dataclass
# ---------------------------------------------------------------------------


def test_operation_to_dict_and_back():
    op = OperationBuilder.add_widget("w1", "button", 10, 20, 80, 30, text="Go")
    op.user_id = "u1"
    d = op.to_dict()
    assert d["type"] == "add_widget"
    assert d["widget_id"] == "w1"
    restored = Operation.from_dict(d)
    assert restored.type == OperationType.ADD_WIDGET
    assert restored.data["text"] == "Go"


def test_operation_type_enum_values():
    assert OperationType.MOVE_WIDGET.value == "move_widget"
    assert OperationType.RESIZE_WIDGET.value == "resize_widget"
    assert OperationType.MODIFY_PROPERTY.value == "modify_property"


# ---------------------------------------------------------------------------
# OperationBuilder
# ---------------------------------------------------------------------------


def test_builder_add_widget():
    op = OperationBuilder.add_widget("b1", "label", 0, 0, 50, 14, text="HI")
    assert op.type == OperationType.ADD_WIDGET
    assert op.data["type"] == "label"
    assert op.data["text"] == "HI"


def test_builder_delete_widget():
    op = OperationBuilder.delete_widget("b1", {"x": 10})
    assert op.type == OperationType.DELETE_WIDGET
    assert op.data["state"]["x"] == 10


def test_builder_move_widget():
    op = OperationBuilder.move_widget("b1", 0, 0, 50, 60)
    assert op.data["old_x"] == 0
    assert op.data["x"] == 50
    assert op.data["y"] == 60


def test_builder_resize_widget():
    op = OperationBuilder.resize_widget("b1", 40, 20, 80, 30)
    assert op.data["old_width"] == 40
    assert op.data["width"] == 80


def test_builder_modify_property():
    op = OperationBuilder.modify_property("b1", "color", "red", "blue")
    assert op.data["property"] == "color"
    assert op.data["old_value"] == "red"
    assert op.data["new_value"] == "blue"


def test_builder_group_widgets():
    op = OperationBuilder.group_widgets("g1", ["w1", "w2", "w3"])
    assert op.type == OperationType.GROUP_WIDGETS
    assert op.data["widget_ids"] == ["w1", "w2", "w3"]


# ---------------------------------------------------------------------------
# UndoRedoManager — basic undo/redo
# ---------------------------------------------------------------------------


def test_initial_state():
    mgr = UndoRedoManager()
    assert not mgr.can_undo()
    assert not mgr.can_redo()
    assert mgr.undo() is None
    assert mgr.redo() is None


def test_execute_and_undo():
    mgr = UndoRedoManager()
    op = OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10)
    mgr.execute(op)
    assert mgr.can_undo()
    assert not mgr.can_redo()
    undone = mgr.undo()
    assert undone is op
    assert not mgr.can_undo()
    assert mgr.can_redo()


def test_redo_after_undo():
    mgr = UndoRedoManager()
    op = OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10)
    mgr.execute(op)
    mgr.undo()
    redone = mgr.redo()
    assert redone is op
    assert mgr.can_undo()
    assert not mgr.can_redo()


def test_undo_redo_sequence():
    mgr = UndoRedoManager()
    ops = [
        OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10),
        OperationBuilder.move_widget("w1", 0, 0, 50, 50),
        OperationBuilder.resize_widget("w1", 10, 10, 40, 40),
    ]
    for op in ops:
        mgr.execute(op)
    assert len(mgr.get_history()) == 3

    # Undo all
    for _ in range(3):
        assert mgr.can_undo()
        mgr.undo()
    assert not mgr.can_undo()

    # Redo all
    for _ in range(3):
        assert mgr.can_redo()
        mgr.redo()
    assert not mgr.can_redo()


def test_new_execute_discards_redo_stack():
    mgr = UndoRedoManager()
    mgr.execute(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
    mgr.execute(OperationBuilder.move_widget("w1", 0, 0, 20, 20))
    mgr.undo()  # undo move
    assert mgr.can_redo()
    # New operation discards the redo branch
    mgr.execute(OperationBuilder.resize_widget("w1", 10, 10, 30, 30))
    assert not mgr.can_redo()
    assert len(mgr.operations) == 2  # add + resize (move discarded)


# ---------------------------------------------------------------------------
# UndoRedoManager — max_history trimming
# ---------------------------------------------------------------------------


def test_max_history_trims_oldest():
    mgr = UndoRedoManager(max_history=5)
    for i in range(10):
        mgr.execute(OperationBuilder.add_widget(f"w{i}", "box", i, 0, 10, 10))
    assert len(mgr.operations) == 5
    # Oldest operations were trimmed
    assert mgr.operations[0].widget_id == "w5"


# ---------------------------------------------------------------------------
# UndoRedoManager — callbacks
# ---------------------------------------------------------------------------


def test_callbacks_fire():
    mgr = UndoRedoManager()
    log = []
    mgr.on_operation = lambda op: log.append(("exec", op.widget_id))
    mgr.on_undo = lambda op: log.append(("undo", op.widget_id))
    mgr.on_redo = lambda op: log.append(("redo", op.widget_id))
    op = OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10)
    mgr.execute(op)
    mgr.undo()
    mgr.redo()
    assert log == [("exec", "w1"), ("undo", "w1"), ("redo", "w1")]


# ---------------------------------------------------------------------------
# UndoRedoManager — clear
# ---------------------------------------------------------------------------


def test_clear_resets():
    mgr = UndoRedoManager()
    mgr.execute(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
    mgr.clear()
    assert not mgr.can_undo()
    assert not mgr.can_redo()
    assert mgr.operations == []
    assert mgr.version == 0


# ---------------------------------------------------------------------------
# UndoRedoManager — save/load state
# ---------------------------------------------------------------------------


def test_save_and_load_state(tmp_path):
    mgr = UndoRedoManager(user_id="u1")
    mgr.execute(OperationBuilder.add_widget("w1", "button", 0, 0, 80, 30))
    mgr.execute(OperationBuilder.move_widget("w1", 0, 0, 50, 50))
    path = str(tmp_path / "history.json")
    mgr.save_state(path)

    mgr2 = UndoRedoManager()
    mgr2.load_state(path)
    assert len(mgr2.operations) == 2
    assert mgr2.operations[0].type == OperationType.ADD_WIDGET
    assert mgr2.operations[1].type == OperationType.MOVE_WIDGET
    assert mgr2.current_index == mgr.current_index
    assert mgr2.version == mgr.version


def test_saved_state_is_valid_json(tmp_path):
    mgr = UndoRedoManager()
    mgr.execute(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
    path = str(tmp_path / "h.json")
    mgr.save_state(path)
    with open(path) as f:
        data = json.load(f)
    assert "operations" in data
    assert "current_index" in data
    assert data["current_index"] == 0


# ---------------------------------------------------------------------------
# UndoRedoManager — get_operation_description
# ---------------------------------------------------------------------------


def test_operation_descriptions():
    mgr = UndoRedoManager()
    cases = [
        (OperationBuilder.add_widget("w1", "button", 0, 0, 10, 10), "Add button"),
        (OperationBuilder.delete_widget("w1", {}), "Delete widget w1"),
        (OperationBuilder.move_widget("w1", 0, 0, 5, 5), "Move widget to (5, 5)"),
        (OperationBuilder.resize_widget("w1", 10, 10, 20, 20), "Resize to 20x20"),
        (OperationBuilder.modify_property("w1", "color", "a", "b"), "Change color to b"),
        (OperationBuilder.group_widgets("g1", ["a", "b"]), "Group 2 widgets"),
    ]
    for op, expected in cases:
        desc = mgr.get_operation_description(op)
        assert desc == expected, f"got '{desc}' expected '{expected}'"


# ---------------------------------------------------------------------------
# UndoRedoManager — version tracking
# ---------------------------------------------------------------------------


def test_version_increments():
    mgr = UndoRedoManager()
    assert mgr.version == 0
    mgr.execute(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
    assert mgr.version == 1
    mgr.execute(OperationBuilder.add_widget("w2", "box", 0, 0, 10, 10))
    assert mgr.version == 2


def test_operation_gets_version_metadata():
    mgr = UndoRedoManager(user_id="test_user")
    op = OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10)
    mgr.execute(op)
    assert op.version == 0
    assert op.parent_version == -1
    assert op.user_id == "test_user"
    assert op.session_id == mgr.session_id


# ---------------------------------------------------------------------------
# CollaborativeUndoRedo
# ---------------------------------------------------------------------------


def test_collaborative_execute_local():
    collab = CollaborativeUndoRedo(user_id="u1")
    op = OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10)
    assert collab.execute_local(op)
    assert collab.local_manager.can_undo()


def test_collaborative_broadcast_callback():
    collab = CollaborativeUndoRedo(user_id="u1")
    broadcast_log = []
    collab.on_broadcast = lambda op: broadcast_log.append(op.widget_id)
    collab.execute_local(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
    assert broadcast_log == ["w1"]


def test_collaborative_receive_remote():
    collab = CollaborativeUndoRedo(user_id="u1")
    remote_op = OperationBuilder.add_widget("w2", "label", 0, 0, 40, 14)
    remote_op.user_id = "u2"
    remote_op.timestamp = 1000.0
    result = collab.receive_remote(remote_op)
    assert result.widget_id == "w2"
    assert "u2" in collab.remote_operations


def test_collaborative_get_all_operations():
    collab = CollaborativeUndoRedo(user_id="u1")
    collab.execute_local(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
    remote_op = OperationBuilder.add_widget("w2", "label", 0, 0, 40, 14)
    remote_op.user_id = "u2"
    remote_op.timestamp = 1.0  # earlier than local op
    collab.receive_remote(remote_op)
    all_ops = collab.get_all_operations()
    assert len(all_ops) == 2
    # Sorted by timestamp — remote (1.0) first, local (now) last
    assert all_ops[0].widget_id == "w2"
    assert all_ops[-1].widget_id == "w1"


def test_collaborative_merge_history():
    collab = CollaborativeUndoRedo(user_id="u1")
    remote_ops = []
    for i in range(3):
        op = OperationBuilder.add_widget(f"r{i}", "box", i * 20, 0, 10, 10)
        op.user_id = "u2"
        op.timestamp = float(1000 + i)
        remote_ops.append(op)
    collab.merge_history(remote_ops)
    assert len(collab.remote_operations.get("u2", [])) == 3
