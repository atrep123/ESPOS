"""Tests for CollaborativeUndoRedo._transform() conflict resolution and edge cases."""

from __future__ import annotations

import time

from shared_undo_redo import (
    CollaborativeUndoRedo,
    Operation,
    OperationBuilder,
    OperationType,
)


def _make_op(
    op_type: OperationType, widget_id: str, user_id: str, timestamp: float, **data_kw
) -> Operation:
    return Operation(
        type=op_type,
        timestamp=timestamp,
        user_id=user_id,
        widget_id=widget_id,
        data=data_kw,
    )


# ---------------------------------------------------------------------------
# _transform: no concurrent local ops  —  passthrough
# ---------------------------------------------------------------------------


class TestTransformPassthrough:
    def test_no_local_ops_returns_unchanged(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        remote = _make_op(OperationType.MOVE_WIDGET, "w1", "u2", 100.0, x=10, y=20)
        result = collab._transform(remote)
        assert result is remote  # exact same object, no deepcopy needed

    def test_local_ops_older_than_remote_are_not_concurrent(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        # Execute a local op that will get an older timestamp
        local_op = OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10)
        collab.execute_local(local_op)
        # Remote op with a much newer timestamp => no concurrent ops
        remote = _make_op(OperationType.MOVE_WIDGET, "w1", "u2", time.time() + 9999, x=50, y=50)
        result = collab._transform(remote)
        assert result is remote

    def test_different_widget_ids_no_conflict(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        local_op = OperationBuilder.move_widget("w1", 0, 0, 10, 10)
        collab.execute_local(local_op)
        # Remote op on *different* widget
        remote = _make_op(OperationType.MOVE_WIDGET, "w_other", "u2", 0.0, x=50, y=50)
        result = collab._transform(remote)
        # Even though local is concurrent, widget_id doesn't match
        assert "deleted" not in result.data
        assert "no_op" not in result.data


# ---------------------------------------------------------------------------
# _transform: MOVE vs MOVE  —  last writer wins (remote passes through)
# ---------------------------------------------------------------------------


class TestTransformMoveVsMove:
    def test_both_move_same_widget_remote_passes_through(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        local_op = OperationBuilder.move_widget("w1", 0, 0, 10, 10)
        collab.execute_local(local_op)
        remote = _make_op(OperationType.MOVE_WIDGET, "w1", "u2", 0.0, x=99, y=99)
        result = collab._transform(remote)
        # "last writer wins" — remote passes through unchanged
        assert result.data["x"] == 99
        assert result.data["y"] == 99
        assert "deleted" not in result.data
        assert "no_op" not in result.data

    def test_move_vs_move_result_is_deepcopy(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.move_widget("w1", 0, 0, 5, 5))
        remote = _make_op(OperationType.MOVE_WIDGET, "w1", "u2", 0.0, x=1, y=2)
        result = collab._transform(remote)
        assert result is not remote  # deepcopy since local_ops were found


# ---------------------------------------------------------------------------
# _transform: remote DELETE with concurrent local ops
# ---------------------------------------------------------------------------


class TestTransformRemoteDelete:
    def test_remote_delete_sets_deleted_flag(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.move_widget("w1", 0, 0, 10, 10))
        remote = _make_op(OperationType.DELETE_WIDGET, "w1", "u2", 0.0, state={"type": "box"})
        result = collab._transform(remote)
        assert result.data.get("deleted") is True

    def test_remote_delete_preserves_original_data(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.move_widget("w1", 0, 0, 10, 10))
        remote = _make_op(OperationType.DELETE_WIDGET, "w1", "u2", 0.0, state={"type": "label"})
        result = collab._transform(remote)
        assert result.data["state"] == {"type": "label"}
        assert result.data["deleted"] is True

    def test_remote_delete_different_widget_no_deleted_flag(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.move_widget("w1", 0, 0, 10, 10))
        remote = _make_op(OperationType.DELETE_WIDGET, "w_other", "u2", 0.0, state={})
        result = collab._transform(remote)
        assert "deleted" not in result.data


# ---------------------------------------------------------------------------
# _transform: local DELETE vs remote op
# ---------------------------------------------------------------------------


class TestTransformLocalDelete:
    def test_local_delete_marks_remote_no_op(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.delete_widget("w1", {"type": "box", "x": 0}))
        remote = _make_op(OperationType.MOVE_WIDGET, "w1", "u2", 0.0, x=50, y=50)
        result = collab._transform(remote)
        assert result.data.get("no_op") is True

    def test_local_delete_marks_remote_resize_no_op(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.delete_widget("w1", {"type": "box"}))
        remote = _make_op(OperationType.RESIZE_WIDGET, "w1", "u2", 0.0, width=100, height=200)
        result = collab._transform(remote)
        assert result.data.get("no_op") is True

    def test_local_delete_different_widget_no_no_op(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.delete_widget("w1", {"type": "box"}))
        remote = _make_op(OperationType.MOVE_WIDGET, "w_other", "u2", 0.0, x=10, y=10)
        result = collab._transform(remote)
        assert "no_op" not in result.data


# ---------------------------------------------------------------------------
# _transform: multiple concurrent local ops
# ---------------------------------------------------------------------------


class TestTransformMultipleConcurrent:
    def test_move_then_delete_sets_no_op(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.move_widget("w1", 0, 0, 10, 10))
        collab.execute_local(OperationBuilder.delete_widget("w1", {"type": "box"}))
        remote = _make_op(OperationType.MOVE_WIDGET, "w1", "u2", 0.0, x=50, y=50)
        result = collab._transform(remote)
        assert result.data.get("no_op") is True

    def test_multiple_moves_both_sides(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.move_widget("w1", 0, 0, 10, 10))
        collab.execute_local(OperationBuilder.move_widget("w1", 10, 10, 20, 20))
        remote = _make_op(OperationType.MOVE_WIDGET, "w1", "u2", 0.0, x=99, y=99)
        result = collab._transform(remote)
        # Multiple MOVE vs MOVE → still passes through (last writer wins)
        assert result.data["x"] == 99
        assert "deleted" not in result.data
        assert "no_op" not in result.data


# ---------------------------------------------------------------------------
# execute_local edge cases
# ---------------------------------------------------------------------------


class TestExecuteLocalEdgeCases:
    def test_execute_local_without_broadcast(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.on_broadcast = None
        assert collab.execute_local(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
        assert collab.local_manager.can_undo()

    def test_execute_local_returns_true(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        result = collab.execute_local(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
        assert result is True

    def test_execute_local_sets_user_id(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        op = OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10)
        collab.execute_local(op)
        history = collab.local_manager.get_history()
        assert history[0].user_id == "u1"


# ---------------------------------------------------------------------------
# receive_remote edge cases
# ---------------------------------------------------------------------------


class TestReceiveRemoteEdgeCases:
    def test_receive_remote_creates_user_entry(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        remote = _make_op(OperationType.ADD_WIDGET, "w2", "u2", 100.0, type="box")
        collab.receive_remote(remote)
        assert "u2" in collab.remote_operations
        assert len(collab.remote_operations["u2"]) == 1

    def test_receive_remote_multiple_users(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        r1 = _make_op(OperationType.ADD_WIDGET, "w2", "u2", 100.0, type="box")
        r2 = _make_op(OperationType.ADD_WIDGET, "w3", "u3", 200.0, type="label")
        collab.receive_remote(r1)
        collab.receive_remote(r2)
        assert "u2" in collab.remote_operations
        assert "u3" in collab.remote_operations

    def test_receive_remote_returns_transformed_op(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.move_widget("w1", 0, 0, 10, 10))
        remote = _make_op(OperationType.MOVE_WIDGET, "w1", "u2", 0.0, x=50, y=50)
        result = collab.receive_remote(remote)
        assert result.widget_id == "w1"
        assert result.data["x"] == 50  # MOVE vs MOVE → passes through


# ---------------------------------------------------------------------------
# merge_history edge cases
# ---------------------------------------------------------------------------


class TestMergeHistoryEdgeCases:
    def test_skip_local_user_ops(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        ops = []
        op = OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10)
        op.user_id = "u1"
        op.timestamp = 100.0
        ops.append(op)
        collab.merge_history(ops)
        # Should NOT appear in remote_operations (skipped because same user_id)
        assert "u1" not in collab.remote_operations

    def test_merge_multiple_remote_ops(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        ops = []
        for i in range(5):
            op = OperationBuilder.add_widget(f"w{i}", "box", i * 10, 0, 10, 10)
            op.user_id = "u2"
            op.timestamp = float(100 + i)
            ops.append(op)
        collab.merge_history(ops)
        assert len(collab.remote_operations["u2"]) == 5

    def test_merge_empty_list(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.merge_history([])
        assert len(collab.remote_operations) == 0


# ---------------------------------------------------------------------------
# get_all_operations edge cases
# ---------------------------------------------------------------------------


class TestGetAllOperationsEdgeCases:
    def test_empty(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        assert collab.get_all_operations() == []

    def test_local_only(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        collab.execute_local(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
        ops = collab.get_all_operations()
        assert len(ops) == 1
        assert ops[0].widget_id == "w1"

    def test_sorted_by_timestamp(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        # Add a local op (gets current timestamp)
        collab.execute_local(OperationBuilder.add_widget("w1", "box", 0, 0, 10, 10))
        # Remote op with much earlier timestamp
        r = _make_op(OperationType.ADD_WIDGET, "w0", "u2", 1.0, type="box")
        collab.receive_remote(r)
        # Remote op with much later timestamp
        r2 = _make_op(OperationType.ADD_WIDGET, "w2", "u3", time.time() + 99999, type="label")
        collab.receive_remote(r2)
        ops = collab.get_all_operations()
        assert len(ops) == 3
        assert ops[0].widget_id == "w0"  # earliest
        assert ops[-1].widget_id == "w2"  # latest


# ---------------------------------------------------------------------------
# CollaborativeUndoRedo init
# ---------------------------------------------------------------------------


class TestCollaborativeInit:
    def test_default_max_history(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        assert collab.local_manager.max_history == 50

    def test_custom_max_history(self):
        collab = CollaborativeUndoRedo(user_id="u1", max_history=10)
        assert collab.local_manager.max_history == 10

    def test_user_id_set(self):
        collab = CollaborativeUndoRedo(user_id="testuser")
        assert collab.local_manager.user_id == "testuser"

    def test_initial_state_empty(self):
        collab = CollaborativeUndoRedo(user_id="u1")
        assert collab.remote_operations == {}
        assert collab.on_broadcast is None
        assert not collab.local_manager.can_undo()
