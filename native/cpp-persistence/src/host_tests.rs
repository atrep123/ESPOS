//! TEST_ONLY NativeHost lifecycle signals and picker; actual canonical host,
//! registry, jobs and Windows filesystem. These callbacks do not prove Tauri
//! sender/navigation authentication. Main owns cfg(test) wiring and execution.
//! Each fixture is retained in a fresh GUID directory under crate/test-tmp.
use crate::host::{Binding, HostDispatch, HostReply, NativeHost, ReadWork, WriteWork};
use crate::save_as::DraftBinding;
use crate::writer::SaveView;
use crate::{
    Candidate, Code, DocumentId, NativePicker, Outcome, PickerKind, RequestId, Status, TargetId,
    TargetState, Version, MAX_SOURCE_BYTES,
};
use base64::{engine::general_purpose::STANDARD, Engine};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    fs,
    io::Write,
    os::windows::fs::MetadataExt,
    path::{Path, PathBuf},
};

struct TestOnlyFs {
    dir: PathBuf,
    storage: PathBuf,
}
impl TestOnlyFs {
    fn new() -> Self {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp");
        fs::create_dir_all(&root).unwrap();
        let nonce = crate::owned_job_nonce().unwrap();
        let dir = root.join(format!(
            "host-{}-{}-{}-{}-{}",
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
    fn host(&self) -> NativeHost {
        NativeHost::open_local(&self.storage).unwrap()
    }
    fn path(&self, name: &str) -> PathBuf {
        assert!(!name.contains(['\\', '/']));
        assert!(name.ends_with(".cpp"));
        self.dir.join(name)
    }
    fn file(&self, name: &str, bytes: &[u8]) -> PathBuf {
        let path = self.path(name);
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)
            .unwrap();
        file.write_all(bytes).unwrap();
        file.sync_all().unwrap();
        path
    }
    fn picker(&self, path: &Path, kind: PickerKind) -> TestOnlyPicker {
        assert_eq!(path.parent(), Some(self.dir.as_path()));
        assert_eq!(path.extension().and_then(|s| s.to_str()), Some("cpp"));
        TestOnlyPicker {
            root: self.dir.clone(),
            path: path.into(),
            kind,
            calls: 0,
        }
    }
    fn artifact(&self, id: &RequestId, suffix: &str) -> PathBuf {
        assert!(matches!(suffix, "backup.bin" | "payload.bin"));
        self.storage
            .join("cpp-recovery-v1")
            .join(format!("{}.{suffix}", id.as_str()))
    }
    fn artifacts(&self) -> BTreeMap<String, Vec<u8>> {
        fs::read_dir(self.storage.join("cpp-recovery-v1"))
            .unwrap()
            .map(|entry| entry.unwrap())
            // The cooperative lease is held exclusively; never open it.
            .filter(|entry| entry.file_name() != "host.lock")
            .map(|entry| {
                (
                    entry.file_name().into_string().unwrap(),
                    fs::read(entry.path()).unwrap(),
                )
            })
            .collect()
    }
}

struct TestOnlyPicker {
    root: PathBuf,
    path: PathBuf,
    kind: PickerKind,
    calls: usize,
}
impl NativePicker for TestOnlyPicker {
    fn select(&mut self, kind: PickerKind) -> Result<Option<PathBuf>, Code> {
        assert_eq!(kind, self.kind);
        assert_eq!(self.path.parent(), Some(self.root.as_path()));
        self.calls += 1;
        Ok(Some(self.path.clone()))
    }
}

fn active(host: &NativeHost) -> Binding {
    let binding = host.prepare_native_view().unwrap();
    let ticket = host.native_document_started(&binding).unwrap();
    host.native_document_finished(ticket).unwrap();
    binding
}
fn raw(call: u64, command: Value) -> Vec<u8> {
    serde_json::to_vec(&json!({"callId": format!("call_{call:032x}"), "command": command})).unwrap()
}
fn reply(host: &NativeHost, binding: &Binding, bytes: &[u8]) -> HostReply {
    match host.dispatch(binding, bytes).unwrap() {
        HostDispatch::Reply(reply) => reply,
        HostDispatch::Read(_) => panic!("expected reply, got new ReadWork"),
        HostDispatch::Write(_) => panic!("expected reply, got new WriteWork"),
        HostDispatch::Project(_) => panic!("expected reply, got new ProjectWork"),
    }
}
fn reservation(reply: HostReply) -> (RequestId, Status) {
    match reply {
        HostReply::Reservation { request_id, state } => (request_id, state),
        _ => panic!("expected reservation"),
    }
}
fn state_reply(reply: HostReply) -> Status {
    match reply {
        HostReply::State { state } => state,
        _ => panic!("expected state"),
    }
}
fn draft_reply(reply: HostReply) -> DraftBinding {
    match reply {
        HostReply::Draft { binding } => binding,
        _ => panic!("expected captured draft"),
    }
}
fn save_state(state: Status) -> SaveView {
    match state {
        Status::Save { write } => write,
        _ => panic!("expected writer state"),
    }
}
fn read_work(host: &NativeHost, binding: &Binding, bytes: &[u8]) -> ReadWork {
    match host.dispatch(binding, bytes).unwrap() {
        HostDispatch::Read(work) => work,
        _ => panic!("expected owned ReadWork"),
    }
}
fn write_work(host: &NativeHost, binding: &Binding, bytes: &[u8]) -> WriteWork {
    match host.dispatch(binding, bytes).unwrap() {
        HostDispatch::Write(work) => work,
        _ => panic!("expected owned WriteWork"),
    }
}
fn denied(host: &NativeHost, binding: &Binding, bytes: &[u8], expected: Code) {
    assert!(
        matches!(host.dispatch(binding, bytes), Err(code) if code == expected),
        "expected {expected:?} for raw DTO"
    );
}
fn same<T: serde::Serialize>(a: &T, b: &T) {
    assert_eq!(
        serde_json::to_value(a).unwrap(),
        serde_json::to_value(b).unwrap()
    );
}
fn begin(id: &RequestId, call: u64) -> Vec<u8> {
    raw(call, json!({"kind": "beginSave", "requestId": id}))
}
fn bind(call: u64, revision: u64, bytes: &[u8]) -> Vec<u8> {
    raw(
        call,
        json!({"kind": "bindDraft", "revision": revision, "sourceBase64": STANDARD.encode(bytes)}),
    )
}
fn save(call: u64, doc: &DocumentId, version: &Version, bytes: &[u8]) -> Vec<u8> {
    raw(
        call,
        json!({"kind": "reserveSave", "documentId": doc, "version": version,
        "sourceBase64": STANDARD.encode(bytes)}),
    )
}
fn save_as(call: u64, draft: &DraftBinding, target: &TargetId, bytes: &[u8]) -> Vec<u8> {
    raw(
        call,
        json!({"kind": "reserveSaveAs", "documentId": draft.document_id,
        "targetGrantId": target, "revision": draft.capture_revision, "sourceBase64": STANDARD.encode(bytes)}),
    )
}
fn open(
    host: &NativeHost,
    binding: &Binding,
    files: &TestOnlyFs,
    path: &Path,
) -> (RequestId, Candidate) {
    let (id, state) = reservation(reply(
        host,
        binding,
        &raw(
            1,
            json!({"kind": "reserve", "intent": {"operation": "open"}}),
        ),
    ));
    assert!(matches!(state, Status::Reserved));
    let work = read_work(
        host,
        binding,
        &raw(2, json!({"kind": "open", "requestId": id})),
    );
    assert_eq!(work.request_id(), &id);
    let mut picker = files.picker(path, PickerKind::Open);
    let result = work.run(&mut picker).unwrap();
    assert_eq!(picker.calls, 1);
    same(&result, &host.state(binding, &id).unwrap());
    match result {
        Status::Complete {
            result: Outcome::Opened { document },
            ..
        } => (id, document),
        _ => panic!("expected actual native open"),
    }
}
fn select_target(
    host: &NativeHost,
    binding: &Binding,
    files: &TestOnlyFs,
    doc: &DocumentId,
    path: &Path,
) -> (RequestId, TargetId, TargetState) {
    let (id, _) = reservation(reply(
        host,
        binding,
        &raw(
            3,
            json!({"kind": "reserve", "intent": {"operation": "chooseTarget", "documentId": doc}}),
        ),
    ));
    let bytes = raw(
        4,
        json!({"kind": "chooseTarget", "requestId": id, "documentId": doc}),
    );
    let work = read_work(host, binding, &bytes);
    assert_eq!(work.request_id(), &id);
    let mut picker = files.picker(path, PickerKind::SaveTarget);
    let result = work.run(&mut picker).unwrap();
    assert_eq!(picker.calls, 1);
    same(&result, &host.state(binding, &id).unwrap());
    // Repeating the action returns the native result, never another picker.
    same(&result, &state_reply(reply(host, binding, &bytes)));
    match result {
        Status::Complete {
            result:
                Outcome::Selected {
                    target_grant_id,
                    document_id,
                    target_state,
                    ..
                },
            ..
        } => {
            assert_eq!(&document_id, doc);
            (id, target_grant_id, target_state)
        }
        _ => panic!("expected actual native target selection"),
    }
}
fn file_snapshot(path: &Path) -> (Vec<u8>, u64, u64, u64) {
    let m = fs::metadata(path).unwrap();
    (
        fs::read(path).unwrap(),
        m.creation_time(),
        m.last_write_time(),
        m.file_size(),
    )
}

#[test]
fn quarantined_and_loading_views_cannot_dispatch_until_first_native_ticket_finishes() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = host.prepare_native_view().unwrap();
    let bytes = raw(
        1,
        json!({"kind": "reserve", "intent": {"operation": "new"}}),
    );
    denied(&host, &binding, &bytes, Code::Unavailable);
    let ticket = host.native_document_started(&binding).unwrap();
    denied(&host, &binding, &bytes, Code::Unavailable);
    host.native_document_finished(ticket).unwrap();
    let (id, state) = reservation(reply(&host, &binding, &bytes));
    assert!(matches!(state, Status::Reserved));
    let create = raw(2, json!({"kind": "new", "requestId": id}));
    let state = state_reply(reply(&host, &binding, &create));
    assert!(matches!(
        &state,
        Status::Complete {
            result: Outcome::Created { .. },
            ..
        }
    ));
    same(&state, &host.state(&binding, &id).unwrap());
    same(&state, &state_reply(reply(&host, &binding, &create)));
    assert!(files.artifacts().is_empty());
}

#[test]
fn second_native_document_start_permanently_revokes_loading_or_active_view() {
    for finish_first in [false, true] {
        let files = TestOnlyFs::new();
        let host = files.host();
        let binding = host.prepare_native_view().unwrap();
        let first = host.native_document_started(&binding).unwrap();
        let late_ticket = if finish_first {
            host.native_document_finished(first).unwrap();
            None
        } else {
            Some(first)
        };
        assert!(matches!(
            host.native_document_started(&binding),
            Err(Code::Revoked)
        ));
        if let Some(ticket) = late_ticket {
            assert_eq!(host.native_document_finished(ticket), Err(Code::Revoked));
        }
        assert!(matches!(
            host.native_document_started(&binding),
            Err(Code::Revoked)
        ));
        host.revoke_native_view(&binding).unwrap();
        denied(&host, &binding, &bind(1, 0, b"late page"), Code::Revoked);
        let fresh = active(&host);
        assert!(matches!(
            reply(&host, &fresh, &bind(1, 0, b"fresh page")),
            HostReply::Draft { .. }
        ));
        denied(&host, &binding, &bind(1, 0, b"late page"), Code::Revoked);
    }
}

#[test]
fn foreign_actual_bindings_and_tickets_are_denied_and_call_id_is_only_correlation() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let foreign_files = TestOnlyFs::new();
    let foreign_host = foreign_files.host();
    let binding = active(&host);
    let foreign = foreign_host.prepare_native_view().unwrap();
    let bytes = bind(1, 9, b"owner capture");
    let draft = draft_reply(reply(&host, &binding, &bytes));
    denied(&host, &foreign, &bytes, Code::Denied);
    assert!(matches!(
        host.native_document_started(&foreign),
        Err(Code::Denied)
    ));
    assert_eq!(host.revoke_native_view(&foreign), Err(Code::Denied));
    assert!(matches!(
        host.state(&foreign, &draft.request_id),
        Err(Code::Denied)
    ));
    let foreign_ticket = foreign_host.native_document_started(&foreign).unwrap();
    assert_eq!(
        host.native_document_finished(foreign_ticket),
        Err(Code::Denied)
    );
    let other = active(&host);
    let other_draft = draft_reply(reply(&host, &other, &bytes));
    assert_ne!(other_draft.document_id, draft.document_id);
    assert_ne!(other_draft.request_id, draft.request_id);
    denied(
        &host,
        &other,
        &raw(1, json!({"kind": "status", "requestId": draft.request_id})),
        Code::InvalidInput,
    );
    denied(
        &host,
        &other,
        &raw(2, json!({"kind": "status", "requestId": draft.request_id})),
        Code::Denied,
    );
    denied(
        &host,
        &other,
        &raw(
            3,
            json!({"kind": "reserve", "intent": {
        "operation": "chooseTarget", "documentId": draft.document_id}}),
        ),
        Code::Denied,
    );
    denied(
        &host,
        &other,
        &raw(
            4,
            json!({"kind": "release", "grant": {
        "kind": "document", "documentId": draft.document_id}}),
        ),
        Code::Denied,
    );
    same(&draft, &draft_reply(reply(&host, &binding, &bytes)));
}

#[test]
fn strict_raw_dto_rejects_duplicate_unknown_numeric_path_and_noncanonical_fields() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    let c = "call_00000000000000000000000000000001";
    let d = "doc_00000000000000000000000000000001";
    let r = "request_00000000000000000000000000000001";
    let v = "version_00000000000000000000000000000001";
    // Build raw strings directly: Value/maps would discard duplicate keys.
    let commands = vec![
        r#"{"kind":"reserve","kind":"reserve","intent":{"operation":"new"}}"#.to_owned(),
        r#"{"kind":"reserve","intent":{"operation":"new","operation":"open"}}"#.to_owned(),
        r#"{"kind":"reserve","intent":{"operation":"new","path":"C:/blocked.cpp"}}"#.to_owned(),
        r#"{"kind":"reserve","intent":{"operation":"new"},"caller":"forged"}"#.to_owned(),
        r#"{"kind":"bindDraft","revision":0,"revision":1,"sourceBase64":""}"#.to_owned(),
        r#"{"kind":"bindDraft","revision":0,"sourceBase64":"","sourceBase64":""}"#.to_owned(),
        r#"{"kind":"bindDraft","revision":0,"sourceBase64":"","binding":{}}"#.to_owned(),
        r#"{"kind":"BindDraft","revision":0,"sourceBase64":""}"#.to_owned(),
        r#"{"kind":"bindDraft","revision":0,"source_base64":""}"#.to_owned(),
        format!(r#"{{"kind":"status","request_id":"{r}"}}"#),
        format!(r#"{{"kind":"status","requestId":"{r}","requestId":"{r}"}}"#),
        r#"{"kind":"open","requestId":"C:/blocked.cpp"}"#.to_owned(),
        format!(r#"{{"kind":"open","requestId":"{r}","path":"C:/blocked.cpp"}}"#),
        format!(
            r#"{{"kind":"release","grant":{{"kind":"document","documentId":"{d}","documentId":"{d}"}}}}"#
        ),
        format!(
            r#"{{"kind":"release","grant":{{"kind":"document","documentId":"{d}","path":"C:/blocked.cpp"}}}}"#
        ),
        format!(
            r#"{{"kind":"reserveSave","documentId":"{d}","version":"{v}","version":"{v}","sourceBase64":""}}"#
        ),
        format!(r#"{{"kind":"reserveSave","documentId":"{d}","version":1,"sourceBase64":""}}"#),
        format!(
            r#"{{"kind":"reserveSaveAs","documentId":"{d}","targetGrantId":"C:/blocked.cpp","revision":0,"sourceBase64":""}}"#
        ),
        format!(
            r#"{{"kind":"confirmSave","requestId":"{r}","decision":"overwriteWithActualBackup"}}"#
        ),
        format!(
            r#"{{"kind":"confirmSave","requestId":"{r}","decision":"Stop","externalHash":"forged"}}"#
        ),
    ];
    for command in commands {
        let bytes = format!(r#"{{"callId":"{c}","command":{command}}}"#);
        denied(&host, &binding, bytes.as_bytes(), Code::InvalidInput);
    }
    for revision in [
        "-1",
        "0.5",
        "1e0",
        "\"1\"",
        "true",
        "null",
        "9007199254740992",
        "18446744073709551616",
    ] {
        for kind in ["bindDraft", "reserveSaveAs"] {
            let extra = if kind == "reserveSaveAs" {
                format!(
                    r#", "documentId":"{d}", "targetGrantId":"target_00000000000000000000000000000001""#
                )
            } else {
                String::new()
            };
            let bytes = format!(
                r#"{{"callId":"{c}","command":{{"kind":"{kind}","revision":{revision},"sourceBase64":""{extra}}}}}"#
            );
            denied(&host, &binding, bytes.as_bytes(), Code::InvalidInput);
        }
    }
    for bytes in [
        format!(r#"{{"callId":"{c}","callId":"{c}","command":{{"kind":"bindDraft","revision":0,"sourceBase64":""}}}}"#),
        format!(r#"{{"callId":"{c}","command":{{"kind":"bindDraft","revision":0,"sourceBase64":""}},"command":{{"kind":"bindDraft","revision":0,"sourceBase64":""}}}}"#),
        format!(r#"{{"callId":"{c}","command":{{"kind":"bindDraft","revision":0,"sourceBase64":""}},"path":"C:/blocked.cpp"}}"#),
        format!(r#"{{"call_id":"{c}","command":{{"kind":"bindDraft","revision":0,"sourceBase64":""}}}}"#),
        r#"{"callId":1,"command":{"kind":"bindDraft","revision":0,"sourceBase64":""}}"#.to_owned(),
        r#"{"callId":"call_ABCDEF00000000000000000000000000","command":{"kind":"bindDraft","revision":0,"sourceBase64":""}}"#.to_owned(),
        r#"{"callId":"call_1","command":{"kind":"bindDraft","revision":0,"sourceBase64":""}}"#.to_owned(),
        "{}".to_owned(),
        "[]".to_owned(),
    ] {
        denied(&host, &binding, bytes.as_bytes(), Code::InvalidInput);
    }
    // Rejections must not poison this call ID with a mutation/replay record.
    let draft = draft_reply(reply(&host, &binding, &bind(1, 0, b"accepted")));
    assert_eq!(draft.source_bytes, 8);
    assert!(files.artifacts().is_empty());
}

#[test]
fn raw_request_source_and_safe_integer_bounds_are_enforced_at_host_dispatch() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    for (call, revision) in [(1, 0), (2, 9_007_199_254_740_991)] {
        let draft = draft_reply(reply(&host, &binding, &bind(call, revision, b"x")));
        assert_eq!(draft.capture_revision, revision);
    }
    let maximum = vec![0xff; MAX_SOURCE_BYTES];
    let draft = draft_reply(reply(&host, &binding, &bind(3, 0, &maximum)));
    assert_eq!(draft.source_bytes, MAX_SOURCE_BYTES);
    assert_eq!(draft.source_hash, crate::windows_write::digest(&maximum));
    // One excess decoded byte still fits the base64/transport envelope.
    let too_large = bind(4, 0, &vec![0xff; MAX_SOURCE_BYTES + 1]);
    assert!(too_large.len() <= crate::host::MAX_HOST_REQUEST_BYTES);
    denied(&host, &binding, &too_large, Code::TooLarge);
    denied(&host, &binding, &too_large, Code::TooLarge);
    denied(
        &host,
        &binding,
        &vec![b' '; crate::host::MAX_HOST_REQUEST_BYTES + 1],
        Code::TooLarge,
    );
    // At the raw bound, JSON is parsed rather than classified as oversize.
    denied(
        &host,
        &binding,
        &vec![b' '; crate::host::MAX_HOST_REQUEST_BYTES],
        Code::InvalidInput,
    );
    for (i, source) in ["!", "YQ", "YR==", "YQ==\n"].iter().enumerate() {
        denied(
            &host,
            &binding,
            &raw(
                10 + i as u64,
                json!({"kind": "bindDraft", "revision": 0, "sourceBase64": source}),
            ),
            Code::InvalidInput,
        );
    }
    assert!(files.artifacts().is_empty());
}

#[test]
fn reserve_and_release_replay_same_raw_bytes_keep_native_identity_and_revocation() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    let bytes = raw(
        1,
        json!({"kind": "reserve", "intent": {"operation": "new"}}),
    );
    let (id, reserved) = reservation(reply(&host, &binding, &bytes));
    let (again, state) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    same(&reserved, &state);
    denied(
        &host,
        &binding,
        &raw(
            1,
            json!({"kind": "reserve", "intent": {"operation": "open"}}),
        ),
        Code::InvalidInput,
    );
    let mut different_raw = bytes.clone();
    different_raw.push(b' '); // Even semantically equivalent JSON has a different raw digest.
    denied(&host, &binding, &different_raw, Code::InvalidInput);
    let created = state_reply(reply(
        &host,
        &binding,
        &raw(2, json!({"kind": "new", "requestId": id})),
    ));
    let document = match &created {
        Status::Complete {
            result: Outcome::Created { document },
            ..
        } => document,
        _ => panic!("expected created document"),
    };
    let (again, state) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    same(&created, &state);
    let release = raw(
        3,
        json!({"kind": "release", "grant": {"kind": "document", "documentId": document.document_id}}),
    );
    assert!(matches!(
        reply(&host, &binding, &release),
        HostReply::Released {}
    ));
    assert!(matches!(
        reply(&host, &binding, &release),
        HostReply::Released {}
    ));
    let mut changed_release = release.clone();
    changed_release.push(b' ');
    denied(&host, &binding, &changed_release, Code::InvalidInput);
    let (again, state) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    assert!(matches!(
        state,
        Status::Complete {
            result: Outcome::Revoked,
            ..
        }
    ));
    assert!(files.artifacts().is_empty());
}

#[test]
fn bind_draft_replay_is_immutable_and_release_prevents_reminting() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    let bytes = bind(1, 17, &[0xef, 0xbb, 0xbf, 0xff, 0, 13, 10]);
    let draft = draft_reply(reply(&host, &binding, &bytes));
    same(&draft, &draft_reply(reply(&host, &binding, &bytes)));
    denied(
        &host,
        &binding,
        &bind(1, 18, b"changed"),
        Code::InvalidInput,
    );
    let release = raw(
        2,
        json!({"kind": "release", "grant": {"kind": "document", "documentId": draft.document_id}}),
    );
    reply(&host, &binding, &release);
    reply(&host, &binding, &release);
    denied(&host, &binding, &bytes, Code::Revoked);
    assert!(matches!(
        host.state(&binding, &draft.request_id).unwrap(),
        Status::Complete {
            result: Outcome::Revoked,
            ..
        }
    ));
    let next = draft_reply(reply(
        &host,
        &binding,
        &bind(3, 17, b"explicit new capture"),
    ));
    assert_ne!(next.document_id, draft.document_id);
    assert!(files.artifacts().is_empty());
}

#[test]
fn reserve_save_replay_and_action_replay_do_not_spawn_work_or_change_actual_files() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    let path = files.file("ordinary.cpp", b"baseline");
    let (_, doc) = open(&host, &binding, &files, &path);
    let version = doc.binding.unwrap().version;
    let bytes = save(10, &doc.document_id, &version, b"captured ordinary bytes");
    let (id, reserved) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(save_state(reserved).phase, "reserved");
    let (again, _) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    denied(
        &host,
        &binding,
        &save(10, &doc.document_id, &version, b"changed"),
        Code::InvalidInput,
    );
    let other = active(&host);
    denied(&host, &other, &bytes, Code::Denied);
    let action = begin(&id, 11);
    let work = write_work(&host, &binding, &action);
    assert_eq!(work.request_id(), &id);
    let (again, pending) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    assert_eq!(save_state(pending).phase, "pending");
    assert_eq!(
        save_state(state_reply(reply(&host, &binding, &action))).phase,
        "pending"
    );
    let written = work.run().unwrap();
    assert_eq!(written.phase, "written");
    assert_eq!(written.operation_id, id);
    assert!(written.adoption.is_some());
    assert_eq!(fs::read(&path).unwrap(), b"captured ordinary bytes");
    assert_eq!(
        fs::read(files.artifact(&id, "backup.bin")).unwrap(),
        b"baseline"
    );
    same(&written, &save_state(host.state(&binding, &id).unwrap()));
    let snapshot = file_snapshot(&path);
    let artifacts = files.artifacts();
    let (again, state) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    same(&written, &save_state(state));
    same(
        &written,
        &save_state(state_reply(reply(&host, &binding, &action))),
    );
    assert_eq!(file_snapshot(&path), snapshot);
    assert_eq!(files.artifacts(), artifacts);
}

fn save_as_flow(existing: bool) {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    let path = if existing {
        files.file("save-as.cpp", b"selected baseline")
    } else {
        files.path("save-as.cpp")
    };
    let source = [0xef, 0xbb, 0xbf, 0xff, 0, 13, 10];
    let draft_raw = bind(1, 73, &source);
    let draft = draft_reply(reply(&host, &binding, &draft_raw));
    let (target_request, target, selected) =
        select_target(&host, &binding, &files, &draft.document_id, &path);
    assert_eq!(matches!(selected, TargetState::Existing { .. }), existing);
    assert_eq!(path.exists(), existing);
    assert!(files.artifacts().is_empty());
    let bytes = save_as(10, &draft, &target, &source);
    let other = active(&host);
    denied(&host, &other, &bytes, Code::Denied);
    denied(
        &host,
        &other,
        &raw(
            11,
            json!({"kind": "chooseTarget", "requestId": target_request,
        "documentId": draft.document_id}),
        ),
        Code::Denied,
    );
    // Valid DTO but wrong immutable capture cannot consume the genuine target.
    let mut wrong_revision: Value = serde_json::from_slice(&bytes).unwrap();
    wrong_revision["callId"] = json!(format!("call_{:032x}", 8));
    wrong_revision["command"]["revision"] = json!(74);
    denied(
        &host,
        &binding,
        &serde_json::to_vec(&wrong_revision).unwrap(),
        Code::Conflict,
    );
    denied(
        &host,
        &binding,
        &save_as(9, &draft, &target, b"changed capture"),
        Code::Conflict,
    );
    let (id, reserved) = reservation(reply(&host, &binding, &bytes));
    let view = save_state(reserved);
    assert_eq!(view.phase, "reserved");
    let identity = view.save_as.unwrap();
    assert_eq!(identity.target_grant_id, target);
    assert_eq!(identity.capture_revision, 73);
    assert_eq!(identity.target_absent, !existing);
    assert!(matches!(
        host.state(&binding, &target_request).unwrap(),
        Status::Complete {
            result: Outcome::Revoked,
            ..
        }
    ));
    let (again, _) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    let mut changed = bytes.clone();
    changed.push(b' ');
    denied(&host, &binding, &changed, Code::InvalidInput);
    let mut fresh = serde_json::from_slice::<Value>(&bytes).unwrap();
    fresh["callId"] = json!(format!("call_{:032x}", 12));
    denied(
        &host,
        &binding,
        &serde_json::to_vec(&fresh).unwrap(),
        Code::Busy,
    );
    if existing {
        // Genuine external change AFTER selection; backup must contain these
        // bytes rather than the selected baseline or editor's captured source.
        fs::write(&path, b"actual external target").unwrap();
    }
    let action = begin(&id, 13);
    let work = write_work(&host, &binding, &action);
    assert_eq!(work.request_id(), &id);
    let (again, state) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    assert_eq!(save_state(state).phase, "pending");
    let mut view = work.run().unwrap();
    let confirm = raw(
        14,
        json!({"kind": "confirmSave", "requestId": id,
        "decision": "OverwriteWithActualBackup"}),
    );
    if existing {
        assert_eq!(view.phase, "external-conflict");
        assert_eq!(
            view.external_hash,
            Some(crate::windows_write::digest(b"actual external target"))
        );
        assert_eq!(view.external_bytes, Some(b"actual external target".len()));
        assert!(view.adoption.is_none());
        assert_eq!(fs::read(&path).unwrap(), b"actual external target");
        assert!(files.artifacts().is_empty());
        let (again, state) = reservation(reply(&host, &binding, &bytes));
        assert_eq!(again, id);
        same(&view, &save_state(state));
        view = write_work(&host, &binding, &confirm).run().unwrap();
        assert_eq!(
            fs::read(files.artifact(&id, "backup.bin")).unwrap(),
            b"actual external target"
        );
    }
    assert_eq!(view.phase, "written");
    assert_eq!(view.operation_id, id);
    assert_eq!(fs::read(&path).unwrap(), source);
    let adopted = view.adoption.as_ref().unwrap();
    assert_eq!(adopted.document_id, draft.document_id);
    let version = adopted.version.clone();
    same(&view, &save_state(host.state(&binding, &id).unwrap()));
    let snapshot = file_snapshot(&path);
    let artifacts = files.artifacts();
    let (again, state) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    same(&view, &save_state(state));
    same(
        &view,
        &save_state(state_reply(reply(&host, &binding, &action))),
    );
    if existing {
        same(
            &view,
            &save_state(state_reply(reply(&host, &binding, &confirm))),
        );
    }
    assert_eq!(file_snapshot(&path), snapshot);
    assert_eq!(files.artifacts(), artifacts);
    // A new call with the consumed target cannot manufacture another SaveAs.
    denied(
        &host,
        &binding,
        &serde_json::to_vec(&fresh).unwrap(),
        Code::Busy,
    ); // cached first failure
    fresh["callId"] = json!(format!("call_{:032x}", 15));
    denied(
        &host,
        &binding,
        &serde_json::to_vec(&fresh).unwrap(),
        Code::Denied,
    );
    let ordinary = save(20, &draft.document_id, &version, b"ordinary follow-up");
    let (next, _) = reservation(reply(&host, &binding, &ordinary));
    assert_ne!(next, id);
    let next_view = write_work(&host, &binding, &begin(&next, 21))
        .run()
        .unwrap();
    assert_eq!(next_view.phase, "written");
    assert!(next_view.save_as.is_none());
    assert_ne!(next_view.adoption.unwrap().version, version);
    assert_eq!(fs::read(&path).unwrap(), b"ordinary follow-up");
    assert_eq!(
        fs::read(files.artifact(&next, "backup.bin")).unwrap(),
        source
    );
    let snapshot = file_snapshot(&path);
    let artifacts = files.artifacts();
    let release = raw(
        22,
        json!({"kind": "release", "grant": {"kind": "document", "documentId": draft.document_id}}),
    );
    assert!(matches!(
        reply(&host, &binding, &release),
        HostReply::Released {}
    ));
    assert!(matches!(
        reply(&host, &binding, &release),
        HostReply::Released {}
    ));
    denied(&host, &binding, &draft_raw, Code::Revoked);
    let (again, _) = reservation(reply(&host, &binding, &bytes));
    assert_eq!(again, id);
    assert_eq!(file_snapshot(&path), snapshot);
    assert_eq!(files.artifacts(), artifacts);
}

#[test]
fn native_save_as_absent_creates_once_adopts_and_supports_ordinary_save() {
    save_as_flow(false);
}

#[test]
fn native_save_as_existing_conflict_backs_up_actual_external_bytes_and_supports_ordinary_save() {
    save_as_flow(true);
}

#[test]
fn native_resource_lost_during_owned_read_drains_cancelled_without_late_grant() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    let path = files.file("read.cpp", b"actual unchanged source");
    let (id, _) = reservation(reply(
        &host,
        &binding,
        &raw(
            1,
            json!({"kind": "reserve", "intent": {"operation": "open"}}),
        ),
    ));
    let bytes = raw(2, json!({"kind": "open", "requestId": id}));
    let work = read_work(&host, &binding, &bytes);
    assert!(matches!(
        host.state(&binding, &id).unwrap(),
        Status::Pending {
            cancel_requested: false
        }
    ));
    struct TestOnlyResourceLostPicker {
        picker: TestOnlyPicker,
        host: NativeHost,
        binding: Binding,
    }
    impl NativePicker for TestOnlyResourceLostPicker {
        fn select(&mut self, kind: PickerKind) -> Result<Option<PathBuf>, Code> {
            let selected = self.picker.select(kind)?;
            // TEST_ONLY nativeResourceLost signal while the actual owned read
            // is executing outside the registry lock; no thread timing needed.
            self.host.revoke_native_view(&self.binding)?;
            Ok(selected)
        }
    }
    let mut picker = TestOnlyResourceLostPicker {
        picker: files.picker(&path, PickerKind::Open),
        host: host.clone(),
        binding: binding.clone(),
    };
    assert!(matches!(
        work.run(&mut picker).unwrap(),
        Status::Complete {
            result: Outcome::Cancelled {
                commit: "not-started"
            },
            ..
        }
    ));
    assert_eq!(picker.picker.calls, 1);
    assert_eq!(fs::read(&path).unwrap(), b"actual unchanged source");
    assert!(matches!(host.state(&binding, &id), Err(Code::Revoked)));
    denied(&host, &binding, &bytes, Code::Revoked);
    let fresh = active(&host);
    assert!(matches!(host.state(&fresh, &id), Err(Code::Denied)));
    assert!(files.artifacts().is_empty());
}

#[test]
fn native_resource_lost_with_owned_write_drains_actual_not_started_and_denies_new_owner() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    let path = files.file("write.cpp", b"original");
    let (_, doc) = open(&host, &binding, &files, &path);
    let version = doc.binding.unwrap().version;
    let bytes = save(10, &doc.document_id, &version, b"must not write");
    let (id, _) = reservation(reply(&host, &binding, &bytes));
    let work = write_work(&host, &binding, &begin(&id, 11));
    assert_eq!(
        save_state(host.state(&binding, &id).unwrap()).phase,
        "pending"
    );
    // TEST_ONLY nativeResourceLost with an outstanding owned WriteWork.
    host.revoke_native_view(&binding).unwrap();
    denied(&host, &binding, &bytes, Code::Revoked);
    let fresh = active(&host);
    let drained = work.run().unwrap();
    assert_eq!(drained.operation_id, id);
    assert_eq!(drained.phase, "not-started");
    assert_eq!(drained.reason, Some(Code::Revoked));
    assert!(drained.cancel_requested);
    assert!(drained.adoption.is_none());
    assert_eq!(fs::read(&path).unwrap(), b"original");
    assert!(files.artifacts().is_empty());
    assert!(matches!(host.state(&binding, &id), Err(Code::Revoked)));
    assert!(matches!(host.state(&fresh, &id), Err(Code::Denied)));
    denied(&host, &fresh, &begin(&id, 12), Code::Denied);
    denied(
        &host,
        &fresh,
        &save(13, &doc.document_id, &version, b"foreign"),
        Code::Denied,
    );
}

#[test]
fn resource_loss_after_real_write_keeps_written_evidence_and_never_relabels_it_cancelled() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    let path = files.file("written.cpp", b"old");
    let (_, doc) = open(&host, &binding, &files, &path);
    let version = doc.binding.unwrap().version;
    let bytes = save(10, &doc.document_id, &version, b"real effect");
    let (id, _) = reservation(reply(&host, &binding, &bytes));
    let written = write_work(&host, &binding, &begin(&id, 11)).run().unwrap();
    assert_eq!(written.phase, "written");
    let cancel = raw(12, json!({"kind": "cancel", "requestId": id}));
    let after_cancel = save_state(state_reply(reply(&host, &binding, &cancel)));
    assert_eq!(after_cancel.phase, "written");
    assert_eq!(after_cancel.operation_id, id);
    let snapshot = file_snapshot(&path);
    let artifacts = files.artifacts();
    assert!(!artifacts.is_empty());
    host.revoke_native_view(&binding).unwrap();
    host.revoke_native_view(&binding).unwrap();
    denied(&host, &binding, &bytes, Code::Revoked);
    denied(&host, &binding, &cancel, Code::Revoked);
    assert_eq!(written.phase, "written");
    assert_eq!(file_snapshot(&path), snapshot);
    assert_eq!(snapshot.0, b"real effect");
    assert_eq!(files.artifacts(), artifacts);
    assert_eq!(fs::read(files.artifact(&id, "backup.bin")).unwrap(), b"old");
    let fresh = active(&host);
    denied(
        &host,
        &fresh,
        &raw(13, json!({"kind": "recoverSave", "requestId": id})),
        Code::Denied,
    );
}

#[test]
fn dropping_undispatched_owned_work_settles_unavailable_and_allows_real_followup() {
    let files = TestOnlyFs::new();
    let host = files.host();
    let binding = active(&host);
    let path = files.file("drop.cpp", b"unchanged");
    let (id, _) = reservation(reply(
        &host,
        &binding,
        &raw(
            30,
            json!({"kind": "reserve", "intent": {"operation": "open"}}),
        ),
    ));
    drop(read_work(
        &host,
        &binding,
        &raw(31, json!({"kind": "open", "requestId": id})),
    ));
    assert!(matches!(
        host.state(&binding, &id).unwrap(),
        Status::Complete {
            result: Outcome::Failed {
                code: Code::Unavailable,
                ..
            },
            ..
        }
    ));
    let (_, doc) = open(&host, &binding, &files, &path);
    let version = doc.binding.unwrap().version;
    let bytes = save(10, &doc.document_id, &version, b"dropped snapshot");
    let (id, _) = reservation(reply(&host, &binding, &bytes));
    let action = begin(&id, 11);
    drop(write_work(&host, &binding, &action));
    let drained = save_state(host.state(&binding, &id).unwrap());
    assert_eq!(drained.phase, "not-started");
    assert_eq!(drained.reason, Some(Code::Unavailable));
    assert!(!drained.cancel_requested);
    same(
        &drained,
        &save_state(state_reply(reply(&host, &binding, &action))),
    );
    assert_eq!(fs::read(&path).unwrap(), b"unchanged");
    assert!(files.artifacts().is_empty());
    let (next, _) = reservation(reply(
        &host,
        &binding,
        &save(12, &doc.document_id, &version, b"real follow-up"),
    ));
    assert_ne!(next, id);
    assert_eq!(
        write_work(&host, &binding, &begin(&next, 13))
            .run()
            .unwrap()
            .phase,
        "written"
    );
    assert_eq!(fs::read(&path).unwrap(), b"real follow-up");
}

#[test]
fn native_host_restart_inspects_history_without_minting_old_document_authority() {
    let files = TestOnlyFs::new();
    let host = files.host();
    assert!(host.recovery_records().unwrap().is_empty());
    let binding = active(&host);
    let path = files.file("restart.cpp", b"original external");
    let (_, document) = open(&host, &binding, &files, &path);
    let version = document.binding.unwrap().version;
    let (id, _) = reservation(reply(
        &host,
        &binding,
        &save(10, &document.document_id, &version, b"captured source"),
    ));
    assert_eq!(
        write_work(&host, &binding, &begin(&id, 11))
            .run()
            .unwrap()
            .phase,
        "written"
    );
    // Current live operations are not silently added to the startup catalog.
    assert!(matches!(host.inspect_recovery(&id), Err(Code::Denied)));
    drop(host);
    let reopened = files.host();
    let catalog = reopened.recovery_records().unwrap();
    assert_eq!(catalog.len(), 1);
    assert_eq!(catalog[0].operation_id, id);
    let observed = reopened.inspect_recovery(&id).unwrap();
    assert_eq!(observed.payload, b"captured source");
    assert_eq!(
        observed.backup.as_deref(),
        Some(b"original external".as_slice())
    );
    assert!(matches!(
        observed.current,
        crate::CurrentTargetObservation::Unchanged { .. }
    ));
    let fresh = active(&reopened);
    assert!(matches!(reopened.state(&binding, &id), Err(Code::Denied)));
    assert!(matches!(
        reopened.state(&fresh, &id),
        Err(Code::UnknownRequest)
    ));
    denied(
        &reopened,
        &fresh,
        &save(12, &document.document_id, &version, b"forged"),
        Code::Denied,
    );
    fs::write(&path, b"changed later").unwrap();
    assert!(matches!(reopened.inspect_recovery(&id).unwrap().current,
        crate::CurrentTargetObservation::Changed { bytes, .. } if bytes == b"changed later"));
    assert_eq!(
        reopened.recovery_records().unwrap()[0].phase,
        "written-receipt"
    );
    assert_eq!(fs::read(&path).unwrap(), b"changed later");
    let before = files.artifacts();
    let list = serde_json::to_value(reply(
        &reopened,
        &fresh,
        &raw(20, json!({"kind":"listRecovery","offset":0,"limit":1})),
    ))
    .unwrap();
    assert_eq!(list["kind"], "recoveryList");
    assert_eq!(list["total"], 1);
    assert_eq!(list["items"][0]["operationId"], id.as_str());
    assert!(list["items"][0].get("documentId").is_none());
    assert!(list["items"][0].get("path").is_none());
    let view = serde_json::to_value(reply(
        &reopened,
        &fresh,
        &raw(21, json!({"kind":"compareRecovery","operationId":id})),
    ))
    .unwrap();
    assert_eq!(view["kind"], "recoveryComparison");
    assert_eq!(view["comparison"]["current"]["status"], "changed");
    assert_eq!(
        view["comparison"]["payload"]["sourceBase64"],
        STANDARD.encode(b"captured source")
    );
    assert_eq!(
        view["comparison"]["backup"]["sourceBase64"],
        STANDARD.encode(b"original external")
    );
    assert_eq!(files.artifacts(), before);
    assert_eq!(fs::read(&path).unwrap(), b"changed later");
    denied(
        &reopened,
        &fresh,
        &raw(22, json!({"kind":"listRecovery","offset":0,"limit":0})),
        Code::InvalidInput,
    );
    denied(
        &reopened,
        &fresh,
        &raw(23, json!({"kind":"listRecovery","offset":0,"limit":33})),
        Code::InvalidInput,
    );
    denied(
        &reopened,
        &fresh,
        &raw(
            24,
            json!({"kind":"compareRecovery","operationId":id,"path":"forged.cpp"}),
        ),
        Code::InvalidInput,
    );
    let quarantined = reopened.prepare_native_view().unwrap();
    denied(
        &reopened,
        &quarantined,
        &raw(25, json!({"kind":"listRecovery","offset":0,"limit":1})),
        Code::Unavailable,
    );
    reopened.revoke_native_view(&fresh).unwrap();
    denied(
        &reopened,
        &fresh,
        &raw(26, json!({"kind":"compareRecovery","operationId":id})),
        Code::Revoked,
    );
}
