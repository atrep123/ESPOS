//! TEST_ONLY fixtures; real NativeHost creation/adoption and Windows NTFS IO.
use super::*;
use serde_json::json;

const SOURCE: &[u8] = b"// TEST_ONLY stage\r\nint value = 1;\r\n";
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
struct TestOnlyPicker(PathBuf);
impl ProjectParentPicker for TestOnlyPicker {
    fn select_parent(&mut self) -> Result<Option<PathBuf>, Code> {
        Ok(Some(self.0.clone()))
    }
}
impl ProjectRootPicker for TestOnlyPicker {
    fn select_root(&mut self) -> Result<Option<PathBuf>, Code> {
        Ok(Some(self.0.clone()))
    }
}
struct Fixture {
    dir: PathBuf,
    storage: PathBuf,
    root: PathBuf,
    host: NativeHost,
    binding: Binding,
    doc: DocumentId,
    version: Version,
}
impl Fixture {
    fn new() -> Self {
        Self::with_source(SOURCE.to_vec())
    }
    fn with_source(source: Vec<u8>) -> Self {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("test-tmp")
            .join(format!("TEST_ONLY-stage-{}", owned_job_nonce().unwrap()));
        fs::create_dir_all(&dir).unwrap();
        let storage = dir.join("storage");
        let parent = dir.join("parent");
        fs::create_dir(&storage).unwrap();
        fs::create_dir(&parent).unwrap();
        let host = NativeHost::open_local(&storage).unwrap();
        let binding = live(&host);
        let draft = {
            let mut state = host.state.lock().unwrap();
            let caller = state.registrations[binding.slot].caller.clone();
            state
                .registry
                .bind_captured_draft(&caller, 1, source)
                .unwrap()
        };
        let ProjectStatus::Created { document, .. } = host
            .prepare_fresh_project(
                &binding,
                &draft.document_id,
                1,
                "test_app".into(),
                companions(),
            )
            .unwrap()
            .run(&mut TestOnlyPicker(parent.clone()))
            .unwrap()
        else {
            panic!("TEST_ONLY adoption")
        };
        Self {
            dir,
            storage,
            root: parent.join("test_app"),
            host,
            binding,
            doc: draft.document_id,
            version: document.binding.unwrap().version,
        }
    }
    fn lease(&self) -> SavedAppLease {
        self.host
            .prepare_saved_app_snapshot(&self.binding, &self.doc, &self.version, 1)
            .unwrap()
            .run()
            .unwrap()
    }
    fn stage(&self) -> Result<StagedAppInputs, Code> {
        self.host
            .stage_saved_app_inputs(&self.binding, self.lease())
    }
    fn stages(&self) -> Vec<PathBuf> {
        let storage = self.storage.join(STORAGE_NAME);
        if !storage.is_dir() {
            return Vec::new();
        }
        fs::read_dir(storage)
            .unwrap()
            .map(|e| e.unwrap().path())
            .filter(|p| stage_name(p.file_name().unwrap().to_str().unwrap()))
            .collect()
    }
    fn busy(&self) -> bool {
        self.host.has_project_work(&self.binding).unwrap()
    }
}
fn error<T>(result: Result<T, Code>, code: Code) {
    match result {
        Err(actual) => assert_eq!(actual, code),
        Ok(_) => panic!("expected {code:?}"),
    }
}
struct Hook;
impl Hook {
    fn set(hook: impl FnMut(usize, &SavedAppLease, &Path) -> Result<(), Code> + 'static) -> Self {
        TEST_STEP.with(|h| *h.borrow_mut() = Some(Box::new(hook)));
        Self
    }
}
impl Drop for Hook {
    fn drop(&mut self) {
        TEST_STEP.with(|h| *h.borrow_mut() = None);
    }
}

#[test]
fn actual_native_stage_exact_roles_generated_path_locks_and_drop_retention() {
    let f = Fixture::new();
    let source_lease = f.lease();
    let expected: Vec<_> = ROLES
        .iter()
        .map(|r| source_lease.bytes(*r).to_vec())
        .collect();
    let mut stage = f
        .host
        .stage_saved_app_inputs(&f.binding, source_lease)
        .unwrap();
    let path = stage.native_stage_path().unwrap().to_path_buf();
    assert_eq!(path.parent().unwrap(), f.storage.join(STORAGE_NAME));
    assert!(!path.starts_with(&f.root));
    crate::fresh_project::exact_layout(&path).unwrap();
    assert!(f.busy());
    for (index, role) in ROLES.iter().enumerate() {
        let staged = member(&path, role.relative_name());
        assert_eq!(fs::read(&staged).unwrap(), expected[index]);
        for p in [&staged, &member(&f.root, role.relative_name())] {
            assert!(fs::write(p, b"TEST_ONLY forbidden").is_err());
            assert!(fs::rename(p, p.with_extension("moved")).is_err());
            assert!(fs::remove_file(p).is_err());
        }
    }
    assert!(fs::rename(&path, path.with_extension("moved")).is_err());
    stage.validate().unwrap();
    error(
        f.host
            .prepare_saved_app_snapshot(&f.binding, &f.doc, &f.version, 1),
        Code::Busy,
    );
    {
        let mut state = f.host.state.lock().unwrap();
        let caller = state.registrations[f.binding.slot].caller.clone();
        error(
            state
                .registry
                .reserve_save(&caller, &f.doc, &f.version, SOURCE.to_vec()),
            Code::Busy,
        );
        error(
            state.registry.release(
                &caller,
                Release::Document {
                    document_id: f.doc.clone(),
                },
            ),
            Code::Busy,
        );
    }
    drop(stage);
    assert!(!f.busy());
    for (index, role) in ROLES.iter().enumerate() {
        let staged = member(&path, role.relative_name());
        assert_eq!(fs::read(&staged).unwrap(), expected[index]);
        fs::write(&staged, &expected[index]).unwrap();
        OpenOptions::new()
            .write(true)
            .open(member(&f.root, role.relative_name()))
            .unwrap();
    }
    let next = f.stage().unwrap();
    assert_ne!(next.root, path);
    assert_eq!(f.stages().len(), 2);
}

#[test]
fn dirty_stale_foreign_owner_and_cross_host_never_create_stage() {
    for mode in 0..4 {
        let f = Fixture::new();
        let mut lease = f.lease();
        match mode {
            0 => f
                .host
                .capture_saved_app_draft(
                    &f.binding,
                    &f.doc,
                    &f.version,
                    2,
                    b"// TEST_ONLY dirty".to_vec(),
                )
                .unwrap(),
            1 => {
                let mut state = f.host.state.lock().unwrap();
                state.registry.documents.get_mut(&f.doc).unwrap().version =
                    Some(Version::mint().unwrap());
            }
            2 => {
                let foreign = live(&f.host);
                error(f.host.stage_saved_app_inputs(&foreign, lease), Code::Denied);
                assert!(f.stages().is_empty());
                continue;
            }
            _ => {
                let other = Fixture::new();
                error(
                    other.host.stage_saved_app_inputs(&other.binding, lease),
                    Code::Denied,
                );
                assert!(f.stages().is_empty());
                assert!(other.stages().is_empty());
                assert!(!f.busy());
                continue;
            }
        }
        error(
            lease.validate(),
            if mode == 0 {
                Code::Revoked
            } else {
                Code::Conflict
            },
        );
        error(
            f.host.stage_saved_app_inputs(&f.binding, lease),
            if mode == 0 {
                Code::Revoked
            } else {
                Code::Conflict
            },
        );
        assert!(f.stages().is_empty());
        assert!(!f.storage.join(STORAGE_NAME).exists());
        assert!(!f.busy());
    }
}

#[test]
fn revoke_navigation_and_dirty_stage_keep_same_busy_and_both_locks_until_drop() {
    for mode in 0..3 {
        let f = Fixture::new();
        let mut stage = f.stage().unwrap();
        let path = stage.root.clone();
        match mode {
            0 => f.host.revoke_native_view(&f.binding).unwrap(),
            1 => error(f.host.native_document_started(&f.binding), Code::Revoked),
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
        assert!(stage.cancel_requested());
        error(stage.native_stage_path(), Code::Revoked);
        assert!(f.busy());
        assert!(fs::write(member(&path, ROLES[0].relative_name()), b"blocked").is_err());
        assert!(fs::write(member(&f.root, ROLES[0].relative_name()), b"blocked").is_err());
        assert_eq!(f.host.state.lock().unwrap().registry.documents.len(), 1);
        drop(stage);
        assert!(!f.busy());
        assert_eq!(
            fs::read(member(&path, ROLES[0].relative_name())).unwrap(),
            SOURCE
        );
        fs::write(member(&path, ROLES[0].relative_name()), SOURCE).unwrap();
        if mode < 2 {
            assert!(f.host.state.lock().unwrap().registry.documents.is_empty());
        }
    }
}

#[test]
fn cancel_at_each_creation_boundary_never_returns_inputs_retains_partial_and_drains() {
    for boundary in 0..12 {
        let f = Fixture::new();
        let host = f.host.clone();
        let binding = f.binding.clone();
        let _hook = Hook::set(move |step, lease, _| {
            if step == boundary {
                host.revoke_native_view(&binding).unwrap();
                assert!(host.has_project_work(&binding).unwrap());
                assert!(lease.cancel_requested());
            }
            Ok(())
        });
        error(f.stage(), Code::Revoked);
        assert!(!f.busy());
        assert_eq!(
            fs::read(member(&f.root, ROLES[0].relative_name())).unwrap(),
            SOURCE
        );
        if boundary < 2 {
            assert!(f.stages().is_empty());
        } else {
            let paths = f.stages();
            assert_eq!(paths.len(), 1);
            let written = ROLES
                .iter()
                .filter(|r| member(&paths[0], r.relative_name()).exists())
                .count();
            assert_eq!(
                written,
                if boundary == 2 {
                    0
                } else {
                    ((boundary - 3) / 2 + 1).min(4)
                }
            );
        }
    }
}

#[test]
fn actual_source_and_stage_extra_namespace_members_fail_closed_and_preserve() {
    for side in 0..3 {
        let f = Fixture::new();
        let mut stage = f.stage().unwrap();
        let extra = match side {
            0 => f.root.join("TEST_ONLY-extra"),
            1 => stage.root.join("app/src/TEST_ONLY-extra"),
            _ => f.storage.join(STORAGE_NAME).join("TEST_ONLY-unrelated"),
        };
        fs::write(&extra, b"TEST_ONLY retain").unwrap();
        error(stage.validate(), Code::Conflict);
        assert!(stage.cancel_requested());
        assert!(f.busy());
        drop(stage);
        assert_eq!(fs::read(extra).unwrap(), b"TEST_ONLY retain");
        assert!(!f.busy());
    }
}

#[test]
fn actual_stage_and_source_hardlink_ads_attempts_block_or_invalidate_for_all_roles() {
    for side in 0..2 {
        for ads in [false, true] {
            for role in ROLES {
                let f = Fixture::new();
                let mut stage = f.stage().unwrap();
                let root = if side == 0 { &f.root } else { &stage.root };
                let path = member(root, role.relative_name());
                let alias = f.dir.join("TEST_ONLY-alias");
                let permitted = if ads {
                    fs::write(format!("{}:TEST_ONLY", path.display()), b"retain").is_ok()
                } else {
                    fs::hard_link(&path, &alias).is_ok()
                };
                if permitted {
                    assert!(stage.validate().is_err());
                    assert!(stage.cancel_requested());
                    assert!(f.busy());
                } else {
                    stage.validate().unwrap();
                }
                drop(stage);
                assert!(path.is_file());
                if permitted && !ads {
                    assert!(alias.is_file());
                }
            }
        }
    }
}

#[test]
fn actual_stage_and_source_directory_changes_block_or_invalidate() {
    for side in 0..2 {
        for relative in DIRECTORIES {
            let f = Fixture::new();
            let mut stage = f.stage().unwrap();
            let path = member(if side == 0 { &f.root } else { &stage.root }, relative);
            let moved = f.dir.join("TEST_ONLY-directory-moved");
            if fs::rename(&path, &moved).is_ok() {
                fs::create_dir(&path).unwrap();
                assert!(stage.validate().is_err());
                assert!(stage.cancel_requested());
                assert!(moved.is_dir());
            } else {
                stage.validate().unwrap();
            }
            assert!(f.busy());
            drop(stage);
            assert!(path.is_dir());
        }
    }
}

#[test]
fn directory_ads_in_staged_namespace_fail_closed_if_ntfs_permits_mutation() {
    for relative in DIRECTORIES {
        let f = Fixture::new();
        let mut stage = f.stage().unwrap();
        let path = if relative.is_empty() {
            stage.root.clone()
        } else {
            member(&stage.root, relative)
        };
        let stream = format!("{}:TEST_ONLY", path.display());
        fs::write(&stream, b"TEST_ONLY retain stream").unwrap();
        assert!(matches!(
            stage.validate(),
            Err(Code::Conflict | Code::UnsupportedPath)
        ));
        assert!(stage.cancel_requested());
        assert!(f.busy());
        drop(stage);
        assert_eq!(fs::read(stream).unwrap(), b"TEST_ONLY retain stream");
    }
}

#[test]
fn changed_replaced_hardlinked_or_ads_member_between_create_and_read_never_succeeds() {
    for mode in 0..4 {
        let f = Fixture::new();
        let alias = f.dir.join("TEST_ONLY-created-alias");
        let _hook = Hook::set(move |step, _, root| {
            if step == 3 {
                let path = member(root, ROLES[0].relative_name());
                match mode {
                    0 => {
                        fs::write(&path, b"TEST_ONLY changed").unwrap();
                    }
                    1 => {
                        // Metadata pin closes the CREATE_NEW/read-lock gap.
                        assert!(fs::rename(&path, &alias).is_err());
                        return Err(Code::IOFailure);
                    }
                    2 => {
                        fs::hard_link(&path, &alias).unwrap();
                    }
                    _ => {
                        fs::write(format!("{}:TEST_ONLY", path.display()), b"stream").unwrap();
                    }
                }
            }
            Ok(())
        });
        assert!(f.stage().is_err());
        assert!(!f.busy());
        let paths = f.stages();
        assert_eq!(paths.len(), 1);
        assert!(member(&paths[0], ROLES[0].relative_name()).is_file());
        assert!(!member(&paths[0], ROLES[1].relative_name()).exists());
    }
}

#[test]
fn source_metadata_or_namespace_change_during_actual_staging_never_returns_stage() {
    for metadata in [false, true] {
        let f = Fixture::new();
        let source_root = f.root.clone();
        let alias = f.dir.join("TEST_ONLY-source-alias");
        let _hook = Hook::set(move |step, _, _| {
            if step == 3 {
                if metadata {
                    fs::hard_link(member(&source_root, ROLES[0].relative_name()), &alias).unwrap();
                } else {
                    fs::write(source_root.join("TEST_ONLY-extra"), b"retain").unwrap();
                }
            }
            Ok(())
        });
        error(f.stage(), Code::Conflict);
        assert_eq!(f.stages().len(), 1);
        assert!(!f.busy());
    }
}

#[test]
fn member_create_new_collision_keeps_unrelated_bytes_and_partial_slot() {
    let f = Fixture::new();
    let _hook = Hook::set(|step, _, root| {
        if step == 4 {
            fs::write(
                member(root, ROLES[2].relative_name()),
                b"TEST_ONLY unrelated",
            )
            .unwrap();
        }
        Ok(())
    });
    error(f.stage(), Code::Conflict);
    let paths = f.stages();
    assert_eq!(paths.len(), 1);
    assert_eq!(
        fs::read(member(&paths[0], ROLES[2].relative_name())).unwrap(),
        b"TEST_ONLY unrelated"
    );
    assert_eq!(
        fs::read(member(&paths[0], ROLES[0].relative_name())).unwrap(),
        SOURCE
    );
    assert!(!member(&paths[0], ROLES[3].relative_name()).exists());
    assert!(!f.busy());
}

#[test]
fn retained_stage_budget_includes_partial_inputs_and_never_overwrites_or_cleans() {
    let f = Fixture::new();
    {
        let _hook = Hook::set(|step, _, _| {
            if step == 2 {
                Err(Code::IOFailure)
            } else {
                Ok(())
            }
        });
        error(f.stage(), Code::IOFailure);
    }
    let partial = f.stages().pop().unwrap();
    for _ in 1..MAX_STAGES {
        drop(f.stage().unwrap());
    }
    let mut before: Vec<_> = f.stages();
    before.sort();
    assert_eq!(before.len(), MAX_STAGES);
    error(f.stage(), Code::TooLarge);
    let mut after = f.stages();
    after.sort();
    assert_eq!(before, after);
    assert_eq!(fs::read_dir(partial).unwrap().count(), 0);
    assert!(!f.busy());
    for p in before
        .iter()
        .filter(|p| member(p, ROLES[0].relative_name()).exists())
    {
        assert_eq!(
            fs::read(member(p, ROLES[0].relative_name())).unwrap(),
            SOURCE
        );
    }
}

#[test]
fn malformed_or_preexisting_userdata_namespace_is_never_adopted_repaired_or_deleted() {
    for mode in 0..5 {
        let f = Fixture::new();
        let storage = f.storage.join(STORAGE_NAME);
        if mode == 4 {
            fs::write(&storage, b"TEST_ONLY unrelated file").unwrap();
        } else {
            fs::create_dir(&storage).unwrap();
            fs::write(storage.join("budget.lock"), b"").unwrap();
            if mode > 0 {
                fs::write(
                    storage.join("owner.bin"),
                    if mode == 1 { b"bad" } else { OWNER },
                )
                .unwrap();
            }
            if mode == 2 {
                fs::write(storage.join("TEST_ONLY-user-history"), b"retain").unwrap();
            }
            if mode == 3 {
                fs::write(storage.join("budget.lock:TEST_ONLY"), b"retain").unwrap();
            }
        }
        assert!(f.stage().is_err());
        assert!(storage.exists());
        assert!(f.stages().is_empty());
        if mode == 2 {
            assert_eq!(
                fs::read(storage.join("TEST_ONLY-user-history")).unwrap(),
                b"retain"
            );
        }
        if mode == 4 {
            assert_eq!(fs::read(&storage).unwrap(), b"TEST_ONLY unrelated file");
        }
    }
}

#[test]
fn actual_junction_stage_storage_fails_closed_and_retains_foreign_tree() {
    let f = Fixture::new();
    let target = f.dir.join("TEST_ONLY-foreign");
    fs::create_dir(&target).unwrap();
    fs::write(target.join("keep"), b"TEST_ONLY retain").unwrap();
    let output = std::process::Command::new("cmd.exe")
        .args(["/c", "mklink", "/J"])
        .arg(f.storage.join(STORAGE_NAME))
        .arg(&target)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    error(f.stage(), Code::UnsupportedPath);
    assert_eq!(fs::read(target.join("keep")).unwrap(), b"TEST_ONLY retain");
}

#[test]
fn staged_inputs_and_partial_stages_do_not_enter_recovery_catalogues_on_host_reopen() {
    let f = Fixture::new();
    drop(f.stage().unwrap());
    {
        let _hook = Hook::set(|step, _, _| {
            if step == 2 {
                Err(Code::IOFailure)
            } else {
                Ok(())
            }
        });
        error(f.stage(), Code::IOFailure);
    }
    let storage = f.storage.clone();
    let source = f.root.clone();
    let paths = f.stages();
    let journal_count = f.host.project_catalogue.len();
    drop(f);
    let host = NativeHost::open_local(&storage).unwrap();
    // Only the original fresh-project journal is catalogued, never stages.
    assert_eq!(host.project_catalogue.len(), journal_count + 1);
    assert!(host
        .project_catalogue
        .values()
        .all(|p| p.parent().unwrap() == storage.join("cpp-fresh-project-v1")));
    let binding = live(&host);
    let candidate = host
        .prepare_project_reopen(&binding)
        .unwrap()
        .run(&mut TestOnlyPicker(source))
        .unwrap()
        .unwrap();
    let version = candidate.binding.unwrap().version;
    let lease = host
        .prepare_saved_app_snapshot(&binding, &candidate.document_id, &version, 0)
        .unwrap()
        .run()
        .unwrap();
    let stage = host.stage_saved_app_inputs(&binding, lease).unwrap();
    assert!(!paths.contains(&stage.root));
    assert!(paths.iter().all(|p| p.is_dir()));
}

#[test]
fn existing_caps_exact_limit_is_copied_into_four_actual_stage_files() {
    let f = Fixture::new();
    let root = f.root.clone();
    let storage = f.storage.clone();
    drop(f);
    for (index, role) in ROLES.iter().enumerate() {
        fs::write(
            member(&root, role.relative_name()),
            vec![b'x'; if index == 0 { MAX_SOURCE_BYTES } else { 65_536 }],
        )
        .unwrap();
    }
    let host = NativeHost::open_local(&storage).unwrap();
    let binding = live(&host);
    let candidate = host
        .prepare_project_reopen(&binding)
        .unwrap()
        .run(&mut TestOnlyPicker(root))
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
    let mut stage = host.stage_saved_app_inputs(&binding, lease).unwrap();
    let path = stage.native_stage_path().unwrap();
    for (index, role) in ROLES.iter().enumerate() {
        let bytes = fs::read(member(path, role.relative_name())).unwrap();
        assert_eq!(
            bytes.len(),
            if index == 0 { MAX_SOURCE_BYTES } else { 65_536 }
        );
        assert!(bytes.iter().all(|b| *b == b'x'));
    }
}

#[test]
fn renderer_stage_commands_cannot_create_native_stage_or_obtain_paths() {
    let f = Fixture::new();
    for kind in [
        "stageSavedAppInputs",
        "nativeStagePath",
        "validateStagedAppInputs",
    ] {
        error(
            f.host.dispatch(
                &f.binding,
                &serde_json::to_vec(&json!({
                    "callId":"call_00000000000000000000000000000001",
                    "command":{"kind":kind,"root":f.root,"documentId":f.doc}
                }))
                .unwrap(),
            ),
            Code::InvalidInput,
        );
    }
    assert!(!f.storage.join(STORAGE_NAME).exists());
}

#[test]
fn cancel_during_member_write_retains_bounded_prefix_without_stage_success() {
    let f = Fixture::with_source(vec![b'x'; MAX_SOURCE_BYTES]);
    let host = f.host.clone();
    let binding = f.binding.clone();
    let _hook = Hook::set(move |step, _, path| {
        if step == 12 && path.file_name().is_some_and(|n| n == "main.cpp") {
            host.revoke_native_view(&binding).unwrap();
            assert!(host.has_project_work(&binding).unwrap());
        }
        Ok(())
    });
    error(f.stage(), Code::Revoked);
    assert!(!f.busy());
    let paths = f.stages();
    assert_eq!(paths.len(), 1);
    assert_eq!(
        fs::read(member(&paths[0], ROLES[0].relative_name())).unwrap(),
        vec![b'x'; 8192]
    );
    assert!(!member(&paths[0], ROLES[1].relative_name()).exists());
    assert_eq!(
        fs::read(member(&f.root, ROLES[0].relative_name()))
            .unwrap()
            .len(),
        MAX_SOURCE_BYTES
    );
}

#[test]
fn controls_are_read_pinned_and_budget_mutations_are_rejected_before_use() {
    for mode in 0..3 {
        let f = Fixture::new();
        let mut stage = f.stage().unwrap();
        let budget = f.storage.join(STORAGE_NAME).join("budget.lock");
        assert!(fs::remove_file(&budget).is_err());
        assert!(fs::rename(&budget, f.dir.join("TEST_ONLY-budget-renamed")).is_err());
        match mode {
            0 => fs::write(&budget, b"TEST_ONLY unrelated").unwrap(),
            1 => fs::write(format!("{}:TEST_ONLY", budget.display()), b"stream").unwrap(),
            _ => fs::hard_link(&budget, f.dir.join("TEST_ONLY-budget-link")).unwrap(),
        }
        assert!(stage.native_stage_path().is_err());
        assert!(stage.cancel_requested());
        assert!(f.busy());
        drop(stage);
        assert!(budget.is_file());
        assert!(!f.busy());
    }
}

#[test]
fn concurrent_native_stage_admission_serializes_capacity_without_clobbering() {
    let f = Fixture::new();
    drop(f.stage().unwrap());
    let other_binding = live(&f.host);
    let candidate = f
        .host
        .prepare_project_reopen(&other_binding)
        .unwrap()
        .run(&mut TestOnlyPicker(f.root.clone()))
        .unwrap()
        .unwrap();
    let other_version = candidate.binding.unwrap().version;
    let mut other_lease = Some(
        f.host
            .prepare_saved_app_snapshot(&other_binding, &candidate.document_id, &other_version, 0)
            .unwrap()
            .run()
            .unwrap(),
    );
    let host = f.host.clone();
    let observed_binding = other_binding.clone();
    let hook = Hook::set(move |step, _, _| {
        if step == 2 {
            let host = host.clone();
            let binding = observed_binding.clone();
            let lease = other_lease.take().unwrap();
            // The second OS thread runs without a test hook and contends on
            // the real SHARE_READ budget writer while this creation is held.
            let result = std::thread::spawn(move || host.stage_saved_app_inputs(&binding, lease))
                .join()
                .unwrap();
            error(result, Code::Busy);
        }
        Ok(())
    });
    let primary = f.stage().unwrap();
    drop(hook);
    assert!(f.busy());
    assert!(!f.host.has_project_work(&other_binding).unwrap());
    let other_lease = f
        .host
        .prepare_saved_app_snapshot(&other_binding, &candidate.document_id, &other_version, 0)
        .unwrap()
        .run()
        .unwrap();
    // A completed stage's read pin permits a separate caller's new admission.
    let mut other = f
        .host
        .stage_saved_app_inputs(&other_binding, other_lease)
        .unwrap();
    other.validate().unwrap();
    assert_ne!(primary.root, other.root);
    assert_eq!(f.stages().len(), 3);
    assert_eq!(
        fs::read(member(&primary.root, ROLES[0].relative_name())).unwrap(),
        SOURCE
    );
}

#[test]
fn cancel_during_shared_bootstrap_does_not_poison_next_authorized_stage() {
    for boundary in [13, 14] {
        let f = Fixture::new();
        let host = f.host.clone();
        let binding = f.binding.clone();
        let hook = Hook::set(move |step, _, _| {
            if step == boundary {
                host.revoke_native_view(&binding).unwrap();
            }
            Ok(())
        });
        error(f.stage(), Code::Revoked);
        drop(hook);
        assert!(!f.busy());
        assert!(f.stages().is_empty());
        // A different genuinely admitted caller reopens the same unchanged app;
        // no old grant, inferred source ancestor or journal repairs the storage.
        let binding = live(&f.host);
        let document = f
            .host
            .prepare_project_reopen(&binding)
            .unwrap()
            .run(&mut TestOnlyPicker(f.root.clone()))
            .unwrap()
            .unwrap();
        let lease = f
            .host
            .prepare_saved_app_snapshot(
                &binding,
                &document.document_id,
                &document.binding.unwrap().version,
                0,
            )
            .unwrap()
            .run()
            .unwrap();
        let mut next = f
            .host
            .stage_saved_app_inputs(&binding, lease)
            .expect("cancelled bootstrap must not disable future native staging");
        next.validate().unwrap();
        assert_eq!(
            fs::read(member(
                next.native_stage_path().unwrap(),
                ROLES[0].relative_name()
            ))
            .unwrap(),
            SOURCE
        );
        drop(next);
        assert!(!f.host.has_project_work(&binding).unwrap());
        assert_eq!(
            fs::read(f.storage.join(STORAGE_NAME).join("owner.bin")).unwrap(),
            OWNER
        );
        assert_eq!(
            fs::metadata(f.storage.join(STORAGE_NAME).join("budget.lock"))
                .unwrap()
                .len(),
            0
        );
    }
}
