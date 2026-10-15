//! TEST_ONLY native admission/pickers; actual Windows NTFS handles and writer.
use super::*;
use serde_json::json;
use std::fs;

const SOURCE: &[u8] = b"// TEST_ONLY saved app\r\nint value=1;\r\n";
const ROLES: [SavedAppRole; 4] = [
    SavedAppRole::Source,
    SavedAppRole::Manifest,
    SavedAppRole::CMake,
    SavedAppRole::Traceability,
];
fn companions() -> [Vec<u8>; 3] {
    [
        b"{}\n".to_vec(),
        b"# TEST_ONLY cmake\n".to_vec(),
        b"# TEST_ONLY trace\n".to_vec(),
    ]
}
fn live(host: &NativeHost) -> Binding {
    let binding = host.prepare_native_view().unwrap();
    host.native_document_finished(host.native_document_started(&binding).unwrap())
        .unwrap();
    binding
}
struct TestOnlyPicker(Option<PathBuf>);
impl ProjectParentPicker for TestOnlyPicker {
    fn select_parent(&mut self) -> Result<Option<PathBuf>, Code> {
        Ok(self.0.clone())
    }
}
impl ProjectRootPicker for TestOnlyPicker {
    fn select_root(&mut self) -> Result<Option<PathBuf>, Code> {
        Ok(self.0.clone())
    }
}
impl NativePicker for TestOnlyPicker {
    fn select(&mut self, _: PickerKind) -> Result<Option<PathBuf>, Code> {
        Ok(self.0.clone())
    }
}
struct Fixture {
    dir: PathBuf,
    root: PathBuf,
    storage: PathBuf,
    host: NativeHost,
    binding: Binding,
    doc: DocumentId,
    version: Version,
}
impl Fixture {
    fn new() -> Self {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("test-tmp")
            .join(format!("TEST_ONLY-snapshot-{}", owned_job_nonce().unwrap()));
        fs::create_dir_all(&dir).unwrap();
        let storage = dir.join("storage");
        fs::create_dir(&storage).unwrap();
        let parent = dir.join("parent");
        fs::create_dir(&parent).unwrap();
        let host = NativeHost::open_local(&storage).unwrap();
        let binding = live(&host);
        let draft = {
            let mut state = host.state.lock().unwrap();
            let owner = state.registrations[binding.slot].caller.clone();
            state
                .registry
                .bind_captured_draft(&owner, 1, SOURCE.to_vec())
                .unwrap()
        };
        let status = host
            .prepare_fresh_project(
                &binding,
                &draft.document_id,
                1,
                "test_app".into(),
                companions(),
            )
            .unwrap()
            .run(&mut TestOnlyPicker(Some(parent.clone())))
            .unwrap();
        let ProjectStatus::Created { document, .. } = status else {
            panic!("TEST_ONLY fresh")
        };
        Self {
            dir,
            root: parent.join("test_app"),
            storage,
            host,
            binding,
            doc: draft.document_id,
            version: document.binding.unwrap().version,
        }
    }
    fn work(&self) -> Result<SavedAppWork, Code> {
        self.host
            .prepare_saved_app_snapshot(&self.binding, &self.doc, &self.version, 1)
    }
    fn lease(&self) -> SavedAppLease {
        self.work().unwrap().run().unwrap()
    }
    fn call(&self, nonce: u64, command: serde_json::Value) -> Result<HostDispatch, Code> {
        self.host.dispatch(
            &self.binding,
            &serde_json::to_vec(&json!({"callId":format!("call_{nonce:032x}"),"command":command}))
                .unwrap(),
        )
    }
    fn save(&self, bytes: &[u8]) -> Result<HostDispatch, Code> {
        self.call(100, json!({"kind":"reserveSave","documentId":self.doc,"version":self.version,"sourceBase64":STANDARD.encode(bytes)}))
    }
}
fn assert_error<T>(result: Result<T, Code>, code: Code) {
    assert!(matches!(result, Err(c) if c == code));
}

#[test]
fn fresh_snapshot_is_exact_immutable_same_owner_and_not_an_ipc_capability() {
    let f = Fixture::new();
    let mut lease = f.lease();
    let [manifest, cmake, trace] = companions();
    for (role, bytes) in ROLES.into_iter().zip([SOURCE, &manifest, &cmake, &trace]) {
        assert_eq!(lease.bytes(role), bytes);
        assert_eq!(
            fs::read(crate::fresh_project::member(&f.root, role.relative_name())).unwrap(),
            bytes
        );
    }
    assert_eq!(lease.document_id(), &f.doc);
    assert_eq!(lease.version(), &f.version);
    assert_eq!(lease.draft_revision(), 1);
    lease.validate().unwrap();
    assert_eq!(f.host.state.lock().unwrap().registry.documents.len(), 1);
    for kind in [
        "prepareSavedAppSnapshot",
        "projectReopen",
        "captureSavedAppDraft",
    ] {
        assert_error(
            f.call(40, json!({"kind":kind,"root":f.root})),
            Code::InvalidInput,
        );
    }
}

#[test]
fn source_only_open_never_guesses_project_ancestry() {
    let f = Fixture::new();
    let foreign = live(&f.host);
    let (job, owner) = {
        let mut state = f.host.state.lock().unwrap();
        let owner = state.registrations[foreign.slot].caller.clone();
        let id = state.registry.reserve(&owner, Operation::Open).unwrap();
        let Start::Work(job) = state
            .registry
            .open(&owner, Request { request_id: id })
            .unwrap()
        else {
            panic!()
        };
        (job, owner)
    };
    let completion = job.run(&mut TestOnlyPicker(Some(crate::fresh_project::member(
        &f.root,
        "app/src/main.cpp",
    ))));
    let document = {
        let mut state = f.host.state.lock().unwrap();
        let Status::Complete {
            result: Outcome::Opened { document },
            ..
        } = state.registry.complete(completion).unwrap()
        else {
            panic!()
        };
        assert_eq!(state.registry.documents[&document.document_id].owner, owner);
        document
    };
    assert_error(
        f.host.prepare_saved_app_snapshot(
            &foreign,
            &document.document_id,
            &document.binding.unwrap().version,
            0,
        ),
        Code::Unavailable,
    );
}

#[test]
fn reopen_uses_native_root_picker_and_fresh_four_member_admission_after_restart() {
    let f = Fixture::new();
    let root = f.root.clone();
    let storage = f.storage.clone();
    let old_doc = f.doc.clone();
    drop(f);
    let host = NativeHost::open_local(&storage).unwrap();
    let binding = live(&host);
    assert_eq!(host.state.lock().unwrap().registry.documents.len(), 0);
    let work = host.prepare_project_reopen(&binding).unwrap();
    assert!(host.has_project_work(&binding).unwrap());
    let candidate = work.run(&mut TestOnlyPicker(Some(root))).unwrap().unwrap();
    assert_ne!(candidate.document_id, old_doc);
    assert!(!host.has_project_work(&binding).unwrap());
    let version = candidate.binding.unwrap().version;
    let mut lease = host
        .prepare_saved_app_snapshot(&binding, &candidate.document_id, &version, 0)
        .unwrap()
        .run()
        .unwrap();
    assert_eq!(lease.bytes(SavedAppRole::Source), SOURCE);
    lease.validate().unwrap();
}

#[test]
fn unsaved_stale_version_revision_and_foreign_owner_host_are_denied() {
    let f = Fixture::new();
    assert_error(
        f.host
            .prepare_saved_app_snapshot(&f.binding, &f.doc, &Version::mint().unwrap(), 1),
        Code::Conflict,
    );
    assert_error(
        f.host
            .prepare_saved_app_snapshot(&f.binding, &f.doc, &f.version, 2),
        Code::Conflict,
    );
    let foreign = live(&f.host);
    assert_error(
        f.host
            .prepare_saved_app_snapshot(&foreign, &f.doc, &f.version, 1),
        Code::Denied,
    );
    let other = Fixture::new();
    let mut lease = f.lease();
    assert_error(
        other
            .host
            .validate_saved_app_lease(&other.binding, &mut lease),
        Code::Denied,
    );
    assert_error(
        f.host.validate_saved_app_lease(&foreign, &mut lease),
        Code::Denied,
    );
    drop(lease);
    f.host
        .capture_saved_app_draft(
            &f.binding,
            &f.doc,
            &f.version,
            2,
            b"// TEST_ONLY unsaved".to_vec(),
        )
        .unwrap();
    assert_error(
        f.host
            .prepare_saved_app_snapshot(&f.binding, &f.doc, &f.version, 2),
        Code::Conflict,
    );
    assert_error(
        f.host
            .capture_saved_app_draft(&f.binding, &f.doc, &f.version, 1, SOURCE.to_vec()),
        Code::Conflict,
    );
    assert_error(
        f.host
            .capture_saved_app_draft(&f.binding, &f.doc, &f.version, 2, SOURCE.to_vec()),
        Code::Conflict,
    );
}

#[test]
fn every_member_change_or_same_bytes_replacement_is_a_conflict() {
    for role in ROLES {
        for replacement in [false, true] {
            let f = Fixture::new();
            let path = crate::fresh_project::member(&f.root, role.relative_name());
            let original = fs::read(&path).unwrap();
            if replacement {
                fs::rename(&path, f.dir.join("TEST_ONLY-old-member")).unwrap();
                fs::write(&path, &original).unwrap();
            } else {
                fs::write(&path, b"TEST_ONLY changed\n").unwrap();
            }
            assert_error(f.work().unwrap().run(), Code::Conflict);
            assert!(!f.host.has_project_work(&f.binding).unwrap());
            assert_eq!(
                fs::read(path).unwrap(),
                if replacement {
                    original
                } else {
                    b"TEST_ONLY changed\n".to_vec()
                }
            );
        }
    }
}

#[test]
fn read_locks_prevent_mutation_and_replacement_until_real_lease_drop() {
    let f = Fixture::new();
    let mut lease = f.lease();
    for role in ROLES {
        let path = crate::fresh_project::member(&f.root, role.relative_name());
        assert!(fs::write(&path, b"TEST_ONLY blocked").is_err());
        assert!(fs::rename(&path, f.dir.join("TEST_ONLY-renamed")).is_err());
        assert!(fs::remove_file(&path).is_err());
    }
    assert!(fs::rename(&f.root, f.dir.join("TEST_ONLY-root-moved")).is_err());
    lease.validate().unwrap();
    drop(lease);
    fs::write(f.root.join("tabos-app.json"), b"{}\n").unwrap();
    assert_eq!(fs::read(f.root.join("app/src/main.cpp")).unwrap(), SOURCE);
}

#[test]
fn native_namespace_provenance_detects_directory_replacement_after_creation() {
    let f = Fixture::new();
    let path = crate::fresh_project::member(&f.root, "app/src");
    // Windows may permit directory renames with metadata-only Pins. Retained
    // native identity must detect replacement even when OS rename is allowed.
    if fs::rename(&path, f.dir.join("TEST_ONLY-source-dir")).is_ok() {
        fs::create_dir(&path).unwrap();
        fs::write(path.join("main.cpp"), SOURCE).unwrap();
        assert_error(f.work().unwrap().run(), Code::Conflict);
    } else {
        f.lease().validate().unwrap();
    }
}

#[test]
fn bounds_layout_ads_and_hardlinks_fail_without_authority_or_cleanup() {
    for scenario in 0..5 {
        let f = Fixture::new();
        match scenario {
            0 => fs::write(f.root.join("tabos-app.json"), vec![b'x'; 65_537]).unwrap(),
            1 => fs::write(f.root.join("extra.txt"), b"TEST_ONLY keep").unwrap(),
            2 => {
                fs::hard_link(f.root.join("CMakeLists.txt"), f.dir.join("TEST_ONLY-link")).unwrap()
            }
            3 => fs::write(f.root.join("tabos-app.json:TEST_ONLY-stream"), b"TEST_ONLY").unwrap(),
            _ => fs::write(f.root.join("docs/UI_BACKEND_TRACEABILITY.md"), b"bad\0").unwrap(),
        }
        let root = f.root.clone();
        let storage = f.storage.clone();
        drop(f);
        let host = NativeHost::open_local(&storage).unwrap();
        let binding = live(&host);
        let result = host
            .prepare_project_reopen(&binding)
            .unwrap()
            .run(&mut TestOnlyPicker(Some(root.clone())));
        assert!(result.is_err());
        assert!(root.is_dir());
        assert_eq!(host.state.lock().unwrap().registry.documents.len(), 0);
        assert!(!host.has_project_work(&binding).unwrap());
    }
}

#[test]
fn junction_project_namespace_is_rejected_by_actual_ntfs_picker_read() {
    let f = Fixture::new();
    let root = f.root.clone();
    let storage = f.storage.clone();
    let alias = f.dir.join("TEST_ONLY-junction");
    drop(f);
    // TEST_ONLY inert fixture paths, no deletion, no GUI; create one junction.
    let output = std::process::Command::new("cmd.exe")
        .arg("/c")
        .arg("mklink")
        .arg("/J")
        .arg(&alias)
        .arg(&root)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let host = NativeHost::open_local(&storage).unwrap();
    let binding = live(&host);
    assert_error(
        host.prepare_project_reopen(&binding)
            .unwrap()
            .run(&mut TestOnlyPicker(Some(alias))),
        Code::UnsupportedPath,
    );
    assert_eq!(fs::read(root.join("app/src/main.cpp")).unwrap(), SOURCE);
}

#[test]
fn active_work_and_lease_exclude_save_save_as_release_and_duplicate_capture() {
    let f = Fixture::new();
    let work = f.work().unwrap();
    assert_error(f.work(), Code::Busy);
    assert_error(f.save(SOURCE), Code::Busy);
    assert_error(
        f.call(
            101,
            json!({"kind":"release","grant":{"kind":"document","documentId":f.doc}}),
        ),
        Code::Busy,
    );
    // Direct same-registry APIs also exclude work: host DTO checks aren't authority.
    {
        let mut state = f.host.state.lock().unwrap();
        let caller = state.registrations[f.binding.slot].caller.clone();
        let target = TargetId::mint().unwrap();
        assert_error(
            state
                .registry
                .reserve_save_as(&caller, &f.doc, &target, 1, SOURCE.to_vec()),
            Code::Busy,
        );
        assert_error(
            state.registry.release(
                &caller,
                Release::Document {
                    document_id: f.doc.clone(),
                },
            ),
            Code::Busy,
        );
    }
    let lease = work.run().unwrap();
    assert!(f.host.has_project_work(&f.binding).unwrap());
    assert_error(f.save(SOURCE), Code::Busy);
    drop(lease);
    assert!(!f.host.has_project_work(&f.binding).unwrap());
    assert!(f.call(103,json!({"kind":"reserveSave","documentId":f.doc,"version":f.version,"sourceBase64":STANDARD.encode(SOURCE)})).is_ok());
    assert_error(f.work(), Code::Busy); // unresolved native Save reservation
}

#[test]
fn save_same_root_updates_four_member_revision_and_exact_current_draft() {
    let f = Fixture::new();
    let old = f.lease().project_revision().clone();
    let bytes = b"// TEST_ONLY saved edit\r\nint value=2;\r\n";
    f.host
        .capture_saved_app_draft(&f.binding, &f.doc, &f.version, 2, bytes.to_vec())
        .unwrap();
    let HostDispatch::Reply(HostReply::Reservation { request_id, .. }) = f.save(bytes).unwrap()
    else {
        panic!()
    };
    let HostDispatch::Write(work) = f
        .call(102, json!({"kind":"beginSave","requestId":request_id}))
        .unwrap()
    else {
        panic!()
    };
    let written = work.run().unwrap();
    assert_eq!(written.phase, "written");
    let version = written.adoption.unwrap().version;
    assert_error(f.work(), Code::Conflict);
    let mut lease = f
        .host
        .prepare_saved_app_snapshot(&f.binding, &f.doc, &version, 2)
        .unwrap()
        .run()
        .unwrap();
    assert_eq!(lease.bytes(SavedAppRole::Source), bytes);
    assert_ne!(lease.project_revision(), &old);
    assert_eq!(lease.bytes(SavedAppRole::Manifest), b"{}\n");
    lease.validate().unwrap();
}

#[test]
fn save_as_elsewhere_clears_project_association_and_does_not_guess_new_root() {
    let f = Fixture::new();
    let target_path = f.dir.join("TEST_ONLY-save-as.cpp");
    let id = {
        let mut state = f.host.state.lock().unwrap();
        let caller = state.registrations[f.binding.slot].caller.clone();
        state
            .registry
            .reserve(&caller, Operation::ChooseTarget(f.doc.clone()))
            .unwrap()
    };
    let HostDispatch::Read(work) = f
        .call(
            104,
            json!({"kind":"chooseTarget","requestId":id,"documentId":f.doc}),
        )
        .unwrap()
    else {
        panic!()
    };
    let Status::Complete {
        result: Outcome::Selected {
            target_grant_id, ..
        },
        ..
    } = work
        .run(&mut TestOnlyPicker(Some(target_path.clone())))
        .unwrap()
    else {
        panic!()
    };
    let HostDispatch::Reply(HostReply::Reservation {request_id,..})=f.call(105,json!({"kind":"reserveSaveAs","documentId":f.doc,"targetGrantId":target_grant_id,"revision":1,"sourceBase64":STANDARD.encode(SOURCE)})).unwrap() else { panic!() };
    let HostDispatch::Write(work) = f
        .call(106, json!({"kind":"beginSave","requestId":request_id}))
        .unwrap()
    else {
        panic!()
    };
    let written = work.run().unwrap();
    assert_eq!(written.phase, "written");
    let version = written.adoption.unwrap().version;
    assert_error(
        f.host
            .prepare_saved_app_snapshot(&f.binding, &f.doc, &version, 1),
        Code::Unavailable,
    );
    assert_eq!(fs::read(target_path).unwrap(), SOURCE);
    assert_eq!(fs::read(f.root.join("app/src/main.cpp")).unwrap(), SOURCE);
}

#[test]
fn revocation_navigation_and_draft_change_cancel_but_preserve_busy_until_drop() {
    for mode in 0..3 {
        let f = Fixture::new();
        let mut lease = f.lease();
        match mode {
            0 => f.host.revoke_native_view(&f.binding).unwrap(),
            1 => assert_error(f.host.native_document_started(&f.binding), Code::Revoked),
            _ => f
                .host
                .capture_saved_app_draft(
                    &f.binding,
                    &f.doc,
                    &f.version,
                    2,
                    b"// TEST_ONLY dirty".to_vec(),
                )
                .unwrap(),
        }
        assert!(lease.cancel_requested());
        assert_error(lease.validate(), Code::Revoked);
        assert!(f.host.has_project_work(&f.binding).unwrap());
        assert!(fs::write(f.root.join("CMakeLists.txt"), b"blocked").is_err());
        assert_eq!(f.host.state.lock().unwrap().registry.documents.len(), 1);
        drop(lease);
        assert!(!f.host.has_project_work(&f.binding).unwrap());
        assert_eq!(fs::read(f.root.join("app/src/main.cpp")).unwrap(), SOURCE);
        if mode < 2 {
            assert_eq!(f.host.state.lock().unwrap().registry.documents.len(), 0);
        }
    }
}

#[test]
fn cancelled_snapshot_work_and_reopen_drop_drain_without_file_cleanup_or_success() {
    let f = Fixture::new();
    let work = f.work().unwrap();
    f.host.revoke_native_view(&f.binding).unwrap();
    assert!(f.host.has_project_work(&f.binding).unwrap());
    assert_error(work.run(), Code::Revoked);
    assert!(!f.host.has_project_work(&f.binding).unwrap());
    let binding = live(&f.host);
    let work = f.host.prepare_project_reopen(&binding).unwrap();
    assert!(f.host.has_project_work(&binding).unwrap());
    drop(work);
    assert!(!f.host.has_project_work(&binding).unwrap());
    assert_eq!(f.host.state.lock().unwrap().registry.documents.len(), 0);
    assert_eq!(fs::read(f.root.join("app/src/main.cpp")).unwrap(), SOURCE);
}

#[test]
fn concurrent_save_release_and_revoke_do_not_drain_the_live_lease() {
    let f = Fixture::new();
    let lease = f.lease();
    let host = f.host.clone();
    let binding = f.binding.clone();
    let doc = f.doc.clone();
    let version = f.version.clone();
    let thread = std::thread::spawn(move || {
        let mut state = host.state.lock().unwrap();
        let caller = state.registrations[binding.slot].caller.clone();
        assert_error(
            state
                .registry
                .reserve_save(&caller, &doc, &version, SOURCE.to_vec()),
            Code::Busy,
        );
        assert_error(
            state
                .registry
                .release(&caller, Release::Document { document_id: doc }),
            Code::Busy,
        );
        drop(state);
        host.revoke_native_view(&binding).unwrap();
    });
    thread.join().unwrap();
    assert!(lease.cancel_requested());
    assert!(f.host.has_project_work(&f.binding).unwrap());
    assert!(fs::write(f.root.join("tabos-app.json"), b"blocked").is_err());
    drop(lease);
    assert!(!f.host.has_project_work(&f.binding).unwrap());
    fs::write(f.root.join("tabos-app.json"), b"{}\n").unwrap();
}

#[test]
fn layout_change_during_lease_invalidates_and_does_not_remove_unrelated_files() {
    let f = Fixture::new();
    let mut lease = f.lease();
    let extra = f.root.join("TEST_ONLY-extra.txt");
    fs::write(&extra, b"TEST_ONLY preserve").unwrap();
    assert_error(lease.validate(), Code::Conflict);
    assert!(lease.cancel_requested());
    assert!(f.host.has_project_work(&f.binding).unwrap());
    drop(lease);
    assert_eq!(fs::read(extra).unwrap(), b"TEST_ONLY preserve");
}

#[test]
fn actual_hardlink_attempt_during_each_live_member_lease_is_blocked_or_invalidates() {
    for role in ROLES {
        let f = Fixture::new();
        let mut lease = f.lease();
        let member = crate::fresh_project::member(&f.root, role.relative_name());
        let alias = f.dir.join("TEST_ONLY-live-hardlink");
        let permitted = fs::hard_link(&member, &alias).is_ok();
        if permitted {
            assert_error(lease.validate(), Code::Conflict);
            assert!(lease.cancel_requested());
            assert!(f.host.has_project_work(&f.binding).unwrap());
            assert_error(f.save(SOURCE), Code::Busy);
            assert_eq!(fs::read(&alias).unwrap(), lease.bytes(role));
        } else {
            lease.validate().unwrap();
        }
        drop(lease);
        assert!(!f.host.has_project_work(&f.binding).unwrap());
        assert!(member.is_file());
        if permitted {
            assert!(alias.is_file());
        } // Drop never cleans aliases.
    }
}

#[test]
fn concurrent_save_as_with_real_native_target_preserves_target_until_lease_drop() {
    let f = Fixture::new();
    let target = {
        let mut state = f.host.state.lock().unwrap();
        let caller = state.registrations[f.binding.slot].caller.clone();
        let id = state
            .registry
            .reserve(&caller, Operation::ChooseTarget(f.doc.clone()))
            .unwrap();
        let Start::Work(job) = state
            .registry
            .choose_target(
                &caller,
                TargetRequest {
                    request_id: id,
                    document_id: f.doc.clone(),
                },
            )
            .unwrap()
        else {
            panic!()
        };
        drop(state);
        let completion = job.run(&mut TestOnlyPicker(Some(
            f.dir.join("TEST_ONLY-concurrent-save-as.cpp"),
        )));
        let mut state = f.host.state.lock().unwrap();
        let Status::Complete {
            result: Outcome::Selected {
                target_grant_id, ..
            },
            ..
        } = state.registry.complete(completion).unwrap()
        else {
            panic!()
        };
        target_grant_id
    };
    let lease = f.lease();
    let host = f.host.clone();
    let binding = f.binding.clone();
    let doc = f.doc.clone();
    let captured = target.clone();
    std::thread::spawn(move || {
        let mut state = host.state.lock().unwrap();
        let caller = state.registrations[binding.slot].caller.clone();
        assert_error(
            state
                .registry
                .reserve_save_as(&caller, &doc, &captured, 1, SOURCE.to_vec()),
            Code::Busy,
        );
        assert!(state.registry.targets.contains_key(&captured));
    })
    .join()
    .unwrap();
    assert!(f.host.has_project_work(&f.binding).unwrap());
    drop(lease);
    let mut state = f.host.state.lock().unwrap();
    let caller = state.registrations[f.binding.slot].caller.clone();
    state
        .registry
        .reserve_save_as(&caller, &f.doc, &target, 1, SOURCE.to_vec())
        .unwrap();
    assert!(!state.registry.targets.contains_key(&target));
}

#[test]
fn revoke_during_root_picker_is_intent_until_reopen_drains_without_late_adoption() {
    let f = Fixture::new();
    let binding = live(&f.host);
    let work = f.host.prepare_project_reopen(&binding).unwrap();
    struct RevokingPicker<'a> {
        fixture: &'a Fixture,
        binding: Binding,
    }
    impl ProjectRootPicker for RevokingPicker<'_> {
        fn select_root(&mut self) -> Result<Option<PathBuf>, Code> {
            self.fixture.host.revoke_native_view(&self.binding)?;
            assert!(self.fixture.host.has_project_work(&self.binding)?);
            Ok(Some(self.fixture.root.clone()))
        }
    }
    assert!(work
        .run(&mut RevokingPicker {
            fixture: &f,
            binding: binding.clone()
        })
        .unwrap()
        .is_none());
    assert!(!f.host.has_project_work(&binding).unwrap());
    assert_eq!(f.host.state.lock().unwrap().registry.documents.len(), 1);
    assert_eq!(fs::read(f.root.join("app/src/main.cpp")).unwrap(), SOURCE);
}

#[test]
fn exact_source_and_companion_bounds_survive_native_reopen_and_snapshot() {
    let f = Fixture::new();
    let root = f.root.clone();
    let storage = f.storage.clone();
    drop(f);
    let expected_source = vec![b'x'; MAX_SOURCE_BYTES];
    fs::write(
        crate::fresh_project::member(&root, "app/src/main.cpp"),
        &expected_source,
    )
    .unwrap();
    for role in &ROLES[1..] {
        fs::write(
            crate::fresh_project::member(&root, role.relative_name()),
            vec![b'x'; 65_536],
        )
        .unwrap();
    }
    let host = NativeHost::open_local(&storage).unwrap();
    let binding = live(&host);
    let candidate = host
        .prepare_project_reopen(&binding)
        .unwrap()
        .run(&mut TestOnlyPicker(Some(root)))
        .unwrap()
        .unwrap();
    let lease = host
        .prepare_saved_app_snapshot(
            &binding,
            &candidate.document_id,
            &candidate.binding.unwrap().version,
            0,
        )
        .unwrap()
        .run()
        .unwrap();
    assert_eq!(lease.bytes(SavedAppRole::Source), expected_source);
    for role in &ROLES[1..] {
        assert_eq!(lease.bytes(*role).len(), 65_536);
    }
}

#[test]
fn rejected_bind_draft_does_not_leave_hidden_work_after_snapshot_drop() {
    for captured in [false, true] {
        let f = Fixture::new();
        let mut work = Some(f.work().unwrap());
        let lease = if captured {
            Some(work.take().unwrap().run().unwrap())
        } else {
            None
        };
        let before = {
            let state = f.host.state.lock().unwrap();
            (
                state.registry.operations.len(),
                state.registry.documents.len(),
            )
        };
        assert_error(
            f.call(
                900,
                json!({"kind":"bindDraft","revision":2,
                "sourceBase64":STANDARD.encode(SOURCE)}),
            ),
            Code::Busy,
        );
        {
            let state = f.host.state.lock().unwrap();
            assert_eq!(
                (
                    state.registry.operations.len(),
                    state.registry.documents.len()
                ),
                before
            );
        }
        drop(lease);
        drop(work);
        assert!(!f.host.has_project_work(&f.binding).unwrap());
        let mut next = f.lease();
        next.validate().unwrap();
        drop(next);
        drop(f.host.prepare_project_reopen(&f.binding).unwrap());
        assert!(!f.host.has_project_work(&f.binding).unwrap());
    }
}
