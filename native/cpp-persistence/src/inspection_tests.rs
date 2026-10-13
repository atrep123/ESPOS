//! Genuine Windows filesystem fixtures; caller/selection is TEST_ONLY.
//! No editor IPC, physical picker, actor-exclusion or power-cut proof.
use super::*;
use crate::writer::WriterEnvironment;
use crate::{Operation, Outcome, Registry, Request, ReserveRequest, Start, Status};

struct Fixture {
    root: PathBuf,
    storage: PathBuf,
    target: PathBuf,
}
impl Fixture {
    fn new(bytes: &[u8]) -> Self {
        let base = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp");
        let root = base.join(format!(
            "inspection-{}",
            windows_read::random_hex().unwrap()
        ));
        assert!(root.starts_with(&base));
        std::fs::create_dir_all(&root).unwrap();
        let storage = root.join("app-storage");
        std::fs::create_dir(&storage).unwrap();
        let target = root.join("selected.cpp");
        std::fs::write(&target, bytes).unwrap();
        Self {
            root,
            storage,
            target,
        }
    }
    // Retain unique ignored fixtures, including moved/corrupted evidence.
}
fn scope(bytes: &[u8]) -> Scope {
    let mut registry = Registry::new().unwrap();
    let caller = registry.attach_caller().unwrap();
    let request_id = registry
        .reserve_request(&caller, ReserveRequest::New {})
        .unwrap();
    let Start::Ready(Status::Complete {
        result: Outcome::Created { document },
        ..
    }) = registry
        .new_document(&caller, Request { request_id })
        .unwrap()
    else {
        panic!()
    };
    let operation = registry
        .reserve(&caller, Operation::Save(document.document_id.clone()))
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
fn overwrite(f: &Fixture, env: &WriterEnvironment, next: &[u8], complete: bool) -> Scope {
    let s = scope(next);
    let mut target = HeldTarget::open(&f.target).unwrap();
    let before = target.snapshot().unwrap();
    let p = env.journal.prepare(&s, &f.target, &before, next).unwrap();
    env.journal.mark_may_write(&s, &p).unwrap();
    if complete {
        target.update(next, &AtomicBool::new(false)).unwrap();
        let after = target.snapshot().unwrap();
        target.recheck(&after).unwrap();
        env.journal.record_written(&s, &p, &after).unwrap();
        env.journal.finish_verified(&s).unwrap();
    }
    s
}
fn restart(f: &Fixture, env: WriterEnvironment) -> WriterEnvironment {
    drop(env);
    WriterEnvironment::open_local(&f.storage).unwrap()
}
// Exact journal bytes/names plus write metadata. host.lock remains held and
// cannot be data-opened, so its size/write metadata is checked separately.
fn journal_snapshot(env: &WriterEnvironment) -> Vec<(String, Vec<u8>, u64, u64, u32)> {
    let mut entries = Vec::new();
    for entry in std::fs::read_dir(&env.journal.root).unwrap() {
        let entry = entry.unwrap();
        let name = entry.file_name().into_string().unwrap();
        let metadata = entry.path().symlink_metadata().unwrap();
        let bytes = if name == "host.lock" {
            vec![]
        } else {
            std::fs::read(entry.path()).unwrap()
        };
        entries.push((
            name,
            bytes,
            metadata.len(),
            metadata.last_write_time(),
            metadata.file_attributes(),
        ));
    }
    entries.sort_by(|a, b| a.0.cmp(&b.0));
    entries
}
fn target_snapshot(path: &Path) -> Revision {
    let file = OpenOptions::new()
        .read(true)
        .share_mode(1)
        .open(path)
        .unwrap();
    capture_read_grant(path, &file).unwrap()
}
#[test]
fn unlisted_and_live_ids_are_denied_without_catalog_or_filesystem_changes() {
    let f = Fixture::new(b"external");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, b"captured", false);
    let before = journal_snapshot(&env);
    assert!(matches!(
        env.inspect_recovery(&s.operation),
        Err(Code::Denied)
    ));
    assert!(env.recovery_records().is_empty());
    assert_eq!(before, journal_snapshot(&env));
    let env = restart(&f, env);
    let unknown = scope(b"unlisted").operation;
    let before = journal_snapshot(&env);
    assert!(matches!(env.inspect_recovery(&unknown), Err(Code::Denied)));
    assert_eq!(env.recovery_records().len(), 1);
    assert_eq!(before, journal_snapshot(&env));
    assert_eq!(std::fs::read(&f.target).unwrap(), b"external");
}
#[test]
fn exact_raw_payload_actual_backup_and_detached_result_preserve_unknown_admission() {
    let f = Fixture::new(b"stale editor baseline");
    let external = b"ACTUAL external\0\xff\r\n";
    let next = b"CAPTURED payload\0\xfe\r\n";
    std::fs::write(&f.target, external).unwrap();
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, next, false);
    std::fs::write(&f.target, b"PARTIAL\0\xff").unwrap();
    let env = restart(&f, env);
    let before_target = target_snapshot(&f.target);
    let before_journal = journal_snapshot(&env);
    let before_catalog = serde_json::to_vec(env.recovery_records()).unwrap();
    let mut inspection = env.inspect_recovery(&s.operation).unwrap();
    assert_eq!(inspection.payload, next);
    assert_eq!(inspection.backup.as_deref(), Some(external.as_slice()));
    assert_eq!(inspection.native_path, f.target);
    assert_eq!(inspection.prior_record.phase, "recovery-required");
    assert!(
        matches!(&inspection.current, CurrentTargetObservation::Changed { bytes, hash }
        if bytes == b"PARTIAL\0\xff" && hash == &digest(bytes))
    );
    inspection.payload.fill(0);
    inspection.backup.as_mut().unwrap().fill(0);
    inspection.scope.session.clear();
    let again = env.inspect_recovery(&s.operation).unwrap();
    assert_eq!(again.payload, next);
    assert_eq!(again.backup.as_deref(), Some(external.as_slice()));
    assert_eq!(again.scope.session, s.session);
    assert_eq!(env.journal.admit_new_write(), Err(Code::Unavailable));
    assert!(env.journal.reservations.lock().unwrap().is_empty());
    assert_eq!(
        before_catalog,
        serde_json::to_vec(env.recovery_records()).unwrap()
    );
    assert_eq!(before_journal, journal_snapshot(&env));
    assert_eq!(before_target, target_snapshot(&f.target));
}
#[test]
fn prior_scope_is_historical_and_never_adopted_by_fresh_registry() {
    let f = Fixture::new(b"old");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, b"saved", true);
    let env = restart(&f, env);
    let before = journal_snapshot(&env);
    let inspection = env.inspect_recovery(&s.operation).unwrap();
    assert_eq!(inspection.scope.operation_id, s.operation);
    assert_eq!(inspection.scope.document_id, s.document);
    assert_eq!(inspection.scope.session, s.session);
    assert_eq!(inspection.scope.incarnation, s.incarnation);
    assert_eq!(inspection.scope.captured_version, s.version);
    assert_eq!(inspection.prior_record.phase, "written-receipt");
    assert!(
        matches!(&inspection.current, CurrentTargetObservation::Unchanged { bytes, .. } if bytes == b"saved")
    );
    let mut fresh = Registry::new().unwrap();
    let caller = fresh.attach_caller().unwrap();
    assert_ne!(caller.session, inspection.scope.session);
    assert!(matches!(
        fresh.status(&caller, &inspection.scope.operation_id),
        Err(Code::UnknownRequest)
    ));
    assert!(matches!(
        fresh.reserve(
            &caller,
            Operation::Save(inspection.scope.document_id.clone())
        ),
        Err(Code::Denied)
    ));
    std::fs::write(&f.target, b"later external").unwrap();
    let again = env.inspect_recovery(&s.operation).unwrap();
    assert_eq!(again.prior_record.phase, "written-receipt");
    assert!(
        matches!(&again.current, CurrentTargetObservation::Changed { bytes, .. } if bytes == b"later external")
    );
    assert!(env.journal.admit_new_write().is_ok());
    assert_eq!(before, journal_snapshot(&env));
}
#[test]
fn missing_current_is_distinct_from_a_real_empty_file_and_does_not_create() {
    let f = Fixture::new(b"old");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, b"payload", false);
    let env = restart(&f, env);
    std::fs::rename(&f.target, f.root.join("retained-original.cpp")).unwrap();
    let before = journal_snapshot(&env);
    let inspection = env.inspect_recovery(&s.operation).unwrap();
    assert!(matches!(
        inspection.current,
        CurrentTargetObservation::Missing
    ));
    assert_eq!(inspection.payload, b"payload");
    assert_eq!(inspection.backup.as_deref(), Some(b"old".as_slice()));
    assert!(!f.target.exists());
    std::fs::write(&f.target, []).unwrap();
    assert!(
        matches!(env.inspect_recovery(&s.operation).unwrap().current,
        CurrentTargetObservation::Changed { bytes, hash } if bytes.is_empty() && hash == digest(b""))
    );
    assert_eq!(before, journal_snapshot(&env));
    assert_eq!(env.journal.admit_new_write(), Err(Code::Unavailable));
}
#[test]
fn current_busy_and_oversized_are_explicit_without_fake_empty_bytes() {
    let f = Fixture::new(b"old");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, b"payload", false);
    let env = restart(&f, env);
    let before = journal_snapshot(&env);
    let held = HeldTarget::open(&f.target).unwrap();
    assert!(matches!(
        env.inspect_recovery(&s.operation).unwrap().current,
        CurrentTargetObservation::Busy
    ));
    drop(held);
    std::fs::write(&f.target, vec![42; MAX_SOURCE_BYTES + 1]).unwrap();
    assert!(matches!(
        env.inspect_recovery(&s.operation).unwrap().current,
        CurrentTargetObservation::Error {
            code: Code::TooLarge
        }
    ));
    assert_eq!(
        std::fs::metadata(&f.target).unwrap().len(),
        (MAX_SOURCE_BYTES + 1) as u64
    );
    assert_eq!(before, journal_snapshot(&env));
}
#[test]
fn read_only_current_attribute_is_observed_without_requesting_write_access() {
    let f = Fixture::new(b"old");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, b"payload", false);
    let env = restart(&f, env);
    let mut permissions = std::fs::metadata(&f.target).unwrap().permissions();
    permissions.set_readonly(true);
    std::fs::set_permissions(&f.target, permissions).unwrap();
    let before = journal_snapshot(&env);
    let metadata = std::fs::metadata(&f.target).unwrap();
    assert!(metadata.permissions().readonly());
    assert!(
        matches!(env.inspect_recovery(&s.operation).unwrap().current,
        CurrentTargetObservation::Changed { bytes, .. } if bytes == b"old")
    );
    let after = std::fs::metadata(&f.target).unwrap();
    assert_eq!(metadata.file_attributes(), after.file_attributes());
    assert_eq!(metadata.last_write_time(), after.last_write_time());
    assert_eq!(before, journal_snapshot(&env));
    assert_eq!(env.journal.admit_new_write(), Err(Code::Unavailable));
}
#[test]
fn corrupt_payload_backup_intent_and_receipt_are_rejected_on_each_inspection() {
    for kind in ["payload.bin", "backup.bin", "intent.json", "written.json"] {
        let f = Fixture::new(b"actual external");
        let env = WriterEnvironment::open_local(&f.storage).unwrap();
        let s = overwrite(&f, &env, b"payload", true);
        let env = restart(&f, env);
        env.inspect_recovery(&s.operation).unwrap();
        let artifact = env.journal.path(&s, kind).unwrap();
        std::fs::write(&artifact, b"corrupt").unwrap();
        let before = journal_snapshot(&env);
        let target_before = target_snapshot(&f.target);
        let catalog_before = serde_json::to_vec(env.recovery_records()).unwrap();
        assert!(env.inspect_recovery(&s.operation).is_err(), "{kind}");
        assert_eq!(before, journal_snapshot(&env));
        assert_eq!(target_before, target_snapshot(&f.target));
        assert_eq!(
            catalog_before,
            serde_json::to_vec(env.recovery_records()).unwrap()
        );
    }
}
#[test]
fn valid_looking_intent_redirection_and_same_byte_artifact_replacement_are_rejected() {
    for replace_payload in [false, true] {
        let f = Fixture::new(b"old");
        let env = WriterEnvironment::open_local(&f.storage).unwrap();
        let s = overwrite(&f, &env, b"captured", false);
        let env = restart(&f, env);
        if replace_payload {
            let path = env.journal.path(&s, "payload.bin").unwrap();
            std::fs::rename(&path, f.root.join("retained-payload.bin")).unwrap();
            std::fs::write(&path, b"captured").unwrap();
        } else {
            let path = env.journal.path(&s, "intent.json").unwrap();
            let mut intent: Intent =
                serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
            intent.path = f.root.join("redirected.cpp");
            intent.scope.operation = scope(b"captured").operation;
            std::fs::write(&path, serde_json::to_vec(&intent).unwrap()).unwrap();
        }
        let before = journal_snapshot(&env);
        assert!(matches!(
            env.inspect_recovery(&s.operation),
            Err(Code::Conflict)
        ));
        assert!(!f.root.join("redirected.cpp").exists());
        assert_eq!(before, journal_snapshot(&env));
        assert_eq!(std::fs::read(&f.target).unwrap(), b"old");
    }
}
#[test]
fn raw_payload_backup_and_current_accept_exactly_one_mib_and_reject_larger_artifacts() {
    let external = vec![255; MAX_SOURCE_BYTES];
    let payload = vec![254; MAX_SOURCE_BYTES];
    let f = Fixture::new(&external);
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let s = overwrite(&f, &env, &payload, false);
    let env = restart(&f, env);
    let inspection = env.inspect_recovery(&s.operation).unwrap();
    assert_eq!(inspection.payload, payload);
    assert_eq!(inspection.backup.as_ref(), Some(&external));
    assert!(
        matches!(inspection.current, CurrentTargetObservation::Unchanged { bytes, .. } if bytes == external)
    );
    for kind in ["payload.bin", "backup.bin"] {
        let path = env.journal.path(&s, kind).unwrap();
        let original = std::fs::read(&path).unwrap();
        std::fs::write(&path, vec![1; MAX_SOURCE_BYTES + 1]).unwrap();
        assert!(matches!(
            env.inspect_recovery(&s.operation),
            Err(Code::TooLarge)
        ));
        std::fs::write(&path, original).unwrap();
    }
    assert_eq!(env.journal.admit_new_write(), Err(Code::Unavailable));
}
#[test]
fn unfinished_create_inspects_payload_without_backup_or_target_creation() {
    let f = Fixture::new(b"unrelated");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let path = f.root.join("absent.cpp");
    let s = scope(b"create payload\0\xff");
    let namespace = CreateNamespace::open(&path).unwrap();
    let p = env
        .journal
        .prepare_create(&s, &namespace, b"create payload\0\xff")
        .unwrap();
    env.journal.mark_create_may_write(&s, &p).unwrap();
    drop(namespace);
    let env = restart(&f, env);
    let before = journal_snapshot(&env);
    let inspection = env.inspect_recovery(&s.operation).unwrap();
    assert_eq!(inspection.payload, b"create payload\0\xff");
    assert!(inspection.backup.is_none());
    assert!(matches!(
        inspection.current,
        CurrentTargetObservation::Missing
    ));
    assert!(!path.exists());
    std::fs::write(&path, b"later ordinary file").unwrap();
    assert!(
        matches!(env.inspect_recovery(&s.operation).unwrap().current,
        CurrentTargetObservation::Present { bytes, .. } if bytes == b"later ordinary file")
    );
    assert_eq!(before, journal_snapshot(&env));
    assert_eq!(env.journal.admit_new_write(), Err(Code::Unavailable));
}
#[test]
fn completed_create_inspects_exact_payload_and_historical_receipt_without_backup() {
    let f = Fixture::new(b"unrelated");
    let env = WriterEnvironment::open_local(&f.storage).unwrap();
    let path = f.root.join("created.cpp");
    let payload = b"created\0\xff\r\n";
    let s = scope(payload);
    let parent = windows_read::capture_parent_identity(&path).unwrap();
    let mut artifacts = None;
    let mut uncertain = false;
    assert!(matches!(
        crate::create_target::execute_create(
            &s,
            &path,
            &parent,
            payload,
            &AtomicBool::new(false),
            &env.journal,
            &mut artifacts,
            &mut uncertain,
        ),
        Ok(crate::create_target::CreatedEffect::Written(..))
    ));
    let env = restart(&f, env);
    let before = journal_snapshot(&env);
    let inspection = env.inspect_recovery(&s.operation).unwrap();
    assert_eq!(inspection.payload, payload);
    assert!(inspection.backup.is_none());
    assert_eq!(inspection.prior_record.phase, "written-receipt");
    assert!(
        matches!(inspection.current, CurrentTargetObservation::Unchanged { bytes, .. } if bytes == payload)
    );
    assert_eq!(before, journal_snapshot(&env));
    assert!(env.journal.admit_new_write().is_ok());
}
