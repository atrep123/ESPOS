//! Actual NativeHost/Registry and inert NTFS files; TEST_ONLY view/picker seams.
use super::*;
use serde_json::json;

struct Fixture {
    root: PathBuf,
    parent: PathBuf,
    host: NativeHost,
    binding: Binding,
    draft: DraftBinding,
}
struct Picker {
    path: Option<PathBuf>,
    calls: usize,
}
impl ProjectParentPicker for Picker {
    fn select_parent(&mut self) -> Result<Option<PathBuf>, Code> {
        self.calls += 1;
        Ok(self.path.clone())
    }
}
fn live(host: &NativeHost) -> Binding {
    let binding = host.prepare_native_view().unwrap();
    let ticket = host.native_document_started(&binding).unwrap();
    host.native_document_finished(ticket).unwrap();
    binding
}
impl Fixture {
    fn new() -> Self {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("test-tmp")
            .join(format!(
                "host-project-{}",
                crate::owned_job_nonce().unwrap()
            ));
        fs::create_dir_all(&root).unwrap();
        let parent = root.join("selected-parent");
        fs::create_dir(&parent).unwrap();
        let storage = root.join("native-storage");
        fs::create_dir(&storage).unwrap();
        let host = NativeHost::open_local(&storage).unwrap();
        let binding = live(&host);
        let raw = serde_json::to_vec(&json!({"callId":"call_00000000000000000000000000000001",
            "command":{"kind":"bindDraft","revision":1,
                "sourceBase64":STANDARD.encode(b"// TEST_ONLY\r\nint count=1;\r\n")}}))
        .unwrap();
        let HostDispatch::Reply(HostReply::Draft { binding: draft }) =
            host.dispatch(&binding, &raw).unwrap()
        else {
            panic!("TEST_ONLY expected native capture")
        };
        Self {
            root,
            parent,
            host,
            binding,
            draft,
        }
    }
    fn work(&self) -> ProjectWork {
        self.host
            .prepare_fresh_project(
                &self.binding,
                &self.draft.document_id,
                1,
                "test_app".into(),
                companions(),
            )
            .unwrap()
    }
}
fn companions() -> [Vec<u8>; 3] {
    [
        b"{}\n".to_vec(),
        b"# TEST_ONLY cmake\n".to_vec(),
        b"# TEST_ONLY trace\n".to_vec(),
    ]
}

fn project_command(f: &Fixture) -> serde_json::Value {
    let [manifest, cmake, traceability] = companions();
    json!({"kind":"createProject","documentId":f.draft.document_id,"revision":1,
        "directoryName":"test_app","manifestBase64":STANDARD.encode(manifest),
        "cmakeBase64":STANDARD.encode(cmake),"traceabilityBase64":STANDARD.encode(traceability)})
}
fn raw_call(call: u64, command: serde_json::Value) -> Vec<u8> {
    serde_json::to_vec(&json!({"callId":format!("call_{call:032x}"),"command":command})).unwrap()
}
fn project_reply(host: &NativeHost, binding: &Binding, raw: &[u8]) -> (RequestId, ProjectStatus) {
    let HostDispatch::Reply(HostReply::ProjectState { request_id, state }) =
        host.dispatch(binding, raw).unwrap()
    else {
        panic!("TEST_ONLY expected project state, never new work on replay")
    };
    (request_id, state)
}

#[test]
fn json_project_replay_before_during_after_io_never_starts_another_work() {
    let f = Fixture::new();
    let raw = raw_call(20, project_command(&f));
    let HostDispatch::Project(work) = f.host.dispatch(&f.binding, &raw).unwrap() else {
        panic!()
    };
    let operation = work.request_id().clone();
    let (replay_id, status) = project_reply(&f.host, &f.binding, &raw);
    assert_eq!(replay_id, operation);
    assert!(matches!(status, ProjectStatus::Reserved {}));
    struct ReplayPicker<'a> {
        fixture: &'a Fixture,
        raw: &'a [u8],
    }
    impl ProjectParentPicker for ReplayPicker<'_> {
        fn select_parent(&mut self) -> Result<Option<PathBuf>, Code> {
            assert!(matches!(
                project_reply(&self.fixture.host, &self.fixture.binding, self.raw).1,
                ProjectStatus::Running {}
            ));
            Ok(Some(self.fixture.parent.clone()))
        }
    }
    let status = work
        .run(&mut ReplayPicker {
            fixture: &f,
            raw: &raw,
        })
        .unwrap();
    assert!(matches!(status, ProjectStatus::Created { .. }));
    let (_, status) = project_reply(&f.host, &f.binding, &raw);
    let ProjectStatus::Created { document, files } = status else {
        panic!()
    };
    assert_eq!(document.document_id, f.draft.document_id);
    let dto = serde_json::to_value(HostReply::ProjectState {
        request_id: operation,
        state: ProjectStatus::Created { document, files },
    })
    .unwrap();
    assert_eq!(dto["kind"], "projectState");
    assert_eq!(dto["state"]["files"][0]["role"], "app/src/main.cpp");
    assert!(dto["state"]["document"].get("root").is_none());
    assert_eq!(f.host.state.lock().unwrap().projects.len(), 1);
}

#[test]
fn json_project_call_collision_and_owner_checks_happen_before_picker() {
    let f = Fixture::new();
    let mut command = project_command(&f);
    let raw = raw_call(21, command.clone());
    let HostDispatch::Project(work) = f.host.dispatch(&f.binding, &raw).unwrap() else {
        panic!()
    };
    command["directoryName"] = json!("other");
    assert!(matches!(
        f.host.dispatch(&f.binding, &raw_call(21, command)),
        Err(Code::InvalidInput)
    ));
    let other = live(&f.host);
    let status = json!({"kind":"projectStatus","requestId":work.request_id()});
    assert!(matches!(
        f.host.dispatch(&other, &raw_call(22, status)),
        Err(Code::Denied)
    ));
    let cancel = json!({"kind":"cancelProject","requestId":work.request_id()});
    assert!(matches!(
        f.host.dispatch(&other, &raw_call(23, cancel)),
        Err(Code::Denied)
    ));
    f.host.revoke_native_view(&f.binding).unwrap();
    assert!(matches!(
        f.host.dispatch(&f.binding, &raw),
        Err(Code::Revoked)
    ));
    let mut picker = Picker {
        path: Some(f.parent.clone()),
        calls: 0,
    };
    work.run(&mut picker).unwrap();
    assert_eq!(picker.calls, 0);
    assert!(!f.parent.join("test_app").exists());
}

#[test]
fn json_project_cancel_is_intent_until_owned_work_drains() {
    let f = Fixture::new();
    let raw = raw_call(24, project_command(&f));
    let HostDispatch::Project(work) = f.host.dispatch(&f.binding, &raw).unwrap() else {
        panic!()
    };
    let id = work.request_id().clone();
    let cancel = raw_call(25, json!({"kind":"cancelProject","requestId":id}));
    assert!(matches!(
        project_reply(&f.host, &f.binding, &cancel).1,
        ProjectStatus::Reserved {}
    ));
    assert!(f.host.has_project_work(&f.binding).unwrap());
    let mut picker = Picker {
        path: Some(f.parent.clone()),
        calls: 0,
    };
    assert!(matches!(
        work.run(&mut picker).unwrap(),
        ProjectStatus::Incomplete {
            code: Code::Revoked,
            may_have_written: false
        }
    ));
    assert_eq!(picker.calls, 0);
    let status = raw_call(26, json!({"kind":"projectStatus","requestId":id}));
    assert!(matches!(
        project_reply(&f.host, &f.binding, &status).1,
        ProjectStatus::Incomplete {
            code: Code::Revoked,
            may_have_written: false
        }
    ));
    assert!(matches!(
        project_reply(&f.host, &f.binding, &raw).1,
        ProjectStatus::Incomplete {
            code: Code::Revoked,
            may_have_written: false
        }
    ));
    assert!(!f.parent.join("test_app").exists());
}

#[test]
fn json_project_rejects_path_authority_source_override_and_unsafe_revision() {
    let f = Fixture::new();
    for (key, value) in [
        ("root", json!(f.parent)),
        ("sourceBase64", json!(STANDARD.encode(b"other"))),
        ("directoryName", json!("../outside")),
        ("revision", json!(9_007_199_254_740_992u64)),
    ] {
        let mut command = project_command(&f);
        command[key] = value;
        assert!(matches!(
            f.host.dispatch(&f.binding, &raw_call(27, command)),
            Err(Code::InvalidInput)
        ));
    }
    let mut command = project_command(&f);
    command["revision"] = json!(2);
    assert!(matches!(
        f.host.dispatch(&f.binding, &raw_call(28, command)),
        Err(Code::Conflict)
    ));
    assert!(f.host.state.lock().unwrap().projects.is_empty());
    assert!(!f.host.project_storage.exists());
}

#[test]
fn json_project_companions_are_canonical_bounded_utf8_and_nonempty() {
    let f = Fixture::new();
    for (index, value, code) in [
        (0, "".into(), Code::InvalidInput),
        (1, "eA".into(), Code::InvalidInput),
        (2, STANDARD.encode([0xff]), Code::InvalidInput),
        (3, STANDARD.encode(b"x\0"), Code::InvalidInput),
        (4, STANDARD.encode(vec![b'x'; 65_537]), Code::TooLarge),
    ] {
        let mut command = project_command(&f);
        command["manifestBase64"] = json!(value);
        assert!(
            matches!(f.host.dispatch(&f.binding, &raw_call(30+index, command)), Err(actual) if actual==code)
        );
    }
    let mut command = project_command(&f);
    command["manifestBase64"] = json!(STANDARD.encode(vec![b'x'; 65_536]));
    assert!(matches!(
        f.host.dispatch(&f.binding, &raw_call(40, command)),
        Ok(HostDispatch::Project(_))
    ));
    assert!(!f.host.project_storage.exists());
}

#[test]
fn json_project_decode_rejects_duplicate_fields_and_fractional_revision() {
    let f = Fixture::new();
    let raw = String::from_utf8(raw_call(42, project_command(&f))).unwrap();
    for replacement in ["\"revision\":1,\"revision\":1", "\"revision\":1.5"] {
        let changed = raw.replace("\"revision\":1", replacement);
        assert!(matches!(
            decode_host_request(changed.as_bytes()),
            Err(Code::InvalidInput)
        ));
    }
}

#[test]
fn json_project_history_is_closed_readonly_and_no_live_document_restored() {
    let f = Fixture::new();
    let work = f.work();
    let operation = work.request_id().clone();
    let storage = f.host.project_storage.parent().unwrap().to_path_buf();
    work.run(&mut Picker {
        path: Some(f.parent.clone()),
        calls: 0,
    })
    .unwrap();
    let target = f.parent.join("test_app/app/src/main.cpp");
    let before = fs::read(&target).unwrap();
    drop(f.host);
    let restarted = NativeHost::open_local(&storage).unwrap();
    let binding = live(&restarted);
    let HostDispatch::Reply(HostReply::ProjectRecoveryIds { items }) = restarted
        .dispatch(
            &binding,
            &raw_call(43, json!({"kind":"listProjectRecovery"})),
        )
        .unwrap()
    else {
        panic!()
    };
    assert_eq!(items, vec![operation.clone()]);
    let HostDispatch::Reply(HostReply::ProjectRecoveryView { inspection }) = restarted
        .dispatch(
            &binding,
            &raw_call(
                44,
                json!({"kind":"inspectProjectRecovery","operationId":operation}),
            ),
        )
        .unwrap()
    else {
        panic!()
    };
    assert_eq!(inspection.historical_phase, "verified");
    assert!(!inspection.current_file_proof);
    assert_eq!(inspection.payload_proofs.len(), 4);
    assert_eq!(restarted.state.lock().unwrap().registry.documents.len(), 0);
    assert_eq!(fs::read(target).unwrap(), before);
}

#[test]
fn actual_host_group_adopts_exact_source_into_same_native_document() {
    let f = Fixture::new();
    let work = f.work();
    let id = work.request_id().clone();
    assert!(f.host.has_project_work(&f.binding).unwrap());
    let mut picker = Picker {
        path: Some(f.parent.clone()),
        calls: 0,
    };
    let ProjectStatus::Created { document, files } = work.run(&mut picker).unwrap() else {
        panic!()
    };
    assert_eq!(picker.calls, 1);
    assert_eq!(document.document_id, f.draft.document_id);
    assert_eq!(
        document.source_base64,
        STANDARD.encode(b"// TEST_ONLY\r\nint count=1;\r\n")
    );
    assert_eq!(
        document.saved_base64.as_ref(),
        Some(&document.source_base64)
    );
    assert!(document.binding.is_some());
    assert_eq!(files.len(), 4);
    assert!(matches!(
        f.host.project_status(&f.binding, &id).unwrap(),
        ProjectStatus::Created { .. }
    ));
    assert!(!f.host.has_project_work(&f.binding).unwrap());
    let state = f.host.state.lock().unwrap();
    assert_eq!(state.registry.documents.len(), 1); // No second native owner/grant.
    assert_eq!(
        state.registry.documents[&f.draft.document_id]
            .selection
            .as_ref()
            .unwrap()
            .bytes,
        b"// TEST_ONLY\r\nint count=1;\r\n"
    );
    assert!(f
        .root
        .starts_with(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp")));
}

#[test]
fn pending_group_blocks_native_source_replacement_and_duplicate_work() {
    let f = Fixture::new();
    let work = f.work();
    assert!(matches!(
        f.host.prepare_fresh_project(
            &f.binding,
            &f.draft.document_id,
            1,
            "other_app".into(),
            companions()
        ),
        Err(Code::Busy)
    ));
    let raw = serde_json::to_vec(&json!({"callId":"call_00000000000000000000000000000002",
        "command":{"kind":"bindDraft","revision":2,"sourceBase64":STANDARD.encode(b"changed")}}))
    .unwrap();
    assert!(matches!(f.host.dispatch(&f.binding, &raw), Err(Code::Busy)));
    drop(work);
    assert!(!f.host.has_project_work(&f.binding).unwrap());
    assert!(matches!(
        f.host.dispatch(&f.binding, &raw),
        Ok(HostDispatch::Reply(HostReply::Draft { .. }))
    ));
}

#[test]
fn foreign_binding_document_and_revision_cannot_prepare_or_read_work() {
    let f = Fixture::new();
    let foreign = live(&f.host);
    assert!(matches!(
        f.host.prepare_fresh_project(
            &foreign,
            &f.draft.document_id,
            1,
            "test_app".into(),
            companions()
        ),
        Err(Code::Denied)
    ));
    assert!(matches!(
        f.host.prepare_fresh_project(
            &f.binding,
            &f.draft.document_id,
            2,
            "test_app".into(),
            companions()
        ),
        Err(Code::Conflict)
    ));
    let work = f.work();
    assert!(matches!(
        f.host.project_status(&foreign, work.request_id()),
        Err(Code::Denied)
    ));
    assert!(matches!(
        f.host.cancel_project(&foreign, work.request_id()),
        Err(Code::Denied)
    ));
}

#[test]
fn cancelled_or_revoked_work_never_opens_picker_or_creates_target() {
    for revoke in [false, true] {
        let f = Fixture::new();
        let work = f.work();
        if revoke {
            f.host.revoke_native_view(&f.binding).unwrap();
        } else {
            f.host
                .cancel_project(&f.binding, work.request_id())
                .unwrap();
        }
        let mut picker = Picker {
            path: Some(f.parent.clone()),
            calls: 0,
        };
        assert!(matches!(
            work.run(&mut picker).unwrap(),
            ProjectStatus::Incomplete {
                code: Code::Revoked,
                may_have_written: false
            }
        ));
        assert_eq!(picker.calls, 0);
        assert_eq!(fs::read_dir(&f.parent).unwrap().count(), 0);
        assert!(!f.host.has_project_work(&f.binding).unwrap());
    }
}

#[test]
fn picker_cancellation_and_drop_keep_source_unsaved_and_release_owned_work() {
    let f = Fixture::new();
    let work = f.work();
    let mut picker = Picker {
        path: None,
        calls: 0,
    };
    assert!(matches!(
        work.run(&mut picker).unwrap(),
        ProjectStatus::Cancelled {
            commit: "not-started"
        }
    ));
    assert!(!f.host.has_project_work(&f.binding).unwrap());
    let work = f.work();
    let id = work.request_id().clone();
    drop(work);
    assert!(matches!(
        f.host.project_status(&f.binding, &id).unwrap(),
        ProjectStatus::Incomplete {
            code: Code::Unavailable,
            may_have_written: false
        }
    ));
    let state = f.host.state.lock().unwrap();
    assert!(state.registry.documents[&f.draft.document_id]
        .selection
        .is_none());
}

#[test]
fn revocation_during_picker_is_rechecked_before_filesystem_effects() {
    let f = Fixture::new();
    let work = f.work();
    struct Revoker<'a>(&'a Fixture);
    impl ProjectParentPicker for Revoker<'_> {
        fn select_parent(&mut self) -> Result<Option<PathBuf>, Code> {
            self.0.host.revoke_native_view(&self.0.binding).unwrap();
            Ok(Some(self.0.parent.clone()))
        }
    }
    assert!(matches!(
        work.run(&mut Revoker(&f)).unwrap(),
        ProjectStatus::Incomplete {
            code: Code::Revoked,
            may_have_written: false
        }
    ));
    assert_eq!(fs::read_dir(&f.parent).unwrap().count(), 0);
}

#[test]
fn existing_target_is_preserved_and_source_never_marked_saved() {
    let f = Fixture::new();
    let work = f.work();
    let root = f.parent.join("test_app");
    fs::create_dir(&root).unwrap();
    fs::write(root.join("keep.txt"), b"TEST_ONLY preserve").unwrap();
    let mut picker = Picker {
        path: Some(f.parent.clone()),
        calls: 0,
    };
    assert!(matches!(
        work.run(&mut picker).unwrap(),
        ProjectStatus::Incomplete {
            code: Code::Conflict,
            may_have_written: false
        }
    ));
    assert_eq!(
        fs::read(root.join("keep.txt")).unwrap(),
        b"TEST_ONLY preserve"
    );
    assert!(
        f.host.state.lock().unwrap().registry.documents[&f.draft.document_id]
            .selection
            .is_none()
    );
}

#[test]
fn partial_group_effect_is_reported_unknown_and_never_marks_document_saved() {
    let f = Fixture::new();
    let work = f.work();
    crate::fresh_project::FAIL_AFTER.with(|value| value.set(2));
    let mut picker = Picker {
        path: Some(f.parent.clone()),
        calls: 0,
    };
    let result = work.run(&mut picker).unwrap();
    crate::fresh_project::FAIL_AFTER.with(|value| value.set(0));
    assert!(matches!(
        result,
        ProjectStatus::Incomplete {
            code: Code::IOFailure,
            may_have_written: true
        }
    ));
    assert!(f.parent.join("test_app/app/src/main.cpp").is_file());
    assert!(f.parent.join("test_app/tabos-app.json").is_file());
    assert!(!f.parent.join("test_app/CMakeLists.txt").exists());
    assert!(!f.host.has_project_work(&f.binding).unwrap());
    let state = f.host.state.lock().unwrap();
    assert!(state.registry.documents[&f.draft.document_id]
        .selection
        .is_none());
    assert!(state.registry.documents[&f.draft.document_id]
        .draft_capture
        .is_some());
}

#[test]
fn restart_catalogue_is_readonly_history_and_never_restores_document_authority() {
    let f = Fixture::new();
    let work = f.work();
    let operation = work.request_id().clone();
    let storage = f.host.project_storage.parent().unwrap().to_path_buf();
    let mut picker = Picker {
        path: Some(f.parent.clone()),
        calls: 0,
    };
    assert!(matches!(
        work.run(&mut picker).unwrap(),
        ProjectStatus::Created { .. }
    ));
    drop(f.host);
    let restarted = NativeHost::open_local(&storage).unwrap();
    let binding = live(&restarted);
    assert_eq!(
        restarted.project_recovery_ids(&binding).unwrap(),
        vec![operation.clone()]
    );
    let inspected = restarted
        .inspect_project_recovery(&binding, &operation)
        .unwrap();
    assert_eq!(inspected.historical_phase, "verified");
    assert!(!inspected.current_file_proof);
    assert_eq!(inspected.payload_proofs.len(), 4);
    assert_eq!(restarted.state.lock().unwrap().registry.documents.len(), 0);
    assert!(matches!(
        restarted.inspect_project_recovery(&binding, &RequestId::mint().unwrap()),
        Err(Code::UnknownRequest)
    ));
}

#[test]
fn changed_historical_payload_remains_invalid_without_touching_current_project() {
    let f = Fixture::new();
    let work = f.work();
    let operation = work.request_id().clone();
    let storage = f.host.project_storage.parent().unwrap().to_path_buf();
    let journal = f
        .host
        .project_storage
        .join(format!("{}-project", operation.as_str()));
    let mut picker = Picker {
        path: Some(f.parent.clone()),
        calls: 0,
    };
    work.run(&mut picker).unwrap();
    let target = f.parent.join("test_app/app/src/main.cpp");
    let before = fs::read(&target).unwrap();
    drop(f.host);
    fs::write(journal.join("payload-1.bin"), b"{\"changed\":true}\n").unwrap();
    let restarted = NativeHost::open_local(&storage).unwrap();
    let binding = live(&restarted);
    let inspected = restarted
        .inspect_project_recovery(&binding, &operation)
        .unwrap();
    assert_eq!(inspected.historical_phase, "invalid");
    assert!(!inspected.current_file_proof);
    assert!(inspected.payload_proofs.is_empty());
    assert_eq!(fs::read(&target).unwrap(), before);
    assert_eq!(
        fs::read(journal.join("payload-1.bin")).unwrap(),
        b"{\"changed\":true}\n"
    );
}
