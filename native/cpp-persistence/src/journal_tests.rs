//! Actual Windows filesystem/flush/lease fixtures; caller/picker is TEST_ONLY.
//! No real editor IPC, UI picker, same-user exclusion, or power-cut experiment.
use super::*;
use crate::writer::WriterEnvironment;
use crate::{Outcome, Registry, Request, ReserveRequest, Start, Status};

struct Fixture {
    root: PathBuf,
    storage: PathBuf,
    target: PathBuf,
}
impl Fixture {
    fn new(bytes: &[u8]) -> Self {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("test-tmp")
            .join(format!("journal-{}", windows_read::random_hex().unwrap()));
        assert!(root.starts_with(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp")));
        std::fs::create_dir_all(&root).unwrap();
        let storage = root.join("app-storage");
        std::fs::create_dir(&storage).unwrap();
        let target = root.join("test.cpp");
        std::fs::write(&target, bytes).unwrap();
        Self {
            root,
            storage,
            target,
        }
    }
    // Retain unique, git-ignored evidence. No recursive deletion or user files.
}
fn scope(bytes: &[u8]) -> Scope {
    let mut registry = Registry::new().unwrap();
    let caller = registry.attach_caller().unwrap();
    let id = registry
        .reserve_request(&caller, ReserveRequest::New {})
        .unwrap();
    let Start::Ready(Status::Complete {
        result: Outcome::Created { document },
        ..
    }) = registry
        .new_document(&caller, Request { request_id: id })
        .unwrap()
    else {
        panic!()
    };
    let operation = registry
        .reserve(
            &caller,
            crate::Operation::Save(document.document_id.clone()),
        )
        .unwrap();
    Scope {
        schema: 1,
        operation,
        session: caller.session,
        incarnation: caller.incarnation,
        document: document.document_id,
        version: None,
        source_hash: digest(bytes),
        source_bytes: bytes.len(),
    }
}
fn overwrite(f: &Fixture, env: &WriterEnvironment, next: &[u8]) -> Scope {
    let s = scope(next);
    let mut t = HeldTarget::open(&f.target).unwrap();
    let before = t.snapshot().unwrap();
    t.recheck(&before).unwrap();
    let p = env.journal.prepare(&s, &f.target, &before, next).unwrap();
    env.journal.mark_may_write(&s, &p).unwrap();
    t.update(next, &AtomicBool::new(false)).unwrap();
    let after = t.snapshot().unwrap();
    t.recheck(&after).unwrap();
    env.journal.record_written(&s, &p, &after).unwrap();
    t.recheck(&after).unwrap();
    env.journal.finish_verified(&s).unwrap();
    s
}
#[test]
fn host_storage_requires_existing_nonredirected_parent() {
    let f = Fixture::new(b"untouched");
    let missing = f.root.join("missing");
    assert!(WriterEnvironment::open_local(&missing).is_err());
    assert!(!missing.exists());
    assert_eq!(std::fs::read(&f.target).unwrap(), b"untouched");
}
#[test]
fn real_single_host_lease_is_busy_and_releases_on_drop() {
    let f = Fixture::new(b"old");
    let first = WriterEnvironment::open_local(&f.storage).unwrap();
    assert!(matches!(
        WriterEnvironment::open_local(&f.storage),
        Err(Code::Busy)
    ));
    drop(first);
    assert!(WriterEnvironment::open_local(&f.storage)
        .unwrap()
        .recovery_records()
        .is_empty());
}
#[test]
fn actual_external_bytes_not_an_editor_baseline_are_backed_up() {
    let f = Fixture::new(b"stale baseline");
    std::fs::write(&f.target, b"actual external revision\0\xff").unwrap();
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, b"new bytes\0\xff");
    let (_, backup) = env.journal.read(&s, "backup.bin").unwrap();
    assert_eq!(backup, b"actual external revision\0\xff");
    assert_eq!(std::fs::read(&f.target).unwrap(), b"new bytes\0\xff");
}
#[test]
fn immutable_journal_collision_does_not_overwrite_an_artifact() {
    let f = Fixture::new(b"old");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = scope(b"next");
    env.journal.reserve_budget(&s).unwrap();
    env.journal.create(&s, "payload.bin", b"first").unwrap();
    assert!(env.journal.create(&s, "payload.bin", b"second").is_err());
    assert_eq!(env.journal.read(&s, "payload.bin").unwrap().1, b"first");
    assert_eq!(std::fs::read(&f.target).unwrap(), b"old");
}
#[test]
fn restart_retains_verified_historical_receipt_but_never_adopts_old_caller() {
    let f = Fixture::new(b"old");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, b"next");
    drop(env);
    // A later ordinary editor modification doesn't invalidate a historical
    // immutable receipt, nor imply that current bytes still equal saved bytes.
    std::fs::write(&f.target, b"later external").unwrap();
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let records = env.recovery_records();
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].operation_id, s.operation);
    assert_eq!(records[0].document_id, s.document);
    assert_eq!(records[0].phase, "written-receipt");
    assert!(records[0].backup_available);
    assert_eq!(records[0].source_hash, digest(b"next"));
    let mut fresh = Registry::new().unwrap();
    let caller = fresh.attach_caller().unwrap();
    assert!(matches!(
        fresh.status(&caller, &s.operation),
        Err(Code::UnknownRequest)
    ));
    assert!(matches!(
        fresh.reserve(&caller, crate::Operation::Save(s.document)),
        Err(Code::Denied)
    ));
    assert_eq!(std::fs::read(&f.target).unwrap(), b"later external");
    assert!(env.journal.admit_new_write().is_ok());
}
#[test]
fn interrupted_write_is_recovery_required_and_new_writes_are_not_admitted() {
    let f = Fixture::new(b"original");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = scope(b"full captured new bytes");
    let mut t = HeldTarget::open(&f.target).unwrap();
    let before = t.snapshot().unwrap();
    let p = env
        .journal
        .prepare(&s, &f.target, &before, b"full captured new bytes")
        .unwrap();
    env.journal.mark_may_write(&s, &p).unwrap();
    // Real partial-effect fixture, no terminal receipt. Reopening may only
    // inspect; matching bytes, cancellation, and old caller IDs aren't proof.
    t.update(b"PARTIAL", &AtomicBool::new(false)).unwrap();
    drop(t);
    // Another live caller/operation must not evade the same-host uncertainty.
    assert_eq!(env.journal.admit_new_write(), Err(Code::Unavailable));
    let later = scope(b"do not write");
    let mut target = HeldTarget::open(&f.target).unwrap();
    let current = target.snapshot().unwrap();
    assert!(matches!(
        env.journal
            .prepare(&later, &f.target, &current, b"do not write"),
        Err(Code::Unavailable)
    ));
    drop(target);
    drop(env);
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    assert_eq!(env.recovery_records()[0].phase, "recovery-required");
    assert!(env.recovery_records()[0].backup_available);
    assert_eq!(env.journal.admit_new_write(), Err(Code::Unavailable));
    assert_eq!(std::fs::read(&f.target).unwrap(), b"PARTIAL");
    assert_eq!(env.journal.read(&s, "backup.bin").unwrap().1, b"original");
    assert_eq!(
        env.journal.read(&s, "payload.bin").unwrap().1,
        b"full captured new bytes"
    );
}
#[test]
fn prepared_but_unfinished_intent_never_proves_not_started_after_restart() {
    let f = Fixture::new(b"original");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = scope(b"next");
    let mut t = HeldTarget::open(&f.target).unwrap();
    let before = t.snapshot().unwrap();
    env.journal
        .prepare(&s, &f.target, &before, b"next")
        .unwrap();
    drop(t);
    drop(env);
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    assert_eq!(env.recovery_records()[0].phase, "recovery-required");
    assert_eq!(std::fs::read(&f.target).unwrap(), b"original");
}
#[test]
fn malformed_receipt_does_not_clean_unknown_or_retry_target() {
    let f = Fixture::new(b"original");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, b"next");
    let receipt = env.journal.path(&s, "written.json").unwrap();
    drop(env);
    std::fs::write(receipt, b"{corrupt").unwrap();
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    assert_eq!(env.recovery_records()[0].phase, "recovery-required");
    assert_eq!(std::fs::read(&f.target).unwrap(), b"next");
}
#[test]
fn orphan_without_intent_fails_closed_and_is_retained() {
    let f = Fixture::new(b"original");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = scope(b"next");
    let p = env.journal.path(&s, "payload.bin").unwrap();
    env.journal.reserve_budget(&s).unwrap();
    env.journal.create(&s, "payload.bin", b"next").unwrap();
    drop(env);
    assert!(WriterEnvironment::open_local(&f.storage).is_err());
    assert_eq!(std::fs::read(p).unwrap(), b"next");
    assert_eq!(std::fs::read(&f.target).unwrap(), b"original");
}
#[test]
fn actual_create_new_flush_readback_and_restart_receipt() {
    let f = Fixture::new(b"unrelated");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let path = f.root.join("new.cpp");
    let s = scope(b"new\0\xff\r\n");
    let parent = windows_read::capture_parent_identity(&path).unwrap();
    let mut artifacts = None;
    let mut uncertain = false;
    let result = crate::create_target::execute_create(
        &s,
        &path,
        &parent,
        b"new\0\xff\r\n",
        &AtomicBool::new(false),
        &env.journal,
        &mut artifacts,
        &mut uncertain,
    )
    .unwrap();
    assert!(matches!(
        result,
        crate::create_target::CreatedEffect::Written(..)
    ));
    assert!(uncertain);
    assert_eq!(std::fs::read(&path).unwrap(), b"new\0\xff\r\n");
    drop(env);
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    assert_eq!(env.recovery_records().len(), 1);
    assert_eq!(env.recovery_records()[0].phase, "written-receipt");
    assert!(!env.recovery_records()[0].backup_available);
}
#[test]
fn complete_artifact_file_budget_is_reserved_before_overwrite() {
    let f = Fixture::new(b"original");
    let mut env = WriterEnvironment::open_local(&f.storage).unwrap();
    // TEST_ONLY smaller cap exercises the exact production quota branch without
    // constructing thousands of fixtures. All filesystem operations are real.
    env.journal.file_limit = 5; // host.lock + five artifacts cannot fit
    let mut target = HeldTarget::open(&f.target).unwrap();
    let before = target.snapshot().unwrap();
    assert!(matches!(
        env.journal
            .prepare(&scope(b"next"), &f.target, &before, b"next"),
        Err(Code::TooLarge)
    ));
    drop(target);
    assert_eq!(std::fs::read(&f.target).unwrap(), b"original");
    assert_eq!(std::fs::read_dir(&env.journal.root).unwrap().count(), 1);
}
#[test]
fn complete_receipt_byte_budget_is_reserved_before_create_new() {
    let f = Fixture::new(b"original");
    let mut env = WriterEnvironment::open_local(&f.storage).unwrap();
    env.journal.byte_limit = (5 * MAX_RECORD - 1) as u64;
    let path = f.root.join("absent.cpp");
    let s = scope(b"next");
    let parent = windows_read::capture_parent_identity(&path).unwrap();
    let mut artifacts = None;
    let mut uncertain = false;
    assert!(matches!(
        crate::create_target::execute_create(
            &s,
            &path,
            &parent,
            b"next",
            &AtomicBool::new(false),
            &env.journal,
            &mut artifacts,
            &mut uncertain
        ),
        Err(Code::TooLarge)
    ));
    assert!(!uncertain);
    assert!(artifacts.is_none());
    assert!(!path.exists());
    assert_eq!(std::fs::read_dir(&env.journal.root).unwrap().count(), 1);
}
#[test]
fn exactly_full_successful_journal_remains_readable_and_reopenable() {
    let f = Fixture::new(b"original");
    let mut env = WriterEnvironment::open_local(&f.storage).unwrap();
    env.journal.file_limit = 6; // exactly host.lock + five artifacts
    overwrite(&f, &env, b"next");
    assert_eq!(std::fs::read_dir(&env.journal.root).unwrap().count(), 6);
    assert_eq!(env.journal.check_quota(0, 0), Ok(()));
    assert_eq!(
        env.journal.scan_recovery().unwrap()[0].phase,
        "written-receipt"
    );
    assert_eq!(
        env.journal.reserve_budget(&scope(b"later")),
        Err(Code::TooLarge)
    );
    drop(env);
    assert_eq!(
        WriterEnvironment::open_local(&f.storage)
            .unwrap()
            .recovery_records()[0]
            .phase,
        "written-receipt"
    );
}
#[test]
fn sibling_creation_does_not_change_selected_parent_object() {
    let f = Fixture::new(b"original");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let path = f.root.join("selected.cpp");
    let parent = windows_read::capture_parent_identity(&path).unwrap();
    std::fs::write(f.root.join("unrelated.cpp"), b"sibling").unwrap();
    let s = scope(b"new");
    let mut artifacts = None;
    let mut uncertain = false;
    assert!(matches!(
        crate::create_target::execute_create(
            &s,
            &path,
            &parent,
            b"new",
            &AtomicBool::new(false),
            &env.journal,
            &mut artifacts,
            &mut uncertain
        ),
        Ok(crate::create_target::CreatedEffect::Written(..))
    ));
    assert_eq!(std::fs::read(&path).unwrap(), b"new");
}
#[test]
fn replaced_selected_parent_is_rejected_before_create_or_artifacts() {
    let f = Fixture::new(b"original");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let directory = f.root.join("selected-parent");
    let retained = f.root.join("retained-parent");
    assert_eq!(directory.parent(), Some(f.root.as_path()));
    assert_eq!(retained.parent(), Some(f.root.as_path()));
    std::fs::create_dir(&directory).unwrap();
    let path = directory.join("selected.cpp");
    let parent = windows_read::capture_parent_identity(&path).unwrap();
    // Only the fresh test's named directory is moved; retained for inspection.
    std::fs::rename(&directory, &retained).unwrap();
    std::fs::create_dir(&directory).unwrap();
    let s = scope(b"new");
    let mut artifacts = None;
    let mut uncertain = false;
    assert!(matches!(
        crate::create_target::execute_create(
            &s,
            &path,
            &parent,
            b"new",
            &AtomicBool::new(false),
            &env.journal,
            &mut artifacts,
            &mut uncertain
        ),
        Err(Code::Conflict)
    ));
    assert!(!path.exists());
    assert!(!uncertain);
    assert!(artifacts.is_none());
    assert_eq!(std::fs::read_dir(&env.journal.root).unwrap().count(), 1);
}
