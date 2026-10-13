//! Pure TEST_ONLY typed inspections plus genuine Windows host restart fixtures.
//! Picker/lifecycle callbacks are TEST_ONLY, not editor IPC or physical UI proof.
//! Execution belongs to main; fresh crate/test-tmp GUID fixtures are retained.
use super::*;
use crate::{DocumentId, RecoveryRecord, RecoveryScope, Version};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::path::PathBuf;

// Existing opaque-ID parser only constructs fixture identities. Neither the
// inspection nor the comparison has a Deserialize codec.
fn request(n: u8) -> RequestId {
    serde_json::from_value(json!(format!("request_{n:032x}"))).unwrap()
}
fn document(n: u8) -> DocumentId {
    serde_json::from_value(json!(format!("doc_{n:032x}"))).unwrap()
}
fn version(n: u8) -> Version {
    serde_json::from_value(json!(format!("version_{n:032x}"))).unwrap()
}
fn independent_hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn expected_revision(bytes: &[u8]) -> Value {
    json!({
        "sourceBase64": STANDARD.encode(bytes),
        "sourceHash": independent_hash(bytes),
        "sourceBytes": bytes.len(),
    })
}
fn wire(inspection: RecoveryInspection) -> Value {
    serde_json::to_value(comparison_view(inspection).unwrap()).unwrap()
}
fn typed_inspection() -> RecoveryInspection {
    let payload = b"TEST_ONLY payload\0\xff\r\n".to_vec();
    let hash = independent_hash(&payload);
    RecoveryInspection {
        prior_record: RecoveryRecord {
            operation_id: request(1),
            document_id: document(2),
            source_hash: hash.clone(),
            source_bytes: payload.len(),
            display_name: "selected.cpp".into(),
            phase: "written-receipt",
            backup_available: true,
        },
        scope: RecoveryScope {
            schema: 1,
            operation_id: request(1),
            session: "a".repeat(32),
            incarnation: "b".repeat(32),
            document_id: document(2),
            captured_version: Some(version(3)),
            source_hash: hash.clone(),
            source_bytes: payload.len(),
        },
        native_path: PathBuf::from(r"C:\TEST_ONLY\selected.cpp"),
        current: CurrentTargetObservation::Unchanged {
            bytes: payload.clone(),
            hash,
        },
        payload,
        backup: Some(b"TEST_ONLY actual external\0\xfe".to_vec()),
    }
}
fn assert_error(inspection: RecoveryInspection, expected: Code) {
    assert!(matches!(comparison_view(inspection), Err(code) if code == expected));
}
fn set_payload(inspection: &mut RecoveryInspection, bytes: Vec<u8>) {
    let hash = independent_hash(&bytes);
    inspection.scope.source_hash = hash.clone();
    inspection.prior_record.source_hash = hash;
    inspection.scope.source_bytes = bytes.len();
    inspection.prior_record.source_bytes = bytes.len();
    inspection.payload = bytes;
}

#[test]
fn exact_wire_schema_contains_only_comparison_fields() {
    let inspection = typed_inspection();
    assert_eq!(
        wire(inspection.clone()),
        json!({
            "schemaVersion": 1,
            "operationId": request(1),
            "displayName": "selected.cpp",
            "historicalPhase": "written-receipt",
            "payload": expected_revision(&inspection.payload),
            "backup": expected_revision(inspection.backup.as_deref().unwrap()),
            "current": {
                "status": "unchanged",
                "sourceBase64": STANDARD.encode(&inspection.payload),
                "sourceHash": independent_hash(&inspection.payload),
                "sourceBytes": inspection.payload.len(),
            },
        })
    );
}

#[test]
fn historical_receipt_stays_historical_when_current_changed_or_missing() {
    let mut inspection = typed_inspection();
    let external = b"later external\0\x80";
    inspection.current = CurrentTargetObservation::Changed {
        bytes: external.to_vec(),
        hash: independent_hash(external),
    };
    let result = wire(inspection.clone());
    assert_eq!(result["historicalPhase"], "written-receipt");
    assert_eq!(result["current"]["status"], "changed");
    inspection.current = CurrentTargetObservation::Missing;
    let result = wire(inspection);
    assert_eq!(result["historicalPhase"], "written-receipt");
    assert_eq!(result["current"], json!({"status": "missing"}));
}

#[test]
fn every_current_state_has_exact_flattened_or_nonbyte_shape() {
    let bytes = b"observed\0\xfe\r\n";
    for status in [
        "unchanged",
        "changed",
        "present",
        "missing",
        "busy",
        "denied",
        "error",
    ] {
        let mut inspection = typed_inspection();
        let mut expected = json!({"status": status});
        inspection.current = match status {
            "unchanged" => {
                let revision = expected_revision(&inspection.payload);
                expected
                    .as_object_mut()
                    .unwrap()
                    .extend(revision.as_object().unwrap().clone());
                inspection.current.clone()
            }
            "changed" | "present" => {
                let revision = expected_revision(bytes);
                expected
                    .as_object_mut()
                    .unwrap()
                    .extend(revision.as_object().unwrap().clone());
                if status == "present" {
                    inspection.prior_record.phase = "recovery-required";
                    inspection.prior_record.backup_available = false;
                    inspection.backup = None;
                    CurrentTargetObservation::Present {
                        bytes: bytes.to_vec(),
                        hash: independent_hash(bytes),
                    }
                } else {
                    CurrentTargetObservation::Changed {
                        bytes: bytes.to_vec(),
                        hash: independent_hash(bytes),
                    }
                }
            }
            "missing" => CurrentTargetObservation::Missing,
            "busy" => CurrentTargetObservation::Busy,
            "denied" => CurrentTargetObservation::Denied,
            "error" => {
                expected["code"] = json!(Code::TooLarge);
                CurrentTargetObservation::Error {
                    code: Code::TooLarge,
                }
            }
            _ => unreachable!(),
        };
        assert_eq!(wire(inspection)["current"], expected, "{status}");
    }
    for code in [
        Code::Denied,
        Code::Busy,
        Code::InvalidInput,
        Code::TooLarge,
        Code::UnsupportedPath,
        Code::IOFailure,
        Code::Conflict,
        Code::UnknownRequest,
        Code::Revoked,
        Code::Unavailable,
    ] {
        let mut inspection = typed_inspection();
        inspection.current = CurrentTargetObservation::Error { code };
        assert_eq!(
            wire(inspection)["current"],
            json!({"status": "error", "code": code})
        );
    }
}

#[test]
fn malformed_hashes_are_rejected_in_both_historical_metadata_and_all_reads() {
    for bad in [
        String::new(),
        "a".repeat(63),
        "a".repeat(65),
        "A".repeat(64),
        "g".repeat(64),
        format!("{}\n", "a".repeat(63)),
        "é".repeat(32),
    ] {
        for field in ["scope", "record", "both"] {
            let mut inspection = typed_inspection();
            if field != "record" {
                inspection.scope.source_hash = bad.clone();
            }
            if field != "scope" {
                inspection.prior_record.source_hash = bad.clone();
            }
            assert_error(inspection, Code::InvalidInput);
        }
        for status in ["unchanged", "changed", "present"] {
            let mut inspection = typed_inspection();
            let bytes = inspection.payload.clone();
            inspection.current = match status {
                "unchanged" => CurrentTargetObservation::Unchanged {
                    bytes,
                    hash: bad.clone(),
                },
                "changed" => CurrentTargetObservation::Changed {
                    bytes,
                    hash: bad.clone(),
                },
                _ => {
                    inspection.prior_record.phase = "recovery-required";
                    inspection.prior_record.backup_available = false;
                    inspection.backup = None;
                    CurrentTargetObservation::Present {
                        bytes,
                        hash: bad.clone(),
                    }
                }
            };
            assert_error(inspection, Code::InvalidInput);
        }
    }
}

#[test]
fn well_formed_but_false_hashes_and_counts_cannot_describe_different_bytes() {
    for field in ["scope", "record", "both"] {
        let mut inspection = typed_inspection();
        let wrong = independent_hash(b"other");
        if field != "record" {
            inspection.scope.source_hash = wrong.clone();
        }
        if field != "scope" {
            inspection.prior_record.source_hash = wrong;
        }
        assert_error(inspection, Code::Conflict);
        let mut inspection = typed_inspection();
        if field != "record" {
            inspection.scope.source_bytes += 1;
        }
        if field != "scope" {
            inspection.prior_record.source_bytes += 1;
        }
        assert_error(inspection, Code::Conflict);
    }
    let mut inspection = typed_inspection();
    inspection.payload[0] ^= 1;
    assert_error(inspection, Code::Conflict);
    for status in ["unchanged", "changed", "present"] {
        let mut inspection = typed_inspection();
        let bytes = inspection.payload.clone();
        let hash = independent_hash(b"not the read bytes");
        inspection.current = match status {
            "unchanged" => CurrentTargetObservation::Unchanged { bytes, hash },
            "changed" => CurrentTargetObservation::Changed { bytes, hash },
            _ => {
                inspection.prior_record.phase = "recovery-required";
                inspection.prior_record.backup_available = false;
                inspection.backup = None;
                CurrentTargetObservation::Present { bytes, hash }
            }
        };
        assert_error(inspection, Code::Conflict);
    }
}

#[test]
fn malformed_scope_ids_phase_display_and_table_tuples_fail_closed() {
    for schema in [0, 2, 255] {
        let mut inspection = typed_inspection();
        inspection.scope.schema = schema;
        assert_error(inspection, Code::InvalidInput);
    }
    for bad in [
        "".into(),
        "a".repeat(31),
        "a".repeat(33),
        "A".repeat(32),
        "g".repeat(32),
        format!("{}\\", "a".repeat(31)),
    ] {
        for session in [true, false] {
            let mut inspection = typed_inspection();
            if session {
                inspection.scope.session = bad.clone();
            } else {
                inspection.scope.incarnation = bad.clone();
            }
            assert_error(inspection, Code::InvalidInput);
        }
    }
    // Opaque typed IDs cannot be malformed through safe public construction;
    // exercise the converter's lexical defense directly as well as mismatches.
    for prefix in ["request_", "doc_", "version_"] {
        assert!(valid_id(&format!("{prefix}{}", "a".repeat(32)), prefix));
        for suffix in [
            "".into(),
            "a".repeat(31),
            "a".repeat(33),
            "A".repeat(32),
            "g".repeat(32),
            "../".into(),
        ] {
            assert!(!valid_id(&format!("{prefix}{suffix}"), prefix));
        }
        assert!(!valid_id(&format!("foreign_{}", "a".repeat(32)), prefix));
    }
    let mut inspection = typed_inspection();
    inspection.scope.operation_id = request(9);
    assert_error(inspection, Code::Conflict);
    let mut inspection = typed_inspection();
    inspection.scope.document_id = document(9);
    assert_error(inspection, Code::Conflict);
    for phase in [
        "",
        "written",
        "saved",
        "currentSaved",
        "Written-receipt",
        "recovery-required ",
    ] {
        let mut inspection = typed_inspection();
        inspection.prior_record.phase = phase;
        assert_error(inspection, Code::InvalidInput);
    }
    for display in [
        "",
        "else.cpp",
        "../selected.cpp",
        "C:\\selected.cpp",
        "selected.cpp\n",
    ] {
        let mut inspection = typed_inspection();
        inspection.prior_record.display_name = display.into();
        assert_error(inspection, Code::InvalidInput);
    }
    let mut inspection = typed_inspection();
    inspection.prior_record.backup_available = false;
    assert_error(inspection, Code::InvalidInput);
    let mut inspection = typed_inspection();
    inspection.backup = None;
    assert_error(inspection, Code::InvalidInput);
    for phase in ["written-receipt", "recovery-required"] {
        let mut inspection = typed_inspection();
        inspection.prior_record.phase = phase;
        inspection.current = CurrentTargetObservation::Present {
            bytes: vec![],
            hash: independent_hash(b""),
        };
        assert_error(inspection, Code::InvalidInput);
    }
    for unchanged in [true, false] {
        let mut inspection = typed_inspection();
        inspection.prior_record.phase = "recovery-required";
        inspection.prior_record.backup_available = false;
        inspection.backup = None;
        if !unchanged {
            inspection.current = CurrentTargetObservation::Changed {
                bytes: vec![],
                hash: independent_hash(b""),
            };
        }
        assert_error(inspection, Code::InvalidInput);
    }
    let mut inspection = typed_inspection();
    inspection.backup = None;
    inspection.prior_record.backup_available = false;
    inspection.current = CurrentTargetObservation::Present {
        bytes: vec![],
        hash: independent_hash(b""),
    };
    assert_error(inspection, Code::InvalidInput);
}

#[test]
fn unchanged_requires_historical_reference_bytes_but_changed_can_have_same_bytes() {
    let mut inspection = typed_inspection();
    let bytes = b"other bytes".to_vec();
    inspection.current = CurrentTargetObservation::Unchanged {
        hash: independent_hash(&bytes),
        bytes,
    };
    assert_error(inspection, Code::Conflict);
    let mut inspection = typed_inspection();
    inspection.prior_record.phase = "recovery-required";
    assert_error(inspection.clone(), Code::Conflict);
    let bytes = inspection.backup.clone().unwrap();
    inspection.current = CurrentTargetObservation::Unchanged {
        hash: independent_hash(&bytes),
        bytes,
    };
    assert_eq!(wire(inspection)["current"]["status"], "unchanged");
    let mut inspection = typed_inspection();
    inspection.current = CurrentTargetObservation::Changed {
        bytes: inspection.payload.clone(),
        hash: independent_hash(&inspection.payload),
    };
    assert_eq!(wire(inspection)["current"]["status"], "changed");
}

#[test]
fn no_backup_is_null_and_real_empty_backup_is_a_revision() {
    let mut inspection = typed_inspection();
    inspection.backup = None;
    inspection.prior_record.backup_available = false;
    assert_eq!(wire(inspection.clone())["backup"], Value::Null);
    inspection.prior_record.phase = "recovery-required";
    inspection.current = CurrentTargetObservation::Missing;
    assert_eq!(wire(inspection)["backup"], Value::Null);
    let mut inspection = typed_inspection();
    inspection.backup = Some(vec![]);
    assert_eq!(wire(inspection)["backup"], expected_revision(b""));
}

#[test]
fn phase_backup_current_table_accepts_only_inspector_possible_tuples() {
    for written in [true, false] {
        for overwrite in [true, false] {
            for status in [
                "unchanged",
                "changed",
                "present",
                "missing",
                "busy",
                "denied",
                "error",
            ] {
                let mut inspection = typed_inspection();
                inspection.prior_record.phase = if written {
                    "written-receipt"
                } else {
                    "recovery-required"
                };
                inspection.prior_record.backup_available = overwrite;
                if !overwrite {
                    inspection.backup = None;
                }
                let bytes = if status == "unchanged" && !written && overwrite {
                    inspection.backup.clone().unwrap()
                } else {
                    inspection.payload.clone()
                };
                let hash = independent_hash(&bytes);
                inspection.current = match status {
                    "unchanged" => CurrentTargetObservation::Unchanged { bytes, hash },
                    "changed" => CurrentTargetObservation::Changed { bytes, hash },
                    "present" => CurrentTargetObservation::Present { bytes, hash },
                    "missing" => CurrentTargetObservation::Missing,
                    "busy" => CurrentTargetObservation::Busy,
                    "denied" => CurrentTargetObservation::Denied,
                    _ => CurrentTargetObservation::Error {
                        code: Code::IOFailure,
                    },
                };
                let allowed = match status {
                    "present" => !written && !overwrite,
                    "unchanged" | "changed" => written || overwrite,
                    _ => true,
                };
                let result = comparison_view(inspection);
                assert_eq!(
                    result.is_ok(),
                    allowed,
                    "written={written} overwrite={overwrite} current={status}"
                );
                match result {
                    Ok(result) => {
                        let result = serde_json::to_value(result).unwrap();
                        assert_eq!(result["current"]["status"], status);
                        assert_eq!(result["backup"].is_null(), !overwrite);
                    }
                    Err(code) => assert_eq!(code, Code::InvalidInput),
                }
            }
        }
    }
}

#[test]
fn each_raw_vector_accepts_one_mib_and_rejects_one_byte_more() {
    let maximum = vec![0xff; MAX_SOURCE_BYTES];
    let mut inspection = typed_inspection();
    set_payload(&mut inspection, maximum.clone());
    inspection.backup = Some(maximum.clone());
    inspection.current = CurrentTargetObservation::Unchanged {
        bytes: maximum.clone(),
        hash: independent_hash(&maximum),
    };
    let result = wire(inspection);
    for field in ["payload", "backup", "current"] {
        assert_eq!(result[field]["sourceBytes"], MAX_SOURCE_BYTES);
        assert_eq!(
            STANDARD
                .decode(result[field]["sourceBase64"].as_str().unwrap())
                .unwrap(),
            maximum
        );
    }
    let oversized = vec![0xfe; MAX_SOURCE_BYTES + 1];
    let mut inspection = typed_inspection();
    set_payload(&mut inspection, oversized.clone());
    assert_error(inspection, Code::TooLarge);
    let mut inspection = typed_inspection();
    inspection.payload = oversized.clone();
    assert_error(inspection, Code::TooLarge);
    let mut inspection = typed_inspection();
    inspection.backup = Some(oversized.clone());
    assert_error(inspection, Code::TooLarge);
    for field in ["scope", "record"] {
        let mut inspection = typed_inspection();
        if field == "scope" {
            inspection.scope.source_bytes = MAX_SOURCE_BYTES + 1;
        } else {
            inspection.prior_record.source_bytes = MAX_SOURCE_BYTES + 1;
        }
        assert_error(inspection, Code::TooLarge);
    }
    for status in ["unchanged", "changed", "present"] {
        let mut inspection = typed_inspection();
        let bytes = oversized.clone();
        let hash = independent_hash(&bytes);
        inspection.current = match status {
            "unchanged" => CurrentTargetObservation::Unchanged { bytes, hash },
            "changed" => CurrentTargetObservation::Changed { bytes, hash },
            _ => {
                inspection.prior_record.phase = "recovery-required";
                inspection.prior_record.backup_available = false;
                inspection.backup = None;
                CurrentTargetObservation::Present { bytes, hash }
            }
        };
        assert_error(inspection, Code::TooLarge);
    }
}

fn crc32(bytes: &[u8]) -> u32 {
    let mut crc = !0u32;
    for byte in bytes {
        crc ^= *byte as u32;
        for _ in 0..8 {
            crc = (crc >> 1) ^ (0xedb88320 & (0u32.wrapping_sub(crc & 1)));
        }
    }
    !crc
}

#[test]
fn raw_binary_bom_crlf_and_crc_roundtrip_without_text_normalization() {
    assert_eq!(crc32(b"123456789"), 0xcbf43926);
    assert_eq!(
        independent_hash(b""),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
    assert_eq!(
        independent_hash(b"abc"),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
    let all_bytes: Vec<u8> = (0..=255).collect();
    for bytes in [
        b"".as_slice(),
        b"abc".as_slice(),
        b"\xef\xbb\xbfraw\0\xff\xfe\r\n\r\n".as_slice(),
        b"\xff\xfeA\0\r\0\n\0".as_slice(),
        all_bytes.as_slice(),
    ] {
        let mut inspection = typed_inspection();
        set_payload(&mut inspection, bytes.to_vec());
        inspection.backup = Some(bytes.to_vec());
        inspection.current = CurrentTargetObservation::Unchanged {
            bytes: bytes.to_vec(),
            hash: independent_hash(bytes),
        };
        let result = wire(inspection);
        for field in ["payload", "backup", "current"] {
            let decoded = STANDARD
                .decode(result[field]["sourceBase64"].as_str().unwrap())
                .unwrap();
            assert_eq!(decoded, bytes);
            assert_eq!(crc32(&decoded), crc32(bytes));
            assert_eq!(result[field]["sourceHash"], independent_hash(bytes));
            assert_eq!(result[field]["sourceBytes"], bytes.len());
        }
    }
}

// Only these genuine fixture tests perform OS I/O; the converter above is pure.
use crate::host::{Binding, HostDispatch, HostReply, NativeHost};
use crate::{NativePicker, Outcome, PickerKind, Status};
use std::{collections::BTreeMap, fs, io::Write, os::windows::fs::MetadataExt};

struct TestOnlyFs {
    root: PathBuf,
    storage: PathBuf,
    target: PathBuf,
}
impl TestOnlyFs {
    fn new() -> Self {
        let base = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp");
        fs::create_dir_all(&base).unwrap();
        let nonce = crate::owned_job_nonce().unwrap();
        let root = base.join(format!(
            "recovery-view-{}-{}-{}-{}-{}",
            &nonce[..8],
            &nonce[8..12],
            &nonce[12..16],
            &nonce[16..20],
            &nonce[20..]
        ));
        assert_eq!(root.parent(), Some(base.as_path()));
        fs::create_dir(&root).unwrap();
        let storage = root.join("app-storage");
        fs::create_dir(&storage).unwrap();
        let target = root.join("selected.cpp");
        Self {
            root,
            storage,
            target,
        }
    }
    // No Drop cleanup: unique test fixtures and recovery artifacts are retained.
    fn snapshot(&self) -> BTreeMap<PathBuf, (Vec<u8>, u64, u64, u32)> {
        let mut paths: Vec<_> = fs::read_dir(self.storage.join("cpp-recovery-v1"))
            .unwrap()
            .map(|entry| entry.unwrap().path())
            .collect();
        paths.push(self.target.clone());
        paths
            .into_iter()
            .map(|path| {
                let metadata = fs::metadata(&path).unwrap();
                let bytes = if path.file_name().unwrap() == "host.lock" {
                    vec![]
                } else {
                    fs::read(&path).unwrap()
                };
                (
                    path,
                    (
                        bytes,
                        metadata.len(),
                        metadata.last_write_time(),
                        metadata.file_attributes(),
                    ),
                )
            })
            .collect()
    }
}
struct TestOnlyPicker {
    root: PathBuf,
    path: PathBuf,
    expected_kind: PickerKind,
    calls: usize,
}
impl NativePicker for TestOnlyPicker {
    fn select(&mut self, kind: PickerKind) -> Result<Option<PathBuf>, Code> {
        assert_eq!(kind, self.expected_kind);
        assert_eq!(self.path.parent(), Some(self.root.as_path()));
        assert_eq!(
            self.path.extension().and_then(|value| value.to_str()),
            Some("cpp")
        );
        self.calls += 1;
        Ok(Some(self.path.clone()))
    }
}
fn dispatch(host: &NativeHost, binding: &Binding, call: u64, command: Value) -> HostDispatch {
    let raw =
        serde_json::to_vec(&json!({"callId": format!("call_{call:032x}"), "command": command}))
            .unwrap();
    host.dispatch(binding, &raw).unwrap()
}
fn reserve(host: &NativeHost, binding: &Binding, call: u64, command: Value) -> RequestId {
    let HostDispatch::Reply(HostReply::Reservation { request_id, state }) =
        dispatch(host, binding, call, command)
    else {
        panic!("expected native reservation")
    };
    match state {
        Status::Reserved => {}
        Status::Save { write } => {
            assert_eq!(write.phase, "reserved");
            assert_eq!(write.operation_id, request_id);
        }
        _ => panic!("expected reserved lifecycle or writer state"),
    }
    request_id
}
fn genuine_host_comparison(create: bool) {
    let fixture = TestOnlyFs::new();
    let old = b"\xef\xbb\xbfactual old\0\xff\r\n";
    let payload = b"\xef\xbb\xbfcaptured new\0\xfe\r\n";
    if !create {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&fixture.target)
            .unwrap();
        file.write_all(old).unwrap();
        file.sync_all().unwrap();
    }
    let host = NativeHost::open_local(&fixture.storage).unwrap();
    let binding = host.prepare_native_view().unwrap();
    // TEST_ONLY lifecycle; no installed bridge or navigation-authentication proof.
    let ticket = host.native_document_started(&binding).unwrap();
    host.native_document_finished(ticket).unwrap();
    let mut picker = TestOnlyPicker {
        root: fixture.root.clone(),
        path: fixture.target.clone(),
        expected_kind: if create {
            PickerKind::SaveTarget
        } else {
            PickerKind::Open
        },
        calls: 0,
    };
    let operation = if create {
        let HostDispatch::Reply(HostReply::Draft { binding: draft }) = dispatch(
            &host,
            &binding,
            1,
            json!({"kind": "bindDraft", "revision": 7, "sourceBase64": STANDARD.encode(payload)}),
        ) else {
            panic!("expected native captured draft")
        };
        let target_request = reserve(
            &host,
            &binding,
            2,
            json!({"kind": "reserve", "intent": {
                "operation": "chooseTarget", "documentId": draft.document_id,
            }}),
        );
        let HostDispatch::Read(work) = dispatch(
            &host,
            &binding,
            3,
            json!({"kind": "chooseTarget", "requestId": target_request, "documentId": draft.document_id}),
        ) else {
            panic!("expected native picker work")
        };
        let Status::Complete {
            result:
                Outcome::Selected {
                    target_grant_id,
                    target_state: crate::TargetState::Absent,
                    ..
                },
            ..
        } = work.run(&mut picker).unwrap()
        else {
            panic!("expected absent create target")
        };
        reserve(
            &host,
            &binding,
            4,
            json!({"kind": "reserveSaveAs", "documentId": draft.document_id,
            "targetGrantId": target_grant_id, "revision": draft.capture_revision,
            "sourceBase64": STANDARD.encode(payload)}),
        )
    } else {
        let open_request = reserve(
            &host,
            &binding,
            1,
            json!({"kind": "reserve", "intent": {"operation": "open"}}),
        );
        let HostDispatch::Read(work) = dispatch(
            &host,
            &binding,
            2,
            json!({"kind": "open", "requestId": open_request}),
        ) else {
            panic!("expected native open work")
        };
        let Status::Complete {
            result: Outcome::Opened { document },
            ..
        } = work.run(&mut picker).unwrap()
        else {
            panic!("expected native opened document")
        };
        let version = document.binding.unwrap().version;
        reserve(
            &host,
            &binding,
            3,
            json!({"kind": "reserveSave", "documentId": document.document_id,
            "version": version, "sourceBase64": STANDARD.encode(payload)}),
        )
    };
    assert_eq!(picker.calls, 1);
    let HostDispatch::Write(work) = dispatch(
        &host,
        &binding,
        5,
        json!({"kind": "beginSave", "requestId": operation}),
    ) else {
        panic!("expected native write work")
    };
    let saved = work.run().unwrap();
    assert_eq!(saved.phase, "written");
    assert_eq!(saved.source_hash, independent_hash(payload));
    assert!(host.recovery_records().unwrap().is_empty());
    drop(host);

    let host = NativeHost::open_local(&fixture.storage).unwrap();
    let catalog_before = serde_json::to_value(host.recovery_records().unwrap()).unwrap();
    assert_eq!(catalog_before.as_array().unwrap().len(), 1);
    let before = fixture.snapshot();
    let inspection = host.inspect_recovery(&operation).unwrap();
    assert_eq!(inspection.payload, payload);
    assert_eq!(
        inspection.backup.as_deref(),
        if create { None } else { Some(old.as_slice()) }
    );
    let result = wire(inspection);
    assert_eq!(result["operationId"], json!(operation));
    assert_eq!(result["displayName"], "selected.cpp");
    assert_eq!(result["historicalPhase"], "written-receipt");
    assert_eq!(result["payload"], expected_revision(payload));
    assert_eq!(
        result["backup"],
        if create {
            Value::Null
        } else {
            expected_revision(old)
        }
    );
    assert_eq!(result["current"]["status"], "unchanged");
    for key in ["sourceBase64", "sourceHash", "sourceBytes"] {
        assert_eq!(result["current"][key], expected_revision(payload)[key]);
    }
    assert_eq!(before, fixture.snapshot());
    assert_eq!(
        catalog_before,
        serde_json::to_value(host.recovery_records().unwrap()).unwrap()
    );

    // A later real target change keeps the written receipt historical.
    let later = b"later external\0\x80\r\n";
    fs::write(&fixture.target, later).unwrap();
    let before = fixture.snapshot();
    let result = wire(host.inspect_recovery(&operation).unwrap());
    assert_eq!(result["historicalPhase"], "written-receipt");
    assert_eq!(result["current"]["status"], "changed");
    assert_eq!(result["current"]["sourceHash"], independent_hash(later));
    assert_eq!(
        STANDARD
            .decode(result["current"]["sourceBase64"].as_str().unwrap())
            .unwrap(),
        later
    );
    assert_eq!(before, fixture.snapshot());
}

#[test]
fn genuine_native_host_save_drop_open_inspect_comparison_retains_actual_backup() {
    genuine_host_comparison(false);
}

#[test]
fn genuine_native_host_create_drop_open_inspect_comparison_has_no_backup() {
    genuine_host_comparison(true);
}
