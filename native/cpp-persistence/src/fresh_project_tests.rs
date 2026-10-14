//! Actual inert Windows filesystem fixtures. Not native GUI/IPC/SDK proof.
//! All artifacts are kept; there is no rollback or test-directory deletion.
use super::*;
use crate::{Registry, RequestId};

struct Fixture {
    root: PathBuf,
    parent: PathBuf,
    journal: PathBuf,
}
impl Fixture {
    fn new() -> Self {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("test-tmp")
            .join(format!(
                "fresh-project-{}",
                windows_read::random_hex().unwrap()
            ));
        fs::create_dir_all(&root).unwrap();
        let parent = root.join("selected-parent");
        let journal = root.join("native-storage");
        fs::create_dir(&parent).unwrap();
        fs::create_dir(&journal).unwrap();
        Self {
            root,
            parent,
            journal,
        }
    }
    fn plan(&self) -> Plan {
        let source =
            b"// TEST_ONLY inert UTF-8 C++; no compiler or SDK\r\nint count = 0;\r\n".to_vec();
        let mut registry = Registry::new().unwrap();
        let caller = registry.attach_caller().unwrap();
        let capture = registry
            .bind_captured_draft(&caller, 1, source.clone())
            .unwrap();
        let scope = Scope {
            schema: 1,
            operation: RequestId::mint().unwrap(),
            session: caller.session,
            incarnation: caller.incarnation,
            document: capture.document_id,
            version: None,
            source_bytes: source.len(),
            source_hash: windows_write::digest(&source),
        };
        let files = Files::new([
            source,
            b"{\"TEST_ONLY\":true}\n".to_vec(),
            b"# TEST_ONLY inert CMake, never executed\n".to_vec(),
            b"# TEST_ONLY no live UI, native caller or hardware proof\n".to_vec(),
        ])
        .unwrap();
        Plan::new(scope, &self.parent, "test_app", &self.journal, files).unwrap()
    }
}

#[test]
fn four_exact_new_files_and_durable_journal_are_observed() {
    let fixture = Fixture::new();
    let plan = fixture.plan();
    let journal = plan.journal.clone();
    let root = plan.root.clone();
    let expected = plan.files.bytes.clone();
    let result = plan.execute(&AtomicBool::new(false)).unwrap();
    assert_eq!(result.files.len(), 4);
    assert_eq!(result.source.bytes, expected[0]);
    for index in 0..4 {
        let actual = fs::read(member(&root, ROLES[index])).unwrap();
        assert_eq!(actual, expected[index]);
        assert_eq!(result.files[index].sha256, windows_write::digest(&actual));
        assert_eq!(
            fs::read(journal.join(format!("payload-{index}.bin"))).unwrap(),
            actual
        );
    }
    let verified: Vec<serde_json::Value> =
        serde_json::from_slice(&fs::read(journal.join("verified.json")).unwrap()).unwrap();
    assert_eq!(verified.len(), 4);
    assert!(journal.join("intent.json").is_file() && journal.join("may-write.json").is_file());
    assert!(fixture
        .root
        .starts_with(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("test-tmp")));
}

#[test]
fn existing_project_and_unknown_contents_are_never_overwritten() {
    let fixture = Fixture::new();
    let plan = fixture.plan();
    let root = plan.root.clone();
    fs::create_dir(&root).unwrap();
    fs::write(root.join("keep.txt"), b"TEST_ONLY existing bytes").unwrap();
    let result = plan.execute(&AtomicBool::new(false)).err().unwrap();
    assert_eq!(result.code, Code::Conflict);
    assert!(!result.may_have_written);
    assert_eq!(
        fs::read(root.join("keep.txt")).unwrap(),
        b"TEST_ONLY existing bytes"
    );
    assert_eq!(fs::read_dir(&fixture.journal).unwrap().count(), 0);
}

#[test]
fn cancellation_before_work_writes_nothing() {
    let fixture = Fixture::new();
    let plan = fixture.plan();
    let failure = plan.execute(&AtomicBool::new(true)).err().unwrap();
    assert_eq!(failure.code, Code::Revoked);
    assert!(!failure.may_have_written);
    assert_eq!(fs::read_dir(&fixture.parent).unwrap().count(), 0);
    assert_eq!(fs::read_dir(&fixture.journal).unwrap().count(), 0);
}

#[test]
fn complete_result_holds_read_and_namespace_locks_until_adoption() {
    let fixture = Fixture::new();
    let plan = fixture.plan();
    let root = plan.root.clone();
    let source = member(&root, ROLES[0]);
    let result = plan.execute(&AtomicBool::new(false)).unwrap();
    assert!(OpenOptions::new().write(true).open(&source).is_err());
    assert!(fs::rename(&root, fixture.parent.join("renamed_app")).is_err());
    assert_eq!(fs::read(&source).unwrap(), result.source.bytes);
    drop(result);
    // Ordinary explicit future saves are not permanently blocked by this group.
    assert!(OpenOptions::new().write(true).open(&source).is_ok());
}

#[test]
fn unexpected_members_block_completion_and_remain_preserved() {
    let fixture = Fixture::new();
    let plan = fixture.plan();
    let root = plan.root.clone();
    let journal = plan.journal.clone();
    FAIL_AFTER.with(|value| value.set(5));
    let failure = plan.execute(&AtomicBool::new(false)).err().unwrap();
    FAIL_AFTER.with(|value| value.set(0));
    assert_eq!(failure.code, Code::Conflict);
    assert!(failure.may_have_written);
    assert!(root.join("TEST_ONLY-extra.tmp").is_file());
    assert!(!journal.join("verified.json").exists());
}

#[test]
fn exhausted_native_journal_quota_stops_before_target_or_new_evidence() {
    let fixture = Fixture::new();
    let plan = fixture.plan();
    for index in 0..MAX_PROJECT_JOURNALS {
        fs::create_dir(fixture.journal.join(format!("TEST_ONLY-kept-{index}"))).unwrap();
    }
    let failure = plan.execute(&AtomicBool::new(false)).err().unwrap();
    assert_eq!(failure.code, Code::TooLarge);
    assert!(!failure.may_have_written);
    assert_eq!(fs::read_dir(&fixture.parent).unwrap().count(), 0);
    assert_eq!(
        fs::read_dir(&fixture.journal).unwrap().count(),
        MAX_PROJECT_JOURNALS
    );
}

#[test]
fn each_partial_file_failure_retains_payloads_and_never_claims_completion() {
    for step in 1..=4 {
        let fixture = Fixture::new();
        let plan = fixture.plan();
        let journal = plan.journal.clone();
        let root = plan.root.clone();
        FAIL_AFTER.with(|value| value.set(step));
        let failure = plan.execute(&AtomicBool::new(false)).err().unwrap();
        FAIL_AFTER.with(|value| value.set(0));
        assert_eq!(failure.code, Code::IOFailure);
        assert!(failure.may_have_written);
        assert!(journal.join("may-write.json").is_file());
        assert!(!journal.join("verified.json").exists());
        for index in 0..4 {
            assert_eq!(member(&root, ROLES[index]).exists(), index < step);
            assert!(journal.join(format!("payload-{index}.bin")).is_file());
        }
        // A new attempt at the existing target cannot replace/retry this group.
        let next = fixture.plan_if_absent();
        assert_eq!(next.err(), Some(Code::Conflict));
    }
}

impl Fixture {
    fn plan_if_absent(&self) -> Result<(), Code> {
        absent(&self.parent.join("test_app"))
    }
}

#[test]
fn input_size_utf8_and_nul_are_checked_before_any_filesystem_effect() {
    let good = || {
        [
            b"// TEST_ONLY source\n".to_vec(),
            b"{}\n".to_vec(),
            b"# cmake\n".to_vec(),
            b"# doc\n".to_vec(),
        ]
    };
    for index in 0..4 {
        for invalid in [vec![], vec![0], vec![0xff]] {
            let mut files = good();
            files[index] = invalid;
            assert!(matches!(Files::new(files), Err(Code::InvalidInput)));
        }
        let mut files = good();
        files[index] = vec![
            b'a';
            if index == 0 {
                MAX_SOURCE_BYTES + 1
            } else {
                COMPANION_CAP + 1
            }
        ];
        assert!(matches!(Files::new(files), Err(Code::TooLarge)));
    }
}

#[test]
fn unsupported_names_and_changed_source_scope_are_refused_without_writes() {
    let fixture = Fixture::new();
    for name in [
        "",
        "..",
        "../escape",
        "a\\b",
        "C:\\other",
        "stream:ads",
        "CON",
        "name.",
    ] {
        let plan = fixture.plan();
        assert!(Plan::new(
            plan.scope,
            &fixture.parent,
            name,
            &fixture.journal,
            plan.files
        )
        .is_err());
    }
    let mut plan = fixture.plan();
    plan.scope.source_hash = "0".repeat(64);
    assert!(matches!(
        Plan::new(
            plan.scope,
            &fixture.parent,
            "another_app",
            &fixture.journal,
            plan.files
        ),
        Err(Code::InvalidInput)
    ));
    assert_eq!(fs::read_dir(&fixture.parent).unwrap().count(), 0);
    assert_eq!(fs::read_dir(&fixture.journal).unwrap().count(), 0);
}
