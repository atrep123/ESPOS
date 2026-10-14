//! Four fixed files, CREATE_NEW only, one recoverable native operation.
//! This is the filesystem component, not installed IPC/picker/owner admission.
//! The host must supply its same-owner Scope and a real native-selected parent.
//! No overwrites, retries, rollback/deletion, arbitrary member paths or shell.
//! Local-cooperative persistence, not cross-file atomicity or power-loss proof.

use crate::{
    windows_read,
    windows_write::{self, Pins, Scope},
    Code, MAX_SOURCE_BYTES,
};
use serde::Serialize;
use std::{
    fs::{self, File, OpenOptions},
    io::Write,
    os::windows::fs::OpenOptionsExt,
    path::{Path, PathBuf},
    sync::atomic::{AtomicBool, Ordering},
};

const ROLES: [&str; 4] = [
    "app/src/main.cpp",
    "tabos-app.json",
    "CMakeLists.txt",
    "docs/UI_BACKEND_TRACEABILITY.md",
];
const COMPANION_CAP: usize = 65_536;
const REPARSE: u32 = 0x00200000;
const MAX_PROJECT_JOURNALS: usize = 128;

pub(crate) struct Files {
    bytes: [Vec<u8>; 4],
}
impl Files {
    pub(crate) fn new(bytes: [Vec<u8>; 4]) -> Result<Self, Code> {
        for (index, value) in bytes.iter().enumerate() {
            let cap = if index == 0 {
                MAX_SOURCE_BYTES
            } else {
                COMPANION_CAP
            };
            if value.len() > cap {
                return Err(Code::TooLarge);
            }
            if value.is_empty() || value.contains(&0) || std::str::from_utf8(value).is_err() {
                return Err(Code::InvalidInput);
            }
        }
        Ok(Self { bytes })
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub(crate) struct FileProof {
    pub(crate) role: &'static str,
    pub(crate) bytes: usize,
    pub(crate) sha256: String,
}

// Not Clone/Deserialize. Namespace handles and captured source scope remain owned
// until execution returns. A renderer's folder/string/receipt cannot mint it.
pub(crate) struct Plan {
    scope: Scope,
    root: PathBuf,
    journal: PathBuf,
    files: Files,
    parent: Pins,
    storage: Pins,
}

pub(crate) struct Created {
    pub(crate) source: windows_read::Selection,
    pub(crate) files: Vec<FileProof>,
    _directories: Vec<Pins>,
    _read_handles: Vec<File>,
}

#[derive(Debug)]
pub(crate) struct Failure {
    pub(crate) code: Code,
    // true also covers uncertain marker publication; never retry that operation.
    pub(crate) may_have_written: bool,
}

#[derive(Serialize)]
struct Intent<'a> {
    schema: &'static str,
    scope: &'a Scope,
    // Historical native origin only. It is NEVER a renewed picker/root grant.
    root: &'a Path,
    files: &'a [FileProof],
}

fn io<T>(result: std::io::Result<T>) -> Result<T, Code> {
    result.map_err(|error| match error.kind() {
        std::io::ErrorKind::AlreadyExists => Code::Conflict,
        std::io::ErrorKind::PermissionDenied => Code::Denied,
        _ => Code::IOFailure,
    })
}
fn cancelled(cancel: &AtomicBool) -> Result<(), Code> {
    if cancel.load(Ordering::Acquire) {
        Err(Code::Revoked)
    } else {
        Ok(())
    }
}
fn member(root: &Path, role: &str) -> PathBuf {
    role.split('/')
        .fold(root.to_path_buf(), |path, part| path.join(part))
}
fn absent(path: &Path) -> Result<(), Code> {
    match fs::symlink_metadata(path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Ok(_) => Err(Code::Conflict),
        Err(error) => io::<()>(Err(error)),
    }
}

fn exact_layout(root: &Path) -> Result<(), Code> {
    for (relative, expected) in [
        ("", &["app", "tabos-app.json", "CMakeLists.txt", "docs"][..]),
        ("app", &["src"][..]),
        ("app/src", &["main.cpp"][..]),
        ("docs", &["UI_BACKEND_TRACEABILITY.md"][..]),
    ] {
        let path = if relative.is_empty() {
            root.to_path_buf()
        } else {
            member(root, relative)
        };
        let mut names = Vec::new();
        for entry in io(fs::read_dir(path))? {
            let entry = io(entry)?;
            let name = entry
                .file_name()
                .into_string()
                .map_err(|_| Code::UnsupportedPath)?;
            if !expected.contains(&name.as_str()) || names.contains(&name) {
                return Err(Code::Conflict);
            }
            names.push(name);
        }
        if names.len() != expected.len() {
            return Err(Code::Conflict);
        }
    }
    Ok(())
}

fn journal_capacity(root: &Path) -> Result<(), Code> {
    // Each owned operation contains only bounded fixed files. Count only this
    // native-owned directory; never descend into historical/project paths.
    // No automatic cleanup, reuse or deletion when history fills.
    let mut count = 0;
    for entry in io(fs::read_dir(root))? {
        let _entry = io(entry)?;
        count += 1;
        if count >= MAX_PROJECT_JOURNALS {
            return Err(Code::TooLarge);
        }
    }
    Ok(())
}
fn exclusive_bytes(path: &Path, bytes: &[u8]) -> Result<(), Code> {
    let mut file = io(OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .share_mode(1)
        .custom_flags(REPARSE)
        .open(path))?;
    io(file.write_all(bytes))?;
    io(file.sync_all())?;
    if windows_write::fresh_project_snapshot(&mut file, bytes.len())? != bytes {
        return Err(Code::Conflict);
    }
    Ok(())
}

impl Plan {
    pub(crate) fn new(
        scope: Scope,
        selected_parent: &Path,
        directory_name: &str,
        journal_parent: &Path,
        files: Files,
    ) -> Result<Self, Code> {
        // A single native folder name; no path/alias/ADS/extra role authority.
        if directory_name.is_empty()
            || directory_name.len() > 64
            || !directory_name.bytes().all(|byte| {
                byte.is_ascii_lowercase() || byte.is_ascii_digit() || matches!(byte, b'_' | b'-')
            })
        {
            return Err(Code::InvalidInput);
        }
        let root = selected_parent.join(directory_name);
        windows_read::validate_path(&root)?;
        if scope.schema != 1
            || scope.source_bytes != files.bytes[0].len()
            || scope.source_hash != windows_write::digest(&files.bytes[0])
        {
            return Err(Code::InvalidInput);
        }
        for role in ROLES {
            windows_read::validate_path(&member(&root, role))?;
        }
        let parent = Pins::open(selected_parent)?;
        let storage = Pins::open(journal_parent)?;
        // Avoid journaling inside the project or creating a project around storage.
        if root.starts_with(journal_parent) || journal_parent.starts_with(&root) {
            return Err(Code::Denied);
        }
        absent(&root)?;
        let journal = journal_parent.join(format!("{}-project", scope.operation.as_str()));
        windows_read::validate_path(&journal.join("may-write.json"))?;
        absent(&journal)?;
        Ok(Self {
            scope,
            root,
            journal,
            files,
            parent,
            storage,
        })
    }

    pub(crate) fn execute(self, cancel: &AtomicBool) -> Result<Created, Failure> {
        let mut may_have_written = false;
        let result = self.execute_inner(cancel, &mut may_have_written);
        result.map_err(|code| Failure {
            code,
            may_have_written,
        })
    }

    fn execute_inner(self, cancel: &AtomicBool, may_write: &mut bool) -> Result<Created, Code> {
        cancelled(cancel)?;
        self.parent.check()?;
        self.storage.check()?;
        absent(&self.root)?;
        absent(&self.journal)?;
        journal_capacity(self.journal.parent().ok_or(Code::Unavailable)?)?;
        let proofs: Vec<_> = self
            .files
            .bytes
            .iter()
            .enumerate()
            .map(|(index, bytes)| FileProof {
                role: ROLES[index],
                bytes: bytes.len(),
                sha256: windows_write::digest(bytes),
            })
            .collect();
        // Everything written here is exclusively new. Partial journal evidence is
        // retained on any error, even before any destination file exists.
        io(fs::create_dir(&self.journal))?;
        let journal_pins = Pins::open(&self.journal)?;
        let intent = serde_json::to_vec(&Intent {
            schema: "espos.fresh-project-intent.v1",
            scope: &self.scope,
            root: &self.root,
            files: &proofs,
        })
        .map_err(|_| Code::InvalidInput)?;
        exclusive_bytes(&self.journal.join("intent.json"), &intent)?;
        for (index, bytes) in self.files.bytes.iter().enumerate() {
            exclusive_bytes(&self.journal.join(format!("payload-{index}.bin")), bytes)?;
        }
        journal_pins.check()?;
        self.parent.check()?;
        absent(&self.root)?;
        cancelled(cancel)?;
        *may_write = true; // BEFORE marker or any destination syscall.
        exclusive_bytes(
            &self.journal.join("may-write.json"),
            b"{\"schema\":\"espos.fresh-project-may-write.v1\"}",
        )?;
        self.parent.check()?;
        absent(&self.root)?;
        cancelled(cancel)?;
        io(fs::create_dir(&self.root))?;
        let mut directories = vec![
            self.parent,
            self.storage,
            journal_pins,
            Pins::open(&self.root)?,
        ];
        for relative in ["app", "app/src", "docs"] {
            for pins in &directories {
                pins.check()?;
            }
            cancelled(cancel)?;
            let path = member(&self.root, relative);
            io(fs::create_dir(&path))?;
            directories.push(Pins::open(&path)?);
        }
        for (index, bytes) in self.files.bytes.iter().enumerate() {
            for pins in &directories {
                pins.check()?;
            }
            cancelled(cancel)?;
            exclusive_bytes(&member(&self.root, ROLES[index]), bytes)?;
            #[cfg(test)]
            test_step(index + 1, &self.root)?;
        }
        // Reopen read-locked exact members and verify final bytes, not just writes
        // or mutable receipts. Keep these handles until the same-owner adoption.
        let mut read_handles = Vec::new();
        exact_layout(&self.root)?;
        for (index, bytes) in self.files.bytes.iter().enumerate() {
            for pins in &directories {
                pins.check()?;
            }
            cancelled(cancel)?;
            let mut file = io(OpenOptions::new()
                .read(true)
                .share_mode(1)
                .custom_flags(REPARSE)
                .open(member(&self.root, ROLES[index])))?;
            if windows_write::fresh_project_snapshot(&mut file, bytes.len())? != *bytes {
                return Err(Code::Conflict);
            }
            read_handles.push(file);
        }
        let source = windows_read::read_selected(member(&self.root, ROLES[0]), false, cancel)?;
        if source.bytes != self.files.bytes[0] {
            return Err(Code::Conflict);
        }
        for pins in &directories {
            pins.check()?;
        }
        cancelled(cancel)?;
        exact_layout(&self.root)?;
        exclusive_bytes(
            &self.journal.join("verified.json"),
            &serde_json::to_vec(&proofs).map_err(|_| Code::InvalidInput)?,
        )?;
        Ok(Created {
            source,
            files: proofs,
            _directories: directories,
            _read_handles: read_handles,
        })
    }
}

#[cfg(test)]
thread_local! { pub(crate) static FAIL_AFTER: std::cell::Cell<usize> = const { std::cell::Cell::new(0) }; }
#[cfg(test)]
fn test_step(step: usize, root: &Path) -> Result<(), Code> {
    if step == 4 && FAIL_AFTER.with(|value| value.get()) == 5 {
        io(fs::write(
            root.join("TEST_ONLY-extra.tmp"),
            b"TEST_ONLY unrelated member",
        ))?;
    }
    if FAIL_AFTER.with(|value| value.get()) == step {
        Err(Code::IOFailure)
    } else {
        Ok(())
    }
}

#[cfg(test)]
#[path = "fresh_project_tests.rs"]
mod tests;
