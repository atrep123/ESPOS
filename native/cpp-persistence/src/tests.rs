//! TEST_ONLY callers/pickers. Filesystem fixtures use actual Windows files under
//! this staged crate only. No test produces or accepts a native save receipt.
use super::*;
use std::{
    fs,
    os::windows::fs::OpenOptionsExt,
    path::{Path, PathBuf},
};

struct TestFs {
    dir: PathBuf,
}
impl TestFs {
    fn new() -> Self {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp");
        assert!(root.starts_with(PathBuf::from(env!("CARGO_MANIFEST_DIR"))));
        fs::create_dir_all(&root).unwrap();
        let dir = root.join(format!("fixture-{}", windows_read::random_hex().unwrap()));
        fs::create_dir(&dir).unwrap();
        Self { dir }
    }
    fn file(&self, name: &str, bytes: &[u8]) -> PathBuf {
        let path = self.dir.join(name);
        fs::write(&path, bytes).unwrap();
        path
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
            .starts_with("fixture-"));
        // Only this test's fresh directory; do not follow any directory symlink.
        if let Err(error) = fs::remove_dir_all(&self.dir) {
            eprintln!("TEST_ONLY fixture retained: {error}");
        }
    }
}
struct TestPicker {
    path: Option<PathBuf>,
    calls: usize,
}
impl NativePicker for TestPicker {
    fn select(&mut self, _: PickerKind) -> Result<Option<PathBuf>, Code> {
        self.calls += 1;
        Ok(self.path.clone())
    }
}
fn fixture() -> (Registry, Caller) {
    let mut r = Registry::new().unwrap();
    let c = r.attach_caller().unwrap();
    (r, c)
}
fn req(id: &RequestId) -> Request {
    Request {
        request_id: id.clone(),
    }
}
fn work(start: Start) -> ReadJob {
    match start {
        Start::Work(job) => job,
        _ => panic!("expected actual read work"),
    }
}
fn candidate(status: Status) -> Candidate {
    match status {
        Status::Complete {
            result: Outcome::Opened { document } | Outcome::Created { document },
            ..
        } => document,
        _ => panic!("expected candidate"),
    }
}
fn create(r: &mut Registry, c: &Caller) -> (RequestId, Candidate) {
    let id = r.reserve(c, Operation::New).unwrap();
    match r.new_document(c, req(&id)).unwrap() {
        Start::Ready(status) => (id, candidate(status)),
        _ => panic!(),
    }
}
fn open_file(r: &mut Registry, c: &Caller, path: &Path) -> (RequestId, Candidate) {
    let id = r.reserve(c, Operation::Open).unwrap();
    let job = work(r.open(c, req(&id)).unwrap());
    let mut picker = TestPicker {
        path: Some(path.to_owned()),
        calls: 0,
    };
    let result = r.complete(job.run(&mut picker)).unwrap();
    assert_eq!(picker.calls, 1);
    (id, candidate(result))
}
fn is_failed(status: Status, expected: Code) {
    assert!(
        matches!(status,Status::Complete {result:Outcome::Failed {code,..},..} if code==expected)
    );
}
#[test]
fn strict_json_types_unknown_duplicate_nested_and_path_fields() {
    let (mut r, c) = fixture();
    let id = r.reserve(&c, Operation::New).unwrap();
    let valid = format!(r#"{{"requestId":"{}"}}"#, id.as_str());
    assert!(decode_request::<Request>(valid.as_bytes()).is_ok());
    for payload in [
        format!(r#"{{"requestId":"{}","path":"C:\\secret"}}"#, id.as_str()),
        format!(
            r#"{{"requestId":"{}","caller":{{"window":"main"}}}}"#,
            id.as_str()
        ),
        format!(
            r#"{{"requestId":"{}","requestId":"{}"}}"#,
            id.as_str(),
            id.as_str()
        ),
        r#"{"requestId":1}"#.into(),
        r#"{"requestId":"C:\\x"}"#.into(),
    ] {
        assert!(matches!(
            decode_request::<Request>(payload.as_bytes()),
            Err(Code::InvalidInput)
        ));
    }
    assert!(matches!(
        decode_request::<Request>(&vec![b' '; 1025]),
        Err(Code::TooLarge)
    ));
    let (_, doc) = create(&mut r, &c);
    let unknown = format!(
        r#"{{"kind":"document","documentId":"{}","root":"C:\\"}}"#,
        doc.document_id.as_str()
    );
    assert!(decode_request::<Release>(unknown.as_bytes()).is_err());
    let target = format!(
        r#"{{"requestId":"{}","documentId":"{}","path":"x"}}"#,
        id.as_str(),
        doc.document_id.as_str()
    );
    assert!(decode_request::<TargetRequest>(target.as_bytes()).is_err());
}
#[test]
fn strict_base64_size_and_byte_validation_has_no_writer() {
    let exact = vec![255; MAX_SOURCE_BYTES];
    assert_eq!(decode_source(&STANDARD.encode(&exact)).unwrap(), exact);
    assert_eq!(
        decode_source(&STANDARD.encode(vec![1; MAX_SOURCE_BYTES + 1])),
        Err(Code::TooLarge)
    );
    for bad in ["/x==", "YQ", "YQ==\n", "====", "é"] {
        assert_eq!(decode_source(bad), Err(Code::InvalidInput));
    }
    assert!(decode_source("").unwrap().is_empty());
}
#[test]
fn reservation_payload_has_fixed_intents_and_no_frontend_authority() {
    let (mut r, c) = fixture();
    let new = decode_request::<ReserveRequest>(br#"{"operation":"new"}"#).unwrap();
    let id = r.reserve_request(&c, new).unwrap();
    let doc = match r.new_document(&c, req(&id)).unwrap() {
        Start::Ready(status) => candidate(status),
        _ => panic!(),
    };
    let payload = format!(
        r#"{{"operation":"chooseTarget","documentId":"{}"}}"#,
        doc.document_id.as_str()
    );
    let target = r
        .reserve_request(&c, decode_request(payload.as_bytes()).unwrap())
        .unwrap();
    assert!(matches!(r.open(&c, req(&target)), Err(Code::InvalidInput)));
    assert!(matches!(r.status(&c, &target).unwrap(), Status::Reserved));
    let other = r.attach_caller().unwrap();
    assert_eq!(
        r.reserve_request(&other, decode_request(payload.as_bytes()).unwrap()),
        Err(Code::Denied)
    );
    for bad in [
        r#"{"operation":"save"}"#,
        r#"{"operation":"open","path":"C:\\secret.cpp"}"#,
        r#"{"operation":"new","requestId":"request_00000000000000000000000000000000"}"#,
        r#"{"operation":"open","caller":"main"}"#,
        r#"{"operation":"open","operation":"new"}"#,
        r#"{"operation":"new","documentId":"doc_00000000000000000000000000000000"}"#,
        r#"{"operation":"chooseTarget"}"#,
        r#"{"operation":"chooseTarget","documentId":"C:\\x.cpp"}"#,
        r#"{"operation":{"kind":"open"}}"#,
    ] {
        assert!(
            matches!(
                decode_request::<ReserveRequest>(bad.as_bytes()),
                Err(Code::InvalidInput)
            ),
            "accepted unauthorized reservation payload: {bad}"
        );
    }
    assert!(matches!(
        decode_request::<ReserveRequest>(&vec![b' '; MAX_REQUEST_JSON_BYTES + 1]),
        Err(Code::TooLarge)
    ));
}
#[test]
fn new_empty_is_never_saved_and_idempotent() {
    let (mut r, c) = fixture();
    let (id, doc) = create(&mut r, &c);
    assert_eq!(doc.source_base64, "");
    assert!(doc.saved_base64.is_none());
    assert!(doc.binding.is_none());
    match r.new_document(&c, req(&id)).unwrap() {
        Start::Ready(status) => assert_eq!(candidate(status).document_id, doc.document_id),
        _ => panic!(),
    }
    assert_eq!(r.counts(), (1, 1, 0));
}
#[test]
fn real_native_byte_exact_empty_czech_bom_eol_invalid_utf8_and_limit() {
    let files = TestFs::new();
    for bytes in [
        Vec::new(),
        "\u{feff}// Příliš žluťoučký 🧪\r\nvoid step(){}\n//end"
            .as_bytes()
            .to_vec(),
        vec![0, 255, 195, 40, 13, 10],
        vec![b'a'; MAX_SOURCE_BYTES],
    ] {
        let path = files.file("actual.cpp", &bytes);
        let (mut r, c) = fixture();
        let (_, doc) = open_file(&mut r, &c, &path);
        assert_eq!(decode_source(&doc.source_base64).unwrap(), bytes);
        assert_eq!(doc.saved_base64, Some(doc.source_base64.clone()));
        assert!(doc.binding.is_some());
        assert_eq!(fs::read(&path).unwrap(), bytes);
        let selected = r
            .documents
            .get(&doc.document_id)
            .unwrap()
            .selection
            .as_ref()
            .unwrap();
        assert!(selected.sha256.is_some());
        assert!(selected.file.is_some());
        assert_ne!(format!("{:?}", selected.parent), "");
    }
}
#[test]
fn too_large_and_missing_reads_do_not_mint_documents() {
    let files = TestFs::new();
    let big = files.file("big.cpp", &vec![0; MAX_SOURCE_BYTES + 1]);
    let (mut r, c) = fixture();
    for (path, expected) in [
        (big, Code::TooLarge),
        (files.dir.join("missing.cpp"), Code::IOFailure),
    ] {
        let id = r.reserve(&c, Operation::Open).unwrap();
        let job = work(r.open(&c, req(&id)).unwrap());
        is_failed(
            r.complete(job.run(&mut TestPicker {
                path: Some(path),
                calls: 0,
            }))
            .unwrap(),
            expected,
        );
        assert_eq!(r.counts().0, 0);
    }
}
#[test]
fn real_share_violation_is_busy_and_does_not_modify_file() {
    let files = TestFs::new();
    let path = files.file("busy.cpp", b"ORIGINAL");
    let _writer = fs::OpenOptions::new()
        .write(true)
        .share_mode(7)
        .open(&path)
        .unwrap();
    let (mut r, c) = fixture();
    let id = r.reserve(&c, Operation::Open).unwrap();
    let job = work(r.open(&c, req(&id)).unwrap());
    is_failed(
        r.complete(job.run(&mut TestPicker {
            path: Some(path.clone()),
            calls: 0,
        }))
        .unwrap(),
        Code::Busy,
    );
    assert_eq!(fs::read(path).unwrap(), b"ORIGINAL");
}
#[test]
fn real_hardlink_selected_target_is_refused_without_write() {
    let files = TestFs::new();
    let path = files.file("single.cpp", b"EXACT");
    let alias = files.dir.join("alias.cpp");
    fs::hard_link(&path, &alias)
        .expect("TEST_ONLY real hardlink fixture needs scoped filesystem permission");
    let (mut r, c) = fixture();
    let id = r.reserve(&c, Operation::Open).unwrap();
    let job = work(r.open(&c, req(&id)).unwrap());
    is_failed(
        r.complete(job.run(&mut TestPicker {
            path: Some(alias),
            calls: 0,
        }))
        .unwrap(),
        Code::UnsupportedPath,
    );
    assert_eq!(fs::read(path).unwrap(), b"EXACT");
}
#[test]
fn caller_session_incarnation_and_wrong_operation_are_denied() {
    let (mut r, c) = fixture();
    let other = r.attach_caller().unwrap();
    let (id, doc) = create(&mut r, &c);
    assert!(matches!(r.status(&other, &id), Err(Code::Denied)));
    assert!(matches!(
        r.reserve(&other, Operation::ChooseTarget(doc.document_id.clone())),
        Err(Code::Denied)
    ));
    assert!(matches!(
        r.release(
            &other,
            Release::Document {
                document_id: doc.document_id
            }
        ),
        Err(Code::Denied)
    ));
    assert!(matches!(r.open(&c, req(&id)), Err(Code::InvalidInput)));
    let (other_session, _) = fixture();
    assert!(matches!(other_session.status(&c, &id), Err(Code::Denied)));
    r.revoke_caller(&c).unwrap();
    let fresh = r.attach_caller().unwrap();
    assert_ne!(fresh, c);
    assert!(matches!(r.status(&c, &id), Err(Code::Denied)));
    assert!(matches!(r.status(&fresh, &id), Err(Code::Denied)));
}
#[test]
fn release_revokes_candidate_and_duplicate_request_never_remints() {
    let (mut r, c) = fixture();
    let (id, doc) = create(&mut r, &c);
    r.release(
        &c,
        Release::Document {
            document_id: doc.document_id,
        },
    )
    .unwrap();
    assert!(matches!(
        r.status(&c, &id).unwrap(),
        Status::Complete {
            result: Outcome::Revoked,
            ..
        }
    ));
    assert!(matches!(
        r.new_document(&c, req(&id)).unwrap(),
        Start::Ready(Status::Complete {
            result: Outcome::Revoked,
            ..
        })
    ));
    assert_eq!(r.counts().0, 0);
}
#[test]
fn one_dialog_per_caller_even_after_cancel_until_completion() {
    let (mut r, c) = fixture();
    let first = r.reserve(&c, Operation::Open).unwrap();
    let second = r.reserve(&c, Operation::Open).unwrap();
    let job = work(r.open(&c, req(&first)).unwrap());
    assert!(matches!(
        r.open(&c, req(&first)).unwrap(),
        Start::Ready(Status::Pending { .. })
    ));
    assert!(matches!(r.open(&c, req(&second)), Err(Code::Busy)));
    assert!(matches!(
        r.cancel(&c, &first).unwrap(),
        Status::Pending {
            cancel_requested: true
        }
    ));
    assert!(matches!(r.open(&c, req(&second)), Err(Code::Busy)));
    let mut picker = TestPicker {
        path: None,
        calls: 0,
    };
    assert!(matches!(
        r.complete(job.run(&mut picker)).unwrap(),
        Status::Complete {
            result: Outcome::Cancelled { .. },
            ..
        }
    ));
    assert_eq!(picker.calls, 0);
    let next = work(r.open(&c, req(&second)).unwrap());
    r.complete(next.run(&mut picker)).unwrap();
    assert_eq!(picker.calls, 1);
}
#[test]
fn cancelled_after_actual_read_before_completion_discards_bytes_and_grant() {
    let files = TestFs::new();
    let path = files.file("late.cpp", b"REAL READ");
    let (mut r, c) = fixture();
    let id = r.reserve(&c, Operation::Open).unwrap();
    let job = work(r.open(&c, req(&id)).unwrap());
    let completion = job.run(&mut TestPicker {
        path: Some(path),
        calls: 0,
    });
    r.cancel(&c, &id).unwrap();
    assert!(matches!(
        r.complete(completion).unwrap(),
        Status::Complete {
            result: Outcome::Cancelled { .. },
            ..
        }
    ));
    assert_eq!(r.counts().0, 0);
}
#[test]
fn revoke_window_while_read_pending_never_mints_late_grant() {
    let files = TestFs::new();
    let path = files.file("late.cpp", b"REAL READ");
    let (mut r, c) = fixture();
    let id = r.reserve(&c, Operation::Open).unwrap();
    let job = work(r.open(&c, req(&id)).unwrap());
    let completion = job.run(&mut TestPicker {
        path: Some(path),
        calls: 0,
    });
    r.revoke_caller(&c).unwrap();
    r.complete(completion).unwrap();
    assert_eq!(r.counts().0, 0);
    assert_eq!(r.counts().2, 0);
    assert!(matches!(r.status(&c, &id), Err(Code::Denied)));
}
#[test]
fn target_selection_existing_and_absent_never_writes_or_rebinds_document() {
    let files = TestFs::new();
    let existing = files.file("existing.cpp", b"TARGET");
    let absent = files.dir.join("absent.cpp");
    let (mut r, c) = fixture();
    let (_, doc) = create(&mut r, &c);
    for path in [&existing, &absent] {
        let id = r
            .reserve(&c, Operation::ChooseTarget(doc.document_id.clone()))
            .unwrap();
        let job = work(
            r.choose_target(
                &c,
                TargetRequest {
                    request_id: id.clone(),
                    document_id: doc.document_id.clone(),
                },
            )
            .unwrap(),
        );
        let status = r
            .complete(job.run(&mut TestPicker {
                path: Some(path.clone()),
                calls: 0,
            }))
            .unwrap();
        let Status::Complete {
            result:
                Outcome::Selected {
                    target_grant_id,
                    target_state,
                    ..
                },
            ..
        } = status
        else {
            panic!()
        };
        assert_eq!(
            matches!(target_state, TargetState::Existing { .. }),
            path == &existing
        );
        r.release(&c, Release::Target { target_grant_id }).unwrap();
        assert!(matches!(
            r.status(&c, &id).unwrap(),
            Status::Complete {
                result: Outcome::Revoked,
                ..
            }
        ));
    }
    assert!(!absent.exists());
    assert_eq!(fs::read(existing).unwrap(), b"TARGET");
    assert!(r
        .documents
        .get(&doc.document_id)
        .unwrap()
        .selection
        .is_none());
}
#[test]
fn release_document_cancels_pending_target_and_revokes_child_grants() {
    let files = TestFs::new();
    let (mut r, c) = fixture();
    let (_, doc) = create(&mut r, &c);
    let id = r
        .reserve(&c, Operation::ChooseTarget(doc.document_id.clone()))
        .unwrap();
    let job = work(
        r.choose_target(
            &c,
            TargetRequest {
                request_id: id.clone(),
                document_id: doc.document_id.clone(),
            },
        )
        .unwrap(),
    );
    let completion = job.run(&mut TestPicker {
        path: Some(files.dir.join("future.cpp")),
        calls: 0,
    });
    r.release(
        &c,
        Release::Document {
            document_id: doc.document_id,
        },
    )
    .unwrap();
    assert!(matches!(
        r.complete(completion).unwrap(),
        Status::Complete {
            result: Outcome::Cancelled { .. },
            ..
        }
    ));
    assert_eq!(r.counts().0, 0);
}
#[test]
fn concrete_grant_and_unresolved_limits_fail_closed() {
    let (mut r, c) = fixture();
    for _ in 0..MAX_GRANTS {
        create(&mut r, &c);
    }
    let id = r.reserve(&c, Operation::New).unwrap();
    match r.new_document(&c, req(&id)).unwrap() {
        Start::Ready(status) => is_failed(status, Code::Busy),
        _ => panic!(),
    }
    assert_eq!(r.counts().0, 32);
    let mut reservations = Vec::new();
    for _ in 0..MAX_UNRESOLVED_OPS {
        reservations.push(r.reserve(&c, Operation::Open).unwrap());
    }
    assert_eq!(r.reserve(&c, Operation::Open), Err(Code::Busy));
    for id in reservations {
        r.cancel(&c, &id).unwrap();
    }
    assert_eq!(r.counts().2, 0);
}
#[test]
fn settled_128_eviction_never_reexecutes_old_id_or_evicts_unresolved() {
    let (mut r, c) = fixture();
    let unresolved = r.reserve(&c, Operation::Open).unwrap();
    let (old, doc) = create(&mut r, &c);
    r.release(
        &c,
        Release::Document {
            document_id: doc.document_id,
        },
    )
    .unwrap();
    for _ in 0..MAX_SETTLED_OPS {
        let (id, doc) = create(&mut r, &c);
        r.release(
            &c,
            Release::Document {
                document_id: doc.document_id,
            },
        )
        .unwrap();
        assert!(matches!(
            r.status(&c, &id).unwrap(),
            Status::Complete {
                result: Outcome::Revoked,
                ..
            }
        ));
    }
    assert_eq!(r.counts(), (0, 128, 1));
    assert!(matches!(
        r.status(&c, &unresolved).unwrap(),
        Status::Reserved
    ));
    assert!(matches!(
        r.new_document(&c, req(&old)),
        Err(Code::UnknownRequest)
    ));
    assert_eq!(r.counts(), (0, 128, 1));
}
#[test]
fn caller_limit_and_release_are_bounded() {
    let (mut r, c) = fixture();
    for _ in 1..MAX_CALLERS {
        r.attach_caller().unwrap();
    }
    assert_eq!(r.attach_caller(), Err(Code::Busy));
    r.revoke_caller(&c).unwrap();
    assert!(r.attach_caller().is_ok());
}
#[test]
fn failed_picker_is_settled_idempotently_without_grants() {
    struct TestOnlyDeniedPicker;
    impl NativePicker for TestOnlyDeniedPicker {
        fn select(&mut self, _: PickerKind) -> Result<Option<PathBuf>, Code> {
            Err(Code::Denied)
        }
    }
    let (mut r, c) = fixture();
    let id = r.reserve(&c, Operation::Open).unwrap();
    let job = work(r.open(&c, req(&id)).unwrap());
    is_failed(
        r.complete(job.run(&mut TestOnlyDeniedPicker)).unwrap(),
        Code::Denied,
    );
    match r.open(&c, req(&id)).unwrap() {
        Start::Ready(status) => is_failed(status, Code::Denied),
        _ => panic!("must not launch another picker"),
    }
    assert_eq!(r.counts(), (0, 1, 0));
}
#[test]
fn picker_panic_returns_failed_completion_and_releases_dialog() {
    struct TestOnlyPanickingPicker;
    impl NativePicker for TestOnlyPanickingPicker {
        fn select(&mut self, _: PickerKind) -> Result<Option<PathBuf>, Code> {
            panic!("TEST_ONLY native picker failure");
        }
    }
    let (mut r, c) = fixture();
    let id = r.reserve(&c, Operation::Open).unwrap();
    let job = work(r.open(&c, req(&id)).unwrap());
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        job.run(&mut TestOnlyPanickingPicker)
    }));
    assert!(
        result.is_ok(),
        "native read job must return a completion on picker panic"
    );
    is_failed(r.complete(result.unwrap()).unwrap(), Code::IOFailure);
    assert_eq!(r.counts(), (0, 1, 0));
    let next = r.reserve(&c, Operation::Open).unwrap();
    let next_job = work(r.open(&c, req(&next)).unwrap());
    let mut picker = TestPicker {
        path: None,
        calls: 0,
    };
    r.complete(next_job.run(&mut picker)).unwrap();
    assert_eq!(picker.calls, 1);
}
#[test]
fn cancelling_completed_read_returns_real_outcome_until_explicit_release() {
    let files = TestFs::new();
    let path = files.file("finished.cpp", b"DONE");
    let (mut r, c) = fixture();
    let (id, doc) = open_file(&mut r, &c, &path);
    assert_eq!(
        candidate(r.cancel(&c, &id).unwrap()).document_id,
        doc.document_id
    );
    r.release(
        &c,
        Release::Document {
            document_id: doc.document_id,
        },
    )
    .unwrap();
    assert!(matches!(
        r.cancel(&c, &id).unwrap(),
        Status::Complete {
            result: Outcome::Revoked,
            ..
        }
    ));
}
#[test]
fn bound_target_payload_cannot_be_changed_to_another_document() {
    let (mut r, c) = fixture();
    let (_, first) = create(&mut r, &c);
    let (_, second) = create(&mut r, &c);
    let id = r
        .reserve(&c, Operation::ChooseTarget(first.document_id))
        .unwrap();
    assert!(matches!(
        r.choose_target(
            &c,
            TargetRequest {
                request_id: id.clone(),
                document_id: second.document_id
            }
        ),
        Err(Code::InvalidInput)
    ));
    assert!(matches!(r.status(&c, &id).unwrap(), Status::Reserved));
    assert_eq!(r.counts().0, 2);
}
#[test]
fn active_read_is_never_evicted_by_settled_history_churn() {
    let (mut r, c) = fixture();
    let pending = r.reserve(&c, Operation::Open).unwrap();
    let job = work(r.open(&c, req(&pending)).unwrap());
    for _ in 0..MAX_SETTLED_OPS + 1 {
        let (_, doc) = create(&mut r, &c);
        r.release(
            &c,
            Release::Document {
                document_id: doc.document_id,
            },
        )
        .unwrap();
    }
    assert!(matches!(
        r.status(&c, &pending).unwrap(),
        Status::Pending {
            cancel_requested: false
        }
    ));
    assert_eq!(r.counts(), (0, 128, 1));
    r.cancel(&c, &pending).unwrap();
    r.complete(job.run(&mut TestPicker {
        path: None,
        calls: 0,
    }))
    .unwrap();
    assert_eq!(r.counts(), (0, 128, 0));
}
#[test]
fn real_directory_is_not_a_source_and_absent_parent_is_not_created() {
    let files = TestFs::new();
    let (mut r, c) = fixture();
    let (_, doc) = create(&mut r, &c);
    let id = r.reserve(&c, Operation::Open).unwrap();
    let job = work(r.open(&c, req(&id)).unwrap());
    let result = r
        .complete(job.run(&mut TestPicker {
            path: Some(files.dir.clone()),
            calls: 0,
        }))
        .unwrap();
    assert!(matches!(
        result,
        Status::Complete {
            result: Outcome::Failed { .. },
            ..
        }
    ));
    let path = files.dir.join("not-created").join("x.cpp");
    let id = r
        .reserve(&c, Operation::ChooseTarget(doc.document_id.clone()))
        .unwrap();
    let job = work(
        r.choose_target(
            &c,
            TargetRequest {
                request_id: id,
                document_id: doc.document_id,
            },
        )
        .unwrap(),
    );
    is_failed(
        r.complete(job.run(&mut TestPicker {
            path: Some(path.clone()),
            calls: 0,
        }))
        .unwrap(),
        Code::IOFailure,
    );
    assert!(!path.parent().unwrap().exists());
}
