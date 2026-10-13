//! TEST_ONLY host identities/picker and real Registry + Windows writer flows.
//! Every file is confined to a fresh GUID directory in this crate's test-tmp.
use super::*;
use crate::{
    Candidate, NativePicker, Outcome, PickerKind, ReadJob, Release, Request, Start, Status,
    TargetRequest, MAX_SETTLED_OPS, MAX_UNRESOLVED_OPS,
};
use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
};

struct TestFs {
    dir: PathBuf,
    storage: PathBuf,
}
impl TestFs {
    fn new() -> Self {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp");
        fs::create_dir_all(&root).unwrap();
        let nonce = crate::windows_read::random_hex().unwrap();
        let dir = root.join(format!(
            "writer-{}-{}-{}-{}-{}",
            &nonce[..8],
            &nonce[8..12],
            &nonce[12..16],
            &nonce[16..20],
            &nonce[20..]
        ));
        fs::create_dir(&dir).unwrap();
        let storage = dir.join("app-storage");
        fs::create_dir(&storage).unwrap();
        Self { dir, storage }
    }
    fn file(&self, name: &str, bytes: &[u8]) -> PathBuf {
        assert!(!name.contains(['\\', '/']));
        let path = self.dir.join(name);
        fs::write(&path, bytes).unwrap();
        path
    }
    fn environment(&self) -> WriterEnvironment {
        WriterEnvironment::open_local(&self.storage).unwrap()
    }
    fn artifact(&self, id: &RequestId, kind: &str) -> PathBuf {
        self.storage
            .join("cpp-recovery-v1")
            .join(format!("{}.{}", id.as_str(), kind))
    }
    fn artifacts(&self) -> BTreeMap<String, Vec<u8>> {
        // host.lock is held share0 for the environment lifetime. Compare every
        // actual operation artifact; never try to borrow its exclusive lease.
        fs::read_dir(self.storage.join("cpp-recovery-v1"))
            .unwrap()
            .map(|e| e.unwrap())
            .filter(|e| e.file_name() != "host.lock")
            .map(|e| {
                (
                    e.file_name().into_string().unwrap(),
                    fs::read(e.path()).unwrap(),
                )
            })
            .collect()
    }
}
impl Drop for TestFs {
    fn drop(&mut self) {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp");
        assert_eq!(self.dir.parent(), Some(root.as_path()));
        assert!(self
            .dir
            .file_name()
            .unwrap()
            .to_str()
            .unwrap()
            .starts_with("writer-"));
        assert!(!fs::symlink_metadata(&self.dir)
            .unwrap()
            .file_type()
            .is_symlink());
        if let Err(e) = fs::remove_dir_all(&self.dir) {
            eprintln!("TEST_ONLY writer fixture retained: {e}");
        }
    }
}
struct TestPicker {
    path: PathBuf,
    calls: usize,
}
impl NativePicker for TestPicker {
    fn select(&mut self, _: PickerKind) -> Result<Option<PathBuf>, Code> {
        self.calls += 1;
        Ok(Some(self.path.clone()))
    }
}
fn registry() -> (Registry, Caller) {
    let mut r = Registry::new().unwrap();
    let c = r.attach_caller().unwrap();
    (r, c)
}
fn read_work(start: Start) -> ReadJob {
    match start {
        Start::Work(job) => job,
        _ => panic!("expected real native read"),
    }
}
fn write_work(start: SaveStart) -> WriteJob {
    match start {
        SaveStart::Work(job) => job,
        SaveStart::Ready(v) => panic!("expected write work, got {}", v.phase),
    }
}
fn open(r: &mut Registry, c: &Caller, path: &Path) -> Candidate {
    let id = r.reserve(c, Operation::Open).unwrap();
    let job = read_work(r.open(c, Request { request_id: id }).unwrap());
    let mut picker = TestPicker {
        path: path.into(),
        calls: 0,
    };
    let status = r.complete(job.run(&mut picker)).unwrap();
    assert_eq!(picker.calls, 1);
    match status {
        Status::Complete {
            result: Outcome::Opened { document },
            ..
        } => document,
        _ => panic!("native open failed"),
    }
}
fn target(r: &mut Registry, c: &Caller, document: &DocumentId, path: &Path) -> crate::TargetId {
    let id = r
        .reserve(c, Operation::ChooseTarget(document.clone()))
        .unwrap();
    let job = read_work(
        r.choose_target(
            c,
            TargetRequest {
                request_id: id,
                document_id: document.clone(),
            },
        )
        .unwrap(),
    );
    let mut picker = TestPicker {
        path: path.into(),
        calls: 0,
    };
    let status = r.complete(job.run(&mut picker)).unwrap();
    assert_eq!(picker.calls, 1);
    match status {
        Status::Complete {
            result: Outcome::Selected {
                target_grant_id, ..
            },
            ..
        } => target_grant_id,
        _ => panic!("native target failed"),
    }
}
fn native_revision(path: &Path) -> Revision {
    let mut held = HeldTarget::open(path).unwrap();
    let revision = held.snapshot().unwrap();
    held.check_namespace().unwrap();
    revision
}
fn baseline(
    r: &Registry,
    c: &Caller,
    doc: &DocumentId,
    version: &Version,
    path: &Path,
    bytes: &[u8],
) {
    let d = r.document(c, doc).unwrap();
    assert_eq!(d.version.as_ref(), Some(version));
    let s = d.selection.as_ref().unwrap();
    assert_eq!(s.path, path);
    assert_eq!(s.bytes, bytes);
    assert_eq!(s.sha256, Some(windows_write::digest_raw(bytes)));
    assert_eq!(s.writer_revision.as_ref(), Some(&native_revision(path)));
    let grant = r.owned_job_source_grant(c, doc, version).unwrap();
    assert_eq!(grant.bytes(), bytes);
    assert_eq!(grant.hash().unwrap(), windows_write::digest_raw(bytes));
    assert_eq!(fs::read(path).unwrap(), bytes);
}
fn save(
    r: &mut Registry,
    c: &Caller,
    doc: &DocumentId,
    version: &Version,
    bytes: &[u8],
    env: &mut WriterEnvironment,
) -> (RequestId, Version) {
    let id = r.reserve_save(c, doc, version, bytes.to_vec()).unwrap();
    let reserved = r.save_reserved_version(c, &id).unwrap();
    assert_ne!(&reserved, version);
    let job = write_work(r.begin_save(c, &id).unwrap());
    let completion = job.run(env);
    let view = r.complete_save(completion).unwrap();
    assert_eq!(view.phase, "written");
    assert_eq!(view.captured_version.as_ref(), Some(version));
    let adoption = view.adoption.unwrap();
    assert_eq!(adoption.document_id, *doc);
    assert_eq!(adoption.version, reserved);
    (id, reserved)
}
fn assert_replay(
    r: &mut Registry,
    c: &Caller,
    id: &RequestId,
    files: &TestFs,
    path: &Path,
    env: &mut WriterEnvironment,
) {
    let revision = native_revision(path);
    let artifacts = files.artifacts();
    let counts = r.counts();
    let view = r.save_view(c, id).unwrap();
    for _ in 0..3 {
        let SaveStart::Ready(replay) = r.begin_save(c, id).unwrap() else {
            panic!("replay dispatched a write")
        };
        assert_eq!(replay.phase, view.phase);
        let SaveStart::Ready(replay) = r
            .confirm_save(c, id, ConflictDecision::OverwriteWithActualBackup)
            .unwrap()
        else {
            panic!("terminal confirmation dispatched a write")
        };
        assert_eq!(replay.phase, view.phase);
        assert_eq!(r.recover_save(c, id, env).unwrap().phase, view.phase);
    }
    assert_eq!(native_revision(path), revision);
    assert_eq!(files.artifacts(), artifacts);
    assert_eq!(r.counts(), counts);
}
// TEST_ONLY delivery fault: retain a genuine native Written receipt but lose
// its in-memory selection delivery. Never fabricate a successful native effect.
fn lose_written_delivery(mut completion: WriteCompletion) -> WriteCompletion {
    completion.effect = match completion.effect {
        Effect::Written(prepared, _) => Effect::Unknown(Some(prepared)),
        _ => panic!("delivery fault requires a real successful write"),
    };
    completion
}

#[test]
fn repeated_ordinary_saves_adopt_exact_native_baseline_and_reserved_version() {
    let files = TestFs::new();
    let mut env = files.environment();
    let original = b"// original\r\n";
    let path = files.file("source.cpp", original);
    let (mut r, c) = registry();
    let doc = open(&mut r, &c, &path);
    let mut version = doc.binding.unwrap().version;
    let payloads = [
        "\u{feff}// Příliš žluťoučký 🧪\r\nvoid f(){}\n"
            .as_bytes()
            .to_vec(),
        vec![0, 255, 195, 40, 13, 10],
        Vec::new(),
        vec![b'x'; crate::MAX_SOURCE_BYTES],
    ];
    let mut previous = original.to_vec();
    for bytes in payloads {
        let old = version.clone();
        let (id, next) = save(&mut r, &c, &doc.document_id, &version, &bytes, &mut env);
        assert_eq!(
            fs::read(files.artifact(&id, "backup.bin")).unwrap(),
            previous
        );
        baseline(&r, &c, &doc.document_id, &next, &path, &bytes);
        assert!(matches!(
            r.reserve_save(&c, &doc.document_id, &old, b"stale".to_vec()),
            Err(Code::Conflict)
        ));
        assert_replay(&mut r, &c, &id, &files, &path, &mut env);
        previous = bytes;
        version = next;
        assert_eq!(r.counts().2, 0);
    }
}

#[test]
fn more_than_32_real_terminal_saves_are_bounded_and_evicted_replays_never_mutate() {
    let files = TestFs::new();
    let mut env = files.environment();
    let path = files.file("many.cpp", b"0");
    let (mut r, c) = registry();
    let doc = open(&mut r, &c, &path);
    let mut version = doc.binding.unwrap().version;
    let unresolved = r.reserve(&c, Operation::Open).unwrap();
    let mut first = None;
    let mut last = None;
    for n in 0..MAX_SETTLED_OPS + 5 {
        let bytes = format!("// native save {n}\r\n").into_bytes();
        let (id, next) = save(&mut r, &c, &doc.document_id, &version, &bytes, &mut env);
        if first.is_none() {
            first = Some(id.clone());
        }
        last = Some(id);
        version = next;
        assert_eq!(r.counts().2, 1);
        assert!(r.counts().1 <= MAX_SETTLED_OPS);
    }
    assert_eq!(r.counts(), (1, MAX_SETTLED_OPS, 1));
    assert!(matches!(
        r.status(&c, &unresolved).unwrap(),
        Status::Reserved
    ));
    let revision = native_revision(&path);
    let artifacts = files.artifacts();
    let first = first.unwrap();
    assert!(matches!(
        r.begin_save(&c, &first),
        Err(Code::UnknownRequest)
    ));
    assert!(matches!(
        r.confirm_save(&c, &first, ConflictDecision::OverwriteWithActualBackup),
        Err(Code::UnknownRequest)
    ));
    assert!(matches!(
        r.recover_save(&c, &first, &mut env),
        Err(Code::UnknownRequest)
    ));
    assert_eq!(native_revision(&path), revision);
    assert_eq!(files.artifacts(), artifacts);
    assert_replay(&mut r, &c, &last.unwrap(), &files, &path, &mut env);
}

#[test]
fn ordinary_external_conflict_requires_exact_confirmation_and_actual_backup() {
    let files = TestFs::new();
    let mut env = files.environment();
    let path = files.file("conflict.cpp", b"baseline");
    let (mut r, c) = registry();
    let doc = open(&mut r, &c, &path);
    let version = doc.binding.unwrap().version;
    let id = r
        .reserve_save(
            &c,
            &doc.document_id,
            &version,
            b"captured new bytes".to_vec(),
        )
        .unwrap();
    fs::write(&path, b"actual external bytes").unwrap();
    let job = write_work(r.begin_save(&c, &id).unwrap());
    let view = r.complete_save(job.run(&mut env)).unwrap();
    assert_eq!(view.phase, "external-conflict");
    assert_eq!(
        view.external_hash,
        Some(windows_write::digest(b"actual external bytes"))
    );
    assert!(files.artifacts().is_empty());
    assert_eq!(r.counts().2, 1);
    assert!(matches!(
        r.release(
            &c,
            Release::Document {
                document_id: doc.document_id.clone()
            }
        ),
        Err(Code::Busy)
    ));
    let SaveStart::Ready(replay) = r.begin_save(&c, &id).unwrap() else {
        panic!("conflict replay wrote")
    };
    assert_eq!(replay.phase, "external-conflict");
    let job = write_work(
        r.confirm_save(&c, &id, ConflictDecision::OverwriteWithActualBackup)
            .unwrap(),
    );
    let view = r.complete_save(job.run(&mut env)).unwrap();
    assert_eq!(view.phase, "written");
    let next = view.adoption.unwrap().version;
    assert_eq!(
        fs::read(files.artifact(&id, "backup.bin")).unwrap(),
        b"actual external bytes"
    );
    baseline(
        &r,
        &c,
        &doc.document_id,
        &next,
        &path,
        b"captured new bytes",
    );
}

#[test]
fn changed_confirmed_observation_stops_without_retry_or_backup_claim() {
    let files = TestFs::new();
    let mut env = files.environment();
    let path = files.file("changed.cpp", b"baseline");
    let (mut r, c) = registry();
    let doc = open(&mut r, &c, &path);
    let version = doc.binding.unwrap().version;
    let id = r
        .reserve_save(&c, &doc.document_id, &version, b"new".to_vec())
        .unwrap();
    fs::write(&path, b"external A").unwrap();
    let job = write_work(r.begin_save(&c, &id).unwrap());
    assert_eq!(
        r.complete_save(job.run(&mut env)).unwrap().phase,
        "external-conflict"
    );
    let job = write_work(
        r.confirm_save(&c, &id, ConflictDecision::OverwriteWithActualBackup)
            .unwrap(),
    );
    fs::write(&path, b"external B").unwrap();
    let view = r.complete_save(job.run(&mut env)).unwrap();
    assert_eq!(view.phase, "not-started");
    assert_eq!(view.reason, Some(Code::Conflict));
    assert!(view.adoption.is_none());
    assert_eq!(fs::read(&path).unwrap(), b"external B");
    assert!(files.artifacts().is_empty());
    assert_eq!(r.counts().2, 0);
    assert_replay(&mut r, &c, &id, &files, &path, &mut env);
}

#[test]
fn save_as_existing_target_requires_conflict_stop_or_approved_actual_backup() {
    let files = TestFs::new();
    let mut env = files.environment();
    let path = files.file("existing.cpp", b"target baseline");
    let (mut r, c) = registry();
    let bytes = vec![0xef, 0xbb, 0xbf, 0xff, 0, 13, 10];
    let draft = r.bind_captured_draft(&c, 73, bytes.clone()).unwrap();
    let t = target(&mut r, &c, &draft.document_id, &path);
    let id = r
        .reserve_save_as(&c, &draft.document_id, &t, 73, bytes.clone())
        .unwrap();
    let job = write_work(r.begin_save(&c, &id).unwrap());
    let view = r.complete_save(job.run(&mut env)).unwrap();
    assert_eq!(view.phase, "external-conflict");
    assert_eq!(view.external_bytes, Some(b"target baseline".len()));
    assert!(view.adoption.is_none());
    assert!(files.artifacts().is_empty());
    let SaveStart::Ready(view) = r.confirm_save(&c, &id, ConflictDecision::Stop).unwrap() else {
        panic!("Stop wrote")
    };
    assert_eq!(view.phase, "not-started");
    assert_eq!(fs::read(&path).unwrap(), b"target baseline");
    assert!(r
        .document(&c, &draft.document_id)
        .unwrap()
        .selection
        .is_none());
    assert_replay(&mut r, &c, &id, &files, &path, &mut env);
    let t = target(&mut r, &c, &draft.document_id, &path);
    let id = r
        .reserve_save_as(&c, &draft.document_id, &t, 73, bytes.clone())
        .unwrap();
    let reserved = r.save_as_reserved_version(&c, &id).unwrap();
    fs::write(&path, b"actual external target").unwrap();
    let job = write_work(r.begin_save(&c, &id).unwrap());
    assert_eq!(
        r.complete_save(job.run(&mut env)).unwrap().phase,
        "external-conflict"
    );
    let job = write_work(
        r.confirm_save(&c, &id, ConflictDecision::OverwriteWithActualBackup)
            .unwrap(),
    );
    let view = r.complete_save(job.run(&mut env)).unwrap();
    assert_eq!(view.phase, "written");
    assert_eq!(view.adoption.unwrap().version, reserved);
    assert_eq!(
        fs::read(files.artifact(&id, "backup.bin")).unwrap(),
        b"actual external target"
    );
    baseline(&r, &c, &draft.document_id, &reserved, &path, &bytes);
    assert!(r
        .document(&c, &draft.document_id)
        .unwrap()
        .draft_capture
        .is_none());
    let (_, next) = save(
        &mut r,
        &c,
        &draft.document_id,
        &reserved,
        b"ordinary after Save As",
        &mut env,
    );
    baseline(
        &r,
        &c,
        &draft.document_id,
        &next,
        &path,
        b"ordinary after Save As",
    );
}

#[test]
fn save_as_absent_create_adopts_and_appearance_requires_confirmation() {
    let files = TestFs::new();
    let mut env = files.environment();
    let (mut r, c) = registry();
    for appears in [false, true] {
        let path = files.dir.join(if appears {
            "appeared.cpp"
        } else {
            "created.cpp"
        });
        let draft = r.bind_captured_draft(&c, 5, b"captured".to_vec()).unwrap();
        let t = target(&mut r, &c, &draft.document_id, &path);
        let id = r
            .reserve_save_as(&c, &draft.document_id, &t, 5, b"captured".to_vec())
            .unwrap();
        let reserved = r.save_as_reserved_version(&c, &id).unwrap();
        if appears {
            fs::write(&path, b"appeared externally").unwrap();
        }
        let job = write_work(r.begin_save(&c, &id).unwrap());
        let mut view = r.complete_save(job.run(&mut env)).unwrap();
        if appears {
            assert_eq!(view.phase, "external-conflict");
            assert_eq!(fs::read(&path).unwrap(), b"appeared externally");
            let job = write_work(
                r.confirm_save(&c, &id, ConflictDecision::OverwriteWithActualBackup)
                    .unwrap(),
            );
            view = r.complete_save(job.run(&mut env)).unwrap();
            assert_eq!(
                fs::read(files.artifact(&id, "backup.bin")).unwrap(),
                b"appeared externally"
            );
        }
        assert_eq!(view.phase, "written");
        assert_eq!(view.adoption.unwrap().version, reserved);
        baseline(&r, &c, &draft.document_id, &reserved, &path, b"captured");
        assert_replay(&mut r, &c, &id, &files, &path, &mut env);
    }
}

#[test]
fn unknown_recovery_verifies_real_receipts_adopts_original_version_and_never_retries() {
    let files = TestFs::new();
    let mut env = files.environment();
    let path = files.file("recover.cpp", b"old");
    let (mut r, c) = registry();
    let doc = open(&mut r, &c, &path);
    let version = doc.binding.unwrap().version;
    let id = r
        .reserve_save(&c, &doc.document_id, &version, b"recovered".to_vec())
        .unwrap();
    let reserved = r.save_reserved_version(&c, &id).unwrap();
    let job = write_work(r.begin_save(&c, &id).unwrap());
    let completion = lose_written_delivery(job.run(&mut env));
    assert_eq!(
        r.complete_save(completion).unwrap().phase,
        "recovery-required"
    );
    assert_eq!(
        r.document(&c, &doc.document_id).unwrap().version.as_ref(),
        Some(&version)
    );
    assert_eq!(r.counts().2, 1);
    assert!(matches!(
        r.release(
            &c,
            Release::Document {
                document_id: doc.document_id.clone()
            }
        ),
        Err(Code::Busy)
    ));
    let revision = native_revision(&path);
    let artifacts = files.artifacts();
    let SaveStart::Ready(view) = r.begin_save(&c, &id).unwrap() else {
        panic!("unknown retried")
    };
    assert_eq!(view.phase, "recovery-required");
    let view = r.recover_save(&c, &id, &mut env).unwrap();
    assert_eq!(view.phase, "written");
    assert_eq!(view.adoption.unwrap().version, reserved);
    assert_eq!(native_revision(&path), revision);
    assert_eq!(files.artifacts(), artifacts);
    assert_eq!(r.counts().2, 0);
    baseline(&r, &c, &doc.document_id, &reserved, &path, b"recovered");
    assert_replay(&mut r, &c, &id, &files, &path, &mut env);
}

#[test]
fn byte_equal_target_without_trusted_receipt_stays_unknown() {
    let files = TestFs::new();
    let mut env = files.environment();
    let path = files.file("untrusted.cpp", b"old");
    let (mut r, c) = registry();
    let doc = open(&mut r, &c, &path);
    let version = doc.binding.unwrap().version;
    let id = r
        .reserve_save(
            &c,
            &doc.document_id,
            &version,
            b"same real new bytes".to_vec(),
        )
        .unwrap();
    let job = write_work(r.begin_save(&c, &id).unwrap());
    let completion = lose_written_delivery(job.run(&mut env));
    r.complete_save(completion).unwrap();
    fs::write(files.artifact(&id, "written.json"), b"{}").unwrap();
    let revision = native_revision(&path);
    let artifacts = files.artifacts();
    let view = r.recover_save(&c, &id, &mut env).unwrap();
    assert_eq!(view.phase, "recovery-required");
    assert!(view.adoption.is_none());
    assert_eq!(
        r.document(&c, &doc.document_id).unwrap().version.as_ref(),
        Some(&version)
    );
    assert_eq!(native_revision(&path), revision);
    assert_eq!(files.artifacts(), artifacts);
    assert_eq!(r.counts().2, 1);
    assert!(matches!(
        r.release(
            &c,
            Release::Document {
                document_id: doc.document_id
            }
        ),
        Err(Code::Busy)
    ));
}

#[test]
fn cancellation_before_write_and_after_native_effect_preserves_real_outcome() {
    let files = TestFs::new();
    let mut env = files.environment();
    let path = files.file("cancel.cpp", b"old");
    let (mut r, c) = registry();
    let doc = open(&mut r, &c, &path);
    let version = doc.binding.unwrap().version;
    let id = r
        .reserve_save(&c, &doc.document_id, &version, b"never written".to_vec())
        .unwrap();
    let job = write_work(r.begin_save(&c, &id).unwrap());
    r.cancel(&c, &id).unwrap();
    let view = r.complete_save(job.run(&mut env)).unwrap();
    assert_eq!(view.phase, "not-started");
    assert_eq!(view.reason, Some(Code::Revoked));
    baseline(&r, &c, &doc.document_id, &version, &path, b"old");
    assert!(files.artifacts().is_empty());
    let id = r
        .reserve_save(&c, &doc.document_id, &version, b"actually written".to_vec())
        .unwrap();
    let reserved = r.save_reserved_version(&c, &id).unwrap();
    let job = write_work(r.begin_save(&c, &id).unwrap());
    let completion = job.run(&mut env);
    r.cancel(&c, &id).unwrap();
    let view = r.complete_save(completion).unwrap();
    assert_eq!(view.phase, "written");
    assert!(view.cancel_requested);
    assert_eq!(view.adoption.unwrap().version, reserved);
    baseline(
        &r,
        &c,
        &doc.document_id,
        &reserved,
        &path,
        b"actually written",
    );
    let Status::Save { write } = r.cancel(&c, &id).unwrap() else {
        panic!()
    };
    assert_eq!(write.phase, "written");
    assert_replay(&mut r, &c, &id, &files, &path, &mut env);
}

#[test]
fn revoke_running_retains_evidence_until_drain_and_never_grants_fresh_owner() {
    let files = TestFs::new();
    let mut env = files.environment();
    for already_written in [false, true] {
        let path = files.file(
            if already_written {
                "revoked-written.cpp"
            } else {
                "revoked-before.cpp"
            },
            b"old",
        );
        let (mut r, c) = registry();
        let doc = open(&mut r, &c, &path);
        let version = doc.binding.unwrap().version;
        let id = r
            .reserve_save(&c, &doc.document_id, &version, b"new".to_vec())
            .unwrap();
        let job = write_work(r.begin_save(&c, &id).unwrap());
        let completion = if already_written {
            let completion = job.run(&mut env);
            r.revoke_caller(&c).unwrap();
            completion
        } else {
            r.revoke_caller(&c).unwrap();
            job.run(&mut env)
        };
        assert!(r.documents.contains_key(&doc.document_id));
        assert_eq!(r.counts().2, 1);
        let fresh = r.attach_caller().unwrap();
        assert_ne!(fresh, c);
        let view = r.complete_save(completion).unwrap();
        assert!(view.adoption.is_none());
        assert!(view.cancel_requested);
        assert_eq!(
            view.phase,
            if already_written {
                "written"
            } else {
                "not-started"
            }
        );
        assert_eq!(
            fs::read(&path).unwrap(),
            if already_written { b"new" } else { b"old" }
        );
        assert_eq!(r.counts().2, 0);
        assert!(!r.documents.contains_key(&doc.document_id));
        assert!(matches!(r.begin_save(&c, &id), Err(Code::Denied)));
        assert!(matches!(
            r.recover_save(&fresh, &id, &mut env),
            Err(Code::Denied)
        ));
    }
}

#[test]
fn late_native_completion_cannot_adopt_changed_version_bytes_or_owner() {
    let files = TestFs::new();
    let mut env = files.environment();
    for change in 0..3 {
        let path = files.file(&format!("guard-{change}.cpp"), b"old");
        let (mut r, c) = registry();
        let doc = open(&mut r, &c, &path);
        let version = doc.binding.unwrap().version;
        let id = r
            .reserve_save(&c, &doc.document_id, &version, b"written snapshot".to_vec())
            .unwrap();
        let job = write_work(r.begin_save(&c, &id).unwrap());
        let completion = job.run(&mut env);
        // TEST_ONLY simulate host owner/source drift between native execution
        // and delivery; no caller-facing API can supply these changes.
        let fresh = r.attach_caller().unwrap();
        let d = r.documents.get_mut(&doc.document_id).unwrap();
        match change {
            0 => d.version = Some(Version::mint().unwrap()),
            1 => d.selection.as_mut().unwrap().bytes = b"newer captured source".to_vec(),
            _ => d.owner = fresh.clone(),
        }
        let expected_version = d.version.clone();
        let expected_bytes = d.selection.as_ref().unwrap().bytes.clone();
        let owner = d.owner.clone();
        let view = r.complete_save(completion).unwrap();
        assert_eq!(view.phase, "written");
        assert!(view.adoption.is_none());
        let d = r.document(&owner, &doc.document_id).unwrap();
        assert_eq!(d.version, expected_version);
        assert_eq!(d.selection.as_ref().unwrap().bytes, expected_bytes);
        assert_eq!(fs::read(&path).unwrap(), b"written snapshot");
        assert_replay(&mut r, &c, &id, &files, &path, &mut env);
    }
}

#[test]
fn save_as_unknown_recovery_respects_original_capture_and_newer_draft() {
    let files = TestFs::new();
    let mut env = files.environment();
    let (mut r, c) = registry();
    for newer in [false, true] {
        let path = files.dir.join(if newer {
            "newer-draft.cpp"
        } else {
            "recovered-draft.cpp"
        });
        let draft = r
            .bind_captured_draft(&c, 91, b"captured draft".to_vec())
            .unwrap();
        let t = target(&mut r, &c, &draft.document_id, &path);
        let id = r
            .reserve_save_as(&c, &draft.document_id, &t, 91, b"captured draft".to_vec())
            .unwrap();
        let reserved = r.save_as_reserved_version(&c, &id).unwrap();
        let job = write_work(r.begin_save(&c, &id).unwrap());
        let completion = lose_written_delivery(job.run(&mut env));
        r.complete_save(completion).unwrap();
        if newer {
            // TEST_ONLY source remains byte-equal but owner capture has advanced.
            r.documents
                .get_mut(&draft.document_id)
                .unwrap()
                .draft_capture
                .as_mut()
                .unwrap()
                .revision = 92;
        }
        let artifacts = files.artifacts();
        let revision = native_revision(&path);
        let view = r.recover_save(&c, &id, &mut env).unwrap();
        assert_eq!(view.phase, "written");
        assert_eq!(native_revision(&path), revision);
        assert_eq!(files.artifacts(), artifacts);
        if newer {
            assert!(view.adoption.is_none());
            let d = r.document(&c, &draft.document_id).unwrap();
            assert!(d.selection.is_none());
            assert!(d.version.is_none());
            assert_eq!(d.draft_capture.as_ref().unwrap().revision, 92);
        } else {
            assert_eq!(view.adoption.unwrap().version, reserved);
            baseline(
                &r,
                &c,
                &draft.document_id,
                &reserved,
                &path,
                b"captured draft",
            );
        }
    }
}

#[test]
fn running_conflict_unknown_survive_history_churn_and_block_grant_release() {
    let files = TestFs::new();
    let mut env = files.environment();
    for state in 0..3 {
        let path = files.file(&format!("held-{state}.cpp"), b"old");
        let (mut r, c) = registry();
        let doc = open(&mut r, &c, &path);
        let version = doc.binding.unwrap().version;
        let other = r.attach_caller().unwrap();
        let churn_path = files.file(&format!("churn-{state}.cpp"), b"churn baseline");
        let churn_doc = open(&mut r, &other, &churn_path);
        let churn_version = churn_doc.binding.unwrap().version;
        let id = r
            .reserve_save(&c, &doc.document_id, &version, b"new".to_vec())
            .unwrap();
        if state == 1 {
            fs::write(&path, b"external").unwrap();
        }
        let job = write_work(r.begin_save(&c, &id).unwrap());
        let mut running = None;
        if state == 0 {
            running = Some(job);
        } else {
            let completion = job.run(&mut env);
            let completion = if state == 2 {
                lose_written_delivery(completion)
            } else {
                completion
            };
            r.complete_save(completion).unwrap();
        }
        let expected = r.save_view(&c, &id).unwrap().phase;
        let artifacts = files.artifacts();
        let bytes = fs::read(&path).unwrap();
        for _ in 0..MAX_SETTLED_OPS + 2 {
            let terminal = r
                .reserve_save(
                    &other,
                    &churn_doc.document_id,
                    &churn_version,
                    b"not dispatched".to_vec(),
                )
                .unwrap();
            r.cancel(&other, &terminal).unwrap();
        }
        assert_eq!(r.counts(), (2, MAX_SETTLED_OPS, 1));
        assert_eq!(r.save_view(&c, &id).unwrap().phase, expected);
        assert!(matches!(
            r.release(
                &c,
                Release::Document {
                    document_id: doc.document_id.clone()
                }
            ),
            Err(Code::Busy)
        ));
        let SaveStart::Ready(view) = r.begin_save(&c, &id).unwrap() else {
            panic!("unresolved replay dispatched")
        };
        assert_eq!(view.phase, expected);
        assert_eq!(fs::read(&path).unwrap(), bytes);
        assert_eq!(files.artifacts(), artifacts);
        if let Some(job) = running {
            r.complete_save(job.undispatched()).unwrap();
        } else if state == 1 {
            r.confirm_save(&c, &id, ConflictDecision::Stop).unwrap();
        } else {
            r.recover_save(&c, &id, &mut env).unwrap();
        }
        assert_eq!(r.counts().2, 0);
        r.release(
            &c,
            Release::Document {
                document_id: doc.document_id,
            },
        )
        .unwrap();
    }
}

#[test]
fn terminal_cancel_and_undispatched_jobs_release_unresolved_capacity_once() {
    let files = TestFs::new();
    let _env = files.environment();
    let path = files.file("capacity.cpp", b"old");
    let (mut r, c) = registry();
    let doc = open(&mut r, &c, &path);
    let version = doc.binding.unwrap().version;
    for n in 0..MAX_UNRESOLVED_OPS + 8 {
        let id = r
            .reserve_save(&c, &doc.document_id, &version, b"not dispatched".to_vec())
            .unwrap();
        if n % 2 == 0 {
            r.cancel(&c, &id).unwrap();
            r.cancel(&c, &id).unwrap();
        } else {
            let job = write_work(r.begin_save(&c, &id).unwrap());
            r.complete_save(job.undispatched()).unwrap();
        }
        let counts = r.counts();
        let SaveStart::Ready(v) = r.begin_save(&c, &id).unwrap() else {
            panic!()
        };
        assert_eq!(v.phase, "not-started");
        assert_eq!(r.counts(), counts);
        assert_eq!(counts.2, 0);
    }
    assert_eq!(fs::read(&path).unwrap(), b"old");
    assert!(files.artifacts().is_empty());
}
