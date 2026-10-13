# Native C++ persistence library

This is the canonical Windows library for the ESPOS desktop's native registry,
not a second editable document owner. The existing frontend ProjectDocument
remains the source owner. Tauri commands and frontend ports are **not connected**
by adding this library.

## Product decision, 2026-10-13

The user selected a conventional local editor with backup, conflict checking and
recovery of uncertain writes. No separate privileged service, ACL changes,
isolated principal, or protection against a malicious process under the same
Windows account is requested. Do not describe a final metadata recheck or
exclusive file handle as unconditional actor exclusion/atomic compare-and-swap.

The native host resolves its existing app-local storage directory and calls
`WriterEnvironment::open_local`. This argument must never be taken from an IPC
request, project contents, a URL, or the current working directory. Only the
`cpp-recovery-v1` child is created; existing ancestors must be ordinary local
NTFS directories. A held `host.lock` enforces a cooperative single-host lease.

## Behavior and limits

- Read and write grants are issued by the same native Registry after native
  selection; request/document/version IDs are not paths or sender authority.
- A save retains immutable captured bytes and one operation ID. Replays/status
  queries do not start another write.
- An external conflict requires explicit Stop or overwrite-with-actual-backup.
  The selected external revision is rechecked under the held target handle.
- Backups contain actual external bytes, not the editor's stale baseline. Backup,
  payload, intent and effect receipts are CREATE_NEW artifacts, never overwritten.
- Writes update one held handle in place. New targets use CREATE_NEW, never
  truncate a file that appeared at the chosen path.
- A possible mutation followed by a transport/error/cancellation/failed
  verification remains recovery-required. No automatic retry/restore/deletion.
- Startup enumerates native journal records without recreating old callers,
  grants or frontend documents. A valid written receipt is historical evidence,
  not a claim that the current file has not subsequently changed.
- Unfinished records block fresh writes; missing/corrupt orphan intents fail
  admission closed and are retained. Native read-only inspection revalidates
  startup-catalogued intents, payloads, actual backups and historical receipts;
  current target observations distinguish changed, missing, busy and errors.
  It never restores, retries, changes admission or mints an old grant. The
  user-facing inspection/resolution UI and genuine Tauri sender/navigation
  binding remain integration work.
- Journal admission is bounded to 4096 files and 512 MiB. No automatic backup
  garbage collection is enabled. Quota exhaustion stops before target mutation.

File flush/readback and namespace checks are real operations. They are **not**
proof of joint directory-entry/cross-file power-loss ordering. In-place saves
can leave partial bytes after a process failure; backups and the uncertain
operation are retained. No power-cut experiment has been performed. Relevant
primitive contracts: [Rust File::sync_all](https://doc.rust-lang.org/std/fs/struct.File.html#method.sync_all),
[OpenOptions::create_new](https://doc.rust-lang.org/std/fs/struct.OpenOptions.html#method.create_new),
[Windows share_mode](https://doc.rust-lang.org/std/os/windows/fs/trait.OpenOptionsExt.html#tymethod.share_mode).

## Verification

`run_tests.py` runs the locked offline Rust test suite using the existing
workspace Job Object helper. Assignment precedes command release, all descendants
must end naturally, and forced cleanup never counts as success. Reports are fresh
under `target/reports`; test fixtures remain under ignored `test-tmp`. It uses the
installed Rust toolchain's `rust-lld` in documented `lld-link` mode with installed
MSVC/Windows SDK import libraries; this affects only the test process environment,
not global Visual Studio telemetry settings. Source bytes are compared at the run
boundaries; that is not an atomic snapshot against an adversarial actor.

This is native-library filesystem verification, **not** a live editor save,
native picker interaction, packaged installer, Tab5 hardware or live MCP proof.
Until integration and validation, the desktop's unavailable native ports remain
unavailable. Original frozen worker artifacts and negative actor evidence remain
untouched.

Source provenance: the existing native-host-adapter registry baseline, the
native-host-writer-recovery types, SaveAs implementation's read/capture helpers,
and CREATE_NEW successor's library/writer/journal/create path. This canonical
composition replaces the unresolved strong-domain gate with the explicitly
chosen local-cooperative policy; it does not relabel old source-only or failed
native runs as accepted.

`NativeHost` coordinates dispatch over the same Registry. A raw `callId` is only
a bounded replay correlation key, not sender authority; exact mutation replays
return their existing operation rather than dispatching more work. Binding and
first-load tickets are native-only. A second main-document start permanently
revokes that registration; outstanding owned work must settle its real effect.
Tests supply explicitly TEST_ONLY lifecycle callbacks, not physical Tauri proof.

Repository decision (2026-10-13): ESPOS and espos-tauri remain separate. Desktop
consumers must depend on an exact published ESPOS Git revision, not a machine
path, moving branch or duplicated library. Keep the lockfile committed. The
isolated `native-cpp.yml` Windows CI verifies this library separately from Python
and firmware; adding a workflow is not evidence of a successful remote run.

Latest observed verification (2026-10-13): **93 passed, 0 failed, 0 ignored**,
offline Windows compile/test, natural root exit 0 and confirmed owned Job zero,
no forced cleanup, source boundary snapshots unchanged. Final formatted-source
report: `target/reports/native-b9c77825f3ea4e5cbd5d123c14259a71/result.json`.
The preceding 64-pass/1-fail native report is retained; it exposed the absent
SaveAs target appearance/parent-timestamp bug, now covered with separate genuine
sibling-change and parent-object-replacement regressions. No live editor save or
Tauri sender/IPC acceptance is claimed.
