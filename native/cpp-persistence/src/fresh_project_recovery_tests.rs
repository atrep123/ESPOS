//! Actual inert Windows/NTFS fixtures, executed only after the main agent wires
//! the new module. No GUI, SDK, compiler job, target-project access or cleanup.
//! Every fixture/artifact remains under this crate's test-tmp directory.
use super::*;
use serde_json::{json, Value};
use std::io::Write;

struct Fixture {
    directory: PathBuf,
    operation: RequestId,
    intent: Value,
    payloads: [Vec<u8>; 4],
}
impl Fixture {
    fn new() -> Self {
        let base = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp");
        let directory = base.join(format!(
            "fresh-recovery-{}",
            windows_read::random_hex().unwrap()
        ));
        fs::create_dir_all(&directory).unwrap();
        assert!(directory.starts_with(base));
        let operation: RequestId = serde_json::from_value(json!(format!(
            "request_{}",
            windows_read::random_hex().unwrap()
        )))
        .unwrap();
        let payloads = [
            b"// TEST_ONLY inert source, never compiled\n".to_vec(),
            b"{\"TEST_ONLY\":true}\n".to_vec(),
            b"# TEST_ONLY inert CMake, never executed\n".to_vec(),
            "# TEST_ONLY žluťoučký; historical evidence only\n"
                .as_bytes()
                .to_vec(),
        ];
        let proofs: Vec<_> = Role::ALL
            .into_iter()
            .map(|role| {
                let bytes = &payloads[role.index()];
                // Reuse the engine's actual serialized proof structure.
                FileProof {
                    role: ROLES[role.index()],
                    bytes: bytes.len(),
                    sha256: windows_write::digest(bytes),
                }
            })
            .collect();
        let scope: Scope = serde_json::from_value(json!({
            "schema": 1, "operation": operation,
            "session": "a".repeat(32), "incarnation": "b".repeat(32),
            "document": format!("doc_{}", "c".repeat(32)), "version": null,
            "source_hash": proofs[0].sha256, "source_bytes": proofs[0].bytes,
        }))
        .unwrap();
        let intent = json!({
            "schema": "espos.fresh-project-intent.v1", "scope": scope,
            // Deliberately not an admissible Windows filesystem path. It must
            // remain historical display data and must NEVER be opened.
            "root": "TEST_ONLY untrusted ../never-open:root", "files": proofs,
        });
        Self {
            directory,
            operation,
            intent,
            payloads,
        }
    }
    fn write(&self, may_write: bool, verified: bool) {
        self.write_intent(&self.intent);
        for role in Role::ALL {
            fs::write(
                self.directory.join(FixedFile::Payload(role).name()),
                &self.payloads[role.index()],
            )
            .unwrap();
        }
        if may_write {
            fs::write(
                self.directory.join("may-write.json"),
                br#"{"schema":"espos.fresh-project-may-write.v1"}"#,
            )
            .unwrap();
        }
        if verified {
            fs::write(
                self.directory.join("verified.json"),
                serde_json::to_vec(&self.intent["files"]).unwrap(),
            )
            .unwrap();
        }
    }
    fn write_intent(&self, intent: &Value) {
        fs::write(
            self.directory.join("intent.json"),
            serde_json::to_vec(intent).unwrap(),
        )
        .unwrap();
    }
    fn operation(&self) -> CataloguedOperation {
        CataloguedOperation::from_host_catalogued_directory(&self.directory, &self.operation)
            .unwrap()
    }
    fn inspect(&self) -> Inspection {
        self.operation().inspect()
    }
    fn invalid(&self, code: Code) {
        let result = self.inspect();
        assert_eq!(result.phase, HistoricalPhase::Invalid);
        assert_eq!(result.invalid_code, Some(code));
        assert!(!result.current_file_proof);
        assert!(result.payload_proofs.is_none());
        assert!(result.historical_scope.is_none());
        assert!(result.historical_root.is_none());
    }
}

#[test]
fn prepared_may_write_verified_are_distinct_historical_observations() {
    for (may, verified, phase) in [
        (false, false, HistoricalPhase::Prepared),
        (true, false, HistoricalPhase::MayWrite),
        (true, true, HistoricalPhase::Verified),
    ] {
        let fixture = Fixture::new();
        fixture.write(may, verified);
        let result = fixture.inspect(); // Successful snapshot requires real NTFS.
        assert_eq!(result.phase, phase);
        assert_eq!(result.invalid_code, None);
        assert!(!result.current_file_proof);
        assert_eq!(
            result.historical_root.as_deref(),
            fixture.intent["root"].as_str()
        );
        assert_eq!(
            result.historical_scope.unwrap().operation,
            fixture.operation
        );
        let proofs = result.payload_proofs.unwrap();
        for role in Role::ALL {
            let index = role.index();
            assert_eq!(proofs[index].role, ROLES[index]);
            assert_eq!(proofs[index].bytes, fixture.payloads[index].len());
            assert_eq!(
                proofs[index].sha256,
                windows_write::digest(&fixture.payloads[index])
            );
        }
        // Only fixed journal artifacts exist; inspection created nothing.
        assert_eq!(
            fs::read_dir(&fixture.directory).unwrap().count(),
            5 + usize::from(may) + usize::from(verified)
        );
    }
}

#[test]
fn missing_intent_or_any_payload_is_invalid_and_never_repaired() {
    for missing in 0..5 {
        let fixture = Fixture::new();
        if missing != 4 {
            fixture.write_intent(&fixture.intent);
        }
        for role in Role::ALL {
            if missing != role.index() {
                fs::write(
                    fixture.directory.join(FixedFile::Payload(role).name()),
                    &fixture.payloads[role.index()],
                )
                .unwrap();
            }
        }
        fixture.invalid(Code::InvalidInput);
        assert_eq!(fs::read_dir(&fixture.directory).unwrap().count(), 4);
    }
}

#[test]
fn verified_without_may_write_is_invalid() {
    let fixture = Fixture::new();
    fixture.write(false, true);
    fixture.invalid(Code::Conflict);
    assert!(!fixture.directory.join("may-write.json").exists());
}

#[test]
fn cached_verified_never_hides_actual_payload_changes_in_any_role() {
    for role in Role::ALL {
        let fixture = Fixture::new();
        fixture.write(true, true);
        let mut changed = fixture.payloads[role.index()].clone();
        changed[0] = b'!'; // Same length, valid UTF-8; actual hash must differ.
        fs::write(
            fixture.directory.join(FixedFile::Payload(role).name()),
            &changed,
        )
        .unwrap();
        fixture.invalid(Code::Conflict);
    }
}

#[test]
fn wrong_sizes_hashes_roles_counts_and_extra_keys_are_invalid() {
    for change in 0..9 {
        let fixture = Fixture::new();
        fixture.write(true, true);
        let mut intent = fixture.intent.clone();
        match change {
            0 => intent["files"][1]["bytes"] = json!(1),
            1 => intent["files"][1]["sha256"] = json!("0".repeat(64)),
            2 => intent["files"][1]["role"] = json!("../outside"),
            3 => intent["files"][1]["role"] = intent["files"][0]["role"].clone(),
            4 => {
                intent["files"].as_array_mut().unwrap().pop();
            }
            5 => {
                intent["files"].as_array_mut().unwrap().push(json!({}));
            }
            6 => intent["files"][1]["extra"] = json!(true),
            7 => intent["extra"] = json!(true),
            _ => intent["scope"]["extra"] = json!(true),
        }
        fixture.write_intent(&intent);
        let result = fixture.inspect();
        assert_eq!(result.phase, HistoricalPhase::Invalid);
        assert!(!result.current_file_proof);
        assert!(result.payload_proofs.is_none());
    }
}

#[test]
fn scope_and_catalogued_operation_must_agree() {
    for change in 0..6 {
        let fixture = Fixture::new();
        fixture.write(false, false);
        let mut intent = fixture.intent.clone();
        match change {
            0 => intent["scope"]["operation"] = json!(format!("request_{}", "d".repeat(32))),
            1 => intent["scope"]["source_bytes"] = json!(1),
            2 => intent["scope"]["source_hash"] = json!("0".repeat(64)),
            3 => intent["scope"]["schema"] = json!(2),
            4 => intent["scope"]["session"] = json!("bad historical session"),
            _ => {
                intent["scope"].as_object_mut().unwrap().remove("version");
            }
        }
        fixture.write_intent(&intent);
        assert_eq!(fixture.inspect().phase, HistoricalPhase::Invalid);
    }
}

#[test]
fn json_cannot_override_the_catalogued_directory() {
    for key in ["directory", "operationDir", "catalogDir", "schemaRootPath"] {
        let fixture = Fixture::new();
        fixture.write(false, false);
        let mut intent = fixture.intent.clone();
        intent[key] = json!("C:\\TEST_ONLY-never-open");
        fixture.write_intent(&intent);
        fixture.invalid(Code::InvalidInput);
    }
}

#[test]
fn malformed_or_duplicate_marker_keys_and_false_verified_are_invalid() {
    for (name, bytes) in [
        ("may-write.json", b"{".as_slice()),
        ("may-write.json", br#"{"schema":"wrong"}"#.as_slice()),
        ("may-write.json", br#"{"schema":"espos.fresh-project-may-write.v1","extra":0}"#.as_slice()),
        ("may-write.json", br#"{"schema":"espos.fresh-project-may-write.v1","schema":"espos.fresh-project-may-write.v1"}"#.as_slice()),
        ("verified.json", b"[]".as_slice()),
        ("verified.json", br#"{"status":"verified"}"#.as_slice()),
    ] {
        let fixture = Fixture::new();
        fixture.write(true, true);
        fs::write(fixture.directory.join(name), bytes).unwrap();
        fixture.invalid(Code::InvalidInput);
    }
}

#[test]
fn actual_utf8_nul_and_empty_bounds_apply_even_with_matching_metadata() {
    for role in Role::ALL {
        for invalid in [vec![], vec![0], vec![0xff]] {
            let mut fixture = Fixture::new();
            let index = role.index();
            fixture.payloads[index] = invalid;
            fixture.intent["files"][index]["bytes"] = json!(fixture.payloads[index].len());
            fixture.intent["files"][index]["sha256"] =
                json!(windows_write::digest(&fixture.payloads[index]));
            if index == 0 {
                fixture.intent["scope"]["source_bytes"] =
                    fixture.intent["files"][0]["bytes"].clone();
                fixture.intent["scope"]["source_hash"] =
                    fixture.intent["files"][0]["sha256"].clone();
            }
            fixture.write(true, true);
            fixture.invalid(Code::InvalidInput);
        }
    }
}

#[test]
fn declared_oversize_is_rejected_before_payload_open() {
    for role in Role::ALL {
        let fixture = Fixture::new();
        fixture.write(false, false);
        let mut intent = fixture.intent.clone();
        intent["files"][role.index()]["bytes"] = json!(role.cap() + 1);
        fixture.write_intent(&intent);
        // Incompatible writer would make any attempted payload open fail Busy.
        let held = OpenOptions::new()
            .write(true)
            .share_mode(0)
            .open(fixture.directory.join(FixedFile::Payload(role).name()))
            .unwrap();
        fixture.invalid(Code::TooLarge);
        drop(held);
    }
}

#[test]
fn actual_oversize_payloads_and_markers_are_bounded_before_reading() {
    for kind in [
        FixedFile::Intent,
        FixedFile::MayWrite,
        FixedFile::Verified,
        FixedFile::Payload(Role::Source),
        FixedFile::Payload(Role::Manifest),
        FixedFile::Payload(Role::CMake),
        FixedFile::Payload(Role::Traceability),
    ] {
        let fixture = Fixture::new();
        fixture.write(true, true);
        OpenOptions::new()
            .write(true)
            .open(fixture.directory.join(kind.name()))
            .unwrap()
            .set_len(kind.cap() as u64 + 1)
            .unwrap();
        fixture.invalid(Code::TooLarge);
    }
}

#[test]
fn exact_payload_byte_caps_including_multibyte_utf8_are_accepted() {
    let mut fixture = Fixture::new();
    for role in Role::ALL {
        let index = role.index();
        fixture.payloads[index] = "ž".repeat(role.cap() / 2).into_bytes();
        fixture.intent["files"][index]["bytes"] = json!(fixture.payloads[index].len());
        fixture.intent["files"][index]["sha256"] =
            json!(windows_write::digest(&fixture.payloads[index]));
    }
    fixture.intent["scope"]["source_bytes"] = fixture.intent["files"][0]["bytes"].clone();
    fixture.intent["scope"]["source_hash"] = fixture.intent["files"][0]["sha256"].clone();
    fixture.write(true, true);
    assert_eq!(fixture.inspect().phase, HistoricalPhase::Verified);
}

#[test]
fn ntfs_hardlinks_and_named_streams_are_refused_for_all_fixed_artifacts() {
    for kind in [
        FixedFile::Intent,
        FixedFile::MayWrite,
        FixedFile::Verified,
        FixedFile::Payload(Role::Source),
        FixedFile::Payload(Role::Manifest),
        FixedFile::Payload(Role::CMake),
        FixedFile::Payload(Role::Traceability),
    ] {
        for hardlink in [false, true] {
            let fixture = Fixture::new();
            fixture.write(true, true);
            let path = fixture.directory.join(kind.name());
            if hardlink {
                fs::hard_link(&path, fixture.directory.join("TEST_ONLY-second-link")).unwrap();
            } else {
                let stream = format!("{}:TEST_ONLY", path.to_str().unwrap());
                File::create(stream)
                    .unwrap()
                    .write_all(b"TEST_ONLY inert ADS")
                    .unwrap();
            }
            fixture.invalid(Code::UnsupportedPath);
        }
    }
}

#[test]
fn held_artifact_and_directory_handles_are_readonly_and_pin_namespace() {
    let fixture = Fixture::new();
    fixture.write(true, true);
    let operation = fixture.operation();
    let payload = NamedPrimary::required(&operation, FixedFile::Payload(Role::Source)).unwrap();
    assert!(OpenOptions::new()
        .write(true)
        .open(fixture.directory.join("payload-0.bin"))
        .is_err());
    assert!(fs::rename(
        &fixture.directory,
        fixture.directory.with_extension("TEST_ONLY-renamed")
    )
    .is_err());
    let mut borrowed = &payload.file;
    assert!(borrowed.write_all(b"TEST_ONLY forbidden").is_err());
    operation.pins.check().unwrap();
    drop(payload);
    drop(operation);
    assert!(OpenOptions::new()
        .write(true)
        .open(fixture.directory.join("payload-0.bin"))
        .is_ok());
}

#[test]
fn unsafe_native_directory_paths_fail_before_opening() {
    let fixture = Fixture::new();
    for path in [
        "relative",
        "C:\\TEST_ONLY\\..\\escape",
        "C:\\TEST_ONLY:ads",
        "\\\\server\\share\\TEST_ONLY",
    ] {
        assert!(matches!(
            CataloguedOperation::from_host_catalogued_directory(
                Path::new(path),
                &fixture.operation
            ),
            Err(Code::UnsupportedPath)
        ));
    }
}
