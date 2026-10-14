"""Memory-only lifecycle regressions; bounded TEST_ONLY threads, no AnyIO loop.

Each controlled binary operation blocks on an Event, never a real pipe/file.
All gates release in finally and every owned thread is joined with a deadline.
Timing windows check non-completion only AFTER positive entry barriers; lock
ownership checks additionally establish exclusion without scheduler guessing.
No tool registry, SDK parser, close method or outcome is replaced.
"""

import io
import threading
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009, PT027
from unittest.mock import patch

from espos_mcp import strict_stdio as transport

PING = b'{"jsonrpc":"2.0","id":7,"method":"ping"}\n'
INVALID_PARAMS = b'{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":[]}}\n'
WAIT = 2.0
WINDOW = 0.1


class TEST_ONLY_Task:
    def __init__(self, function):
        self.started = threading.Event()
        self.done = threading.Event()
        self.value = None
        self.error = None

        def invoke():
            self.started.set()
            try:
                self.value = function()
            except BaseException as exc:
                self.error = exc
            finally:
                self.done.set()

        self.thread = threading.Thread(target=invoke, name="TEST_ONLY_lifecycle", daemon=True)
        self.thread.start()


class TEST_ONLY_Sink(io.BytesIO):
    def __init__(self):
        super().__init__()
        self.writes = 0
        self.flushes = 0

    def write(self, raw):
        self.writes += 1
        return super().write(raw)

    def flush(self):
        self.flushes += 1
        return super().flush()


class TEST_ONLY_PausedText(str):
    def __new__(cls, text, entered, release):
        obj = super().__new__(cls, text)
        obj.entered, obj.release = entered, release
        obj.encodings = 0
        return obj

    def encode(self, *args, **kwargs):
        self.encodings += 1
        self.entered.set()
        if not self.release.wait(WAIT):
            raise AssertionError("TEST_ONLY encoding gate deadline")
        return super().encode(*args, **kwargs)


class CloseOrderingTests(unittest.TestCase):
    def wait(self, event):
        self.assertTrue(event.wait(WAIT), "TEST_ONLY positive barrier deadline")

    def finish(self, tasks, gates=()):
        for gate in gates:
            gate.set()
        for task in tasks:
            task.thread.join(WAIT)
            self.assertFalse(task.thread.is_alive(), "TEST_ONLY owned thread did not terminate")

    def test_closed_output_rejects_before_encoding_or_physical_io(self):
        sink = TEST_ONLY_Sink()
        output = transport.BoundedTextOutput(sink)
        output.close()
        entered, release = threading.Event(), threading.Event()
        release.set()
        text = TEST_ONLY_PausedText(PING.decode(), entered, release)
        before = (sink.writes, sink.flushes)
        rejected = False
        try:
            output.write(text)
        except (ValueError, transport.StdioBoundaryError):
            rejected = True
        self.assertEqual(
            (text.encodings, sink.writes, sink.flushes, rejected), (0, before[0], before[1], True)
        )
        self.assertFalse(sink.closed)

    def test_closed_output_flush_rejects_without_touching_binary(self):
        sink = TEST_ONLY_Sink()
        output = transport.BoundedTextOutput(sink)
        output.close()
        before = sink.flushes
        rejected = False
        try:
            output.flush()
        except (ValueError, transport.StdioBoundaryError):
            rejected = True
        self.assertEqual((sink.flushes, rejected), (before, True))
        output.close()
        self.assertEqual(sink.flushes, before)

    def test_encoding_holds_the_same_actual_output_lock(self):
        entered, release = threading.Event(), threading.Event()
        sink = TEST_ONLY_Sink()
        output = transport.BoundedTextOutput(sink)
        text = TEST_ONLY_PausedText(PING.decode(), entered, release)
        writer = TEST_ONLY_Task(lambda: output.write(text))
        try:
            self.wait(entered)
            # READ-only ownership probe of the actual primitive. Never replace
            # the lock or grant a fake admission; release if baseline was free.
            acquired = output._lock.acquire(blocking=False)
            if acquired:
                output._lock.release()
            self.assertFalse(acquired, "Encoding escaped the physical-I/O lifecycle lock")
        finally:
            self.finish([writer], [release])
            output.close()
        self.assertIsNone(writer.error)

    def test_concurrent_close_waits_for_inflight_encoding_then_rejects_new_write(self):
        entered, release = threading.Event(), threading.Event()
        sink = TEST_ONLY_Sink()
        output = transport.BoundedTextOutput(sink)
        text = TEST_ONLY_PausedText(PING.decode(), entered, release)
        writer = TEST_ONLY_Task(lambda: output.write(text))
        tasks = [writer]
        try:
            self.wait(entered)
            closer = TEST_ONLY_Task(output.close)
            tasks.append(closer)
            self.wait(closer.started)
            self.assertFalse(closer.done.wait(WINDOW), "Close passed the active encoding operation")
        finally:
            self.finish(tasks, [release])
            output.close()
        self.assertIsNone(writer.error)
        self.assertIsNone(closer.error)
        self.assertTrue(output.closed)
        self.assertEqual(sink.getvalue(), PING)
        with self.assertRaises((ValueError, transport.StdioBoundaryError)):
            output.write(PING.decode())
        self.assertEqual(sink.getvalue(), PING)

    def test_concurrent_close_waits_for_physical_write_without_closing_binary(self):
        entered, release = threading.Event(), threading.Event()

        class TEST_ONLY_PausedWrite(TEST_ONLY_Sink):
            def write(self, raw):
                entered.set()
                if not release.wait(WAIT):
                    raise AssertionError("TEST_ONLY write gate deadline")
                return super().write(raw)

        sink = TEST_ONLY_PausedWrite()
        output = transport.BoundedTextOutput(sink)
        writer = TEST_ONLY_Task(lambda: output.write(PING.decode()))
        tasks = [writer]
        try:
            self.wait(entered)
            closer = TEST_ONLY_Task(output.close)
            tasks.append(closer)
            self.wait(closer.started)
            self.assertFalse(closer.done.wait(WINDOW))
        finally:
            self.finish(tasks, [release])
            output.close()
        self.assertIsNone(writer.error)
        self.assertIsNone(closer.error)
        self.assertEqual(sink.getvalue(), PING)
        self.assertFalse(sink.closed)
        self.assertTrue(output.closed)

    def test_concurrent_flush_excludes_even_encoding_until_flush_finishes(self):
        entered, release = threading.Event(), threading.Event()

        class TEST_ONLY_PausedFlush(TEST_ONLY_Sink):
            def flush(self):
                entered.set()
                if not release.wait(WAIT):
                    raise AssertionError("TEST_ONLY flush gate deadline")
                return super().flush()

        sink = TEST_ONLY_PausedFlush()
        output = transport.BoundedTextOutput(sink)
        flush = TEST_ONLY_Task(output.flush)
        encoded, encode_release = threading.Event(), threading.Event()
        encode_release.set()
        text = TEST_ONLY_PausedText(PING.decode(), encoded, encode_release)
        tasks = [flush]
        try:
            self.wait(entered)
            writer = TEST_ONLY_Task(lambda: output.write(text))
            tasks.append(writer)
            self.wait(writer.started)
            self.assertFalse(encoded.wait(WINDOW), "Encoding ran concurrently with physical flush")
        finally:
            self.finish(tasks, [release])
            output.close()
        self.assertIsNone(flush.error)
        self.assertIsNone(writer.error)
        self.assertEqual(sink.getvalue(), PING)

    def test_close_flush_excludes_new_encoding_and_write_then_rejects(self):
        entered, release = threading.Event(), threading.Event()

        class TEST_ONLY_PausedCloseFlush(TEST_ONLY_Sink):
            def flush(self):
                entered.set()
                if not release.wait(WAIT):
                    raise AssertionError("TEST_ONLY close-flush gate deadline")
                return super().flush()

        sink = TEST_ONLY_PausedCloseFlush()
        output = transport.BoundedTextOutput(sink)
        closer = TEST_ONLY_Task(output.close)
        encoded, encode_release = threading.Event(), threading.Event()
        encode_release.set()
        text = TEST_ONLY_PausedText(PING.decode(), encoded, encode_release)
        tasks = [closer]
        try:
            self.wait(entered)
            writer = TEST_ONLY_Task(lambda: output.write(text))
            tasks.append(writer)
            self.wait(writer.started)
            self.assertFalse(
                encoded.wait(WINDOW), "Close did not serialize its own flush with encoding"
            )
        finally:
            self.finish(tasks, [release])
            output.close()
        self.assertIsNone(closer.error)
        self.assertIsInstance(writer.error, (ValueError, transport.StdioBoundaryError))
        self.assertEqual(text.encodings, 0)
        self.assertEqual(sink.getvalue(), b"")

    def test_partial_failure_close_and_flush_never_retry_binary(self):
        class TEST_ONLY_PartialFailure(TEST_ONLY_Sink):
            def write(self, raw):
                if self.writes == 0:
                    return super().write(raw[:3])
                self.writes += 1
                raise OSError("TEST_ONLY partial failure")

        sink = TEST_ONLY_PartialFailure()
        output = transport.BoundedTextOutput(sink)
        with self.assertRaises(transport.StdioBoundaryError):
            output.write(PING.decode())
        before = (sink.writes, sink.flushes, sink.getvalue())
        output.flush()  # Open but failed: deliberately no physical retry.
        output.close()
        output.close()
        with self.assertRaises((ValueError, transport.StdioBoundaryError)):
            output.write(PING.decode())
        self.assertEqual((sink.writes, sink.flushes, sink.getvalue()), before)
        self.assertEqual(sink.getvalue(), b'{"j')
        self.assertFalse(sink.closed)

    def test_close_flush_error_still_closes_wrapper_without_retry_or_binary_close(self):
        class TEST_ONLY_FlushError(TEST_ONLY_Sink):
            def flush(self):
                self.flushes += 1
                raise OSError("TEST_ONLY flush error")

        sink = TEST_ONLY_FlushError()
        output = transport.BoundedTextOutput(sink)
        with self.assertRaises(transport.StdioBoundaryError):
            output.close()
        self.assertTrue(output.closed)
        self.assertFalse(sink.closed)
        output.close()
        self.assertEqual(sink.flushes, 1)

    def test_concurrent_repeated_close_is_idempotent_and_not_deadlocked_by_flush(self):
        sink = TEST_ONLY_Sink()
        output = transport.BoundedTextOutput(sink)
        tasks = [TEST_ONLY_Task(output.close) for _ in range(3)]
        self.finish(tasks)
        self.assertTrue(all(task.error is None for task in tasks))
        self.assertTrue(output.closed)
        self.assertEqual(sink.flushes, 1)
        self.assertFalse(sink.closed)

    def test_two_inflight_output_frames_never_interleave_partial_writes(self):
        entered, release = threading.Event(), threading.Event()

        class TEST_ONLY_ShortBarrier(TEST_ONLY_Sink):
            def write(self, raw):
                if self.writes == 0:
                    entered.set()
                    if not release.wait(WAIT):
                        raise AssertionError("TEST_ONLY first-write gate deadline")
                return super().write(raw[:3])

        sink = TEST_ONLY_ShortBarrier()
        output = transport.BoundedTextOutput(sink)
        other = b'{"jsonrpc":"2.0","id":8,"method":"ping"}\n'
        first = TEST_ONLY_Task(lambda: output.write(PING.decode()))
        tasks = [first]
        try:
            self.wait(entered)
            second = TEST_ONLY_Task(lambda: output.write(other.decode()))
            tasks.append(second)
            self.wait(second.started)
        finally:
            self.finish(tasks, [release])
            output.close()
        self.assertTrue(all(task.error is None for task in tasks))
        self.assertEqual(sink.getvalue(), PING + other)

    def late_read(self, raw, failure=False):
        entered, release = threading.Event(), threading.Event()

        class TEST_ONLY_PausedRead(io.BytesIO):
            calls = 0

            def readline(self, size=-1):
                self.calls += 1
                entered.set()
                if not release.wait(WAIT):
                    raise AssertionError("TEST_ONLY read gate deadline")
                if failure:
                    raise OSError("TEST_ONLY late I/O error")
                return super().readline(size)

        binary = TEST_ONLY_PausedRead(raw)
        sink = TEST_ONLY_Sink()
        output = transport.BoundedTextOutput(sink)
        reader = transport.StrictTextInput(binary, output)
        with patch.object(transport, "admit_frame", wraps=transport.admit_frame) as admission:
            pending = TEST_ONLY_Task(reader.readline)
            tasks = [pending]
            try:
                self.wait(entered)
                closer = TEST_ONLY_Task(reader.close)
                tasks.append(closer)
                self.wait(closer.done)  # Must finish WHILE underlying read is paused.
                self.assertFalse(release.is_set())
                self.assertIsNone(closer.error)
                self.assertTrue(reader.closed)
            finally:
                self.finish(tasks, [release])
                reader.close()
                output.close()
            self.assertEqual(
                admission.call_count, 0, "Closed in-flight read reached admission/reply"
            )
        self.assertIsInstance(pending.error, transport.StdioBoundaryError)
        self.assertEqual(str(pending.error), "MCP input stream is closed.")
        self.assertIsNone(pending.value)
        self.assertEqual(sink.getvalue(), b"")
        self.assertEqual(binary.calls, 1)
        self.assertFalse(binary.closed)
        self.assertFalse(sink.closed)

    def test_concurrent_close_discards_inflight_valid_frame_before_admission(self):
        self.late_read(PING)

    def test_concurrent_close_discards_invalid_params_before_correlated_reply(self):
        self.late_read(INVALID_PARAMS)

    def test_concurrent_close_rejects_late_eof_instead_of_returning_empty_success(self):
        self.late_read(b"")

    def test_concurrent_close_rejects_late_io_error_with_closed_not_stale_failure(self):
        self.late_read(b"", failure=True)

    def test_concurrent_close_discards_oversized_result_before_admission(self):
        self.late_read(b"x" * (transport.MAX_INPUT_FRAME_BYTES + 2))

    def test_concurrent_close_discards_malformed_result_before_rejected_token(self):
        self.late_read(b'{"TEST_ONLY":NaN}\n')

    def test_new_read_after_close_rejects_while_old_binary_read_remains_pending(self):
        entered, release = threading.Event(), threading.Event()

        class TEST_ONLY_OnePausedRead(io.BytesIO):
            calls = 0

            def readline(self, size=-1):
                self.calls += 1
                if self.calls == 1:
                    entered.set()
                    if not release.wait(WAIT):
                        raise AssertionError("TEST_ONLY read gate deadline")
                return super().readline(size)

        binary = TEST_ONLY_OnePausedRead(PING)
        output = transport.BoundedTextOutput(io.BytesIO())
        reader = transport.StrictTextInput(binary, output)
        pending = TEST_ONLY_Task(reader.readline)
        tasks = [pending]
        try:
            self.wait(entered)
            closer = TEST_ONLY_Task(reader.close)
            tasks.append(closer)
            self.wait(closer.done)
            later = TEST_ONLY_Task(reader.readline)
            tasks.append(later)
            self.wait(later.done)
            self.assertIsInstance(later.error, transport.StdioBoundaryError)
            self.assertEqual(binary.calls, 1)
            self.assertFalse(pending.done.is_set())
        finally:
            self.finish(tasks, [release])
            reader.close()
            output.close()

    def test_inflight_read_without_close_still_admits_exact_original_frame(self):
        entered, release = threading.Event(), threading.Event()

        class TEST_ONLY_PausedRead(io.BytesIO):
            def readline(self, size=-1):
                entered.set()
                if not release.wait(WAIT):
                    raise AssertionError("TEST_ONLY read gate deadline")
                return super().readline(size)

        binary = TEST_ONLY_PausedRead(PING)
        output = transport.BoundedTextOutput(io.BytesIO())
        reader = transport.StrictTextInput(binary, output)
        pending = TEST_ONLY_Task(reader.readline)
        try:
            self.wait(entered)
        finally:
            self.finish([pending], [release])
            reader.close()
            output.close()
        self.assertIsNone(pending.error)
        self.assertEqual(pending.value.encode("utf-8"), PING)
        self.assertEqual(binary.tell(), len(PING))


if __name__ == "__main__":
    unittest.main(verbosity=2)
