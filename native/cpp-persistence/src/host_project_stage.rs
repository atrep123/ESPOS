//! Native saved-app INPUT staging only. No SDK recipe, compiler, IPC or build
//! receipt. Ordinary inherited app-local ACLs are not a same-user security
//! boundary. Never reuse, overwrite or delete stages, including partial ones.
use super::*;
use crate::{
    fresh_project::member,
    windows_write::{self, HeldTarget, Pins, Revision},
};
use std::{
    ffi::c_void,
    fs::{self, File, OpenOptions},
    io::Write,
    os::windows::{
        fs::{MetadataExt, OpenOptionsExt},
        io::AsRawHandle,
    },
    path::Path,
};

const STORAGE_NAME: &str = "cpp-build-inputs-v1";
const OWNER: &[u8] = b"espos.native-saved-app-inputs.v1\n";
// At most 32 retained stages, each <= 1 MiB + 3 * 64 KiB. Partial and
// historical directories consume slots too. No eviction or recovery adoption.
const MAX_STAGES: usize = 32;
const REPARSE: u32 = 0x00200000;
const DIRECTORY: u32 = 0x02000000;
const DIRECTORIES: [&str; 4] = ["", "app", "app/src", "docs"];

/// Non-Clone owned staged input lifetime, returned only by the native Host.
/// Holds the original saved lease, namespace pins, and four staged read locks.
/// Drop releases locks/Busy, retains inputs, and reports no build outcome.
/// Retained and partial inputs count toward 32 slots; explicit retention and
/// cleanup UX is still needed. This component alone is not end-user build ready.
///
/// Native consumers can name the owned field without any dependency/pin change:
/// ```no_run
/// use espos_cpp_persistence::{Code, host::{Binding, NativeHost, SavedAppLease, StagedAppInputs}};
/// struct OwnedBuildInputs { inputs: StagedAppInputs }
/// fn stage(host: &NativeHost, binding: &Binding, lease: SavedAppLease) -> Result<OwnedBuildInputs, Code> {
///     let mut inputs = host.stage_saved_app_inputs(binding, lease)?;
///     let _generated_input_path = inputs.native_stage_path()?;
///     inputs.validate()?;
///     Ok(OwnedBuildInputs { inputs }) // retain through downstream drain
/// }
/// ```
/// The lifetime is not Clone or a renderer DTO:
/// ```compile_fail
/// use espos_cpp_persistence::host::StagedAppInputs;
/// fn duplicate(inputs: &StagedAppInputs) -> StagedAppInputs { inputs.clone() }
/// ```
/// ```compile_fail
/// use espos_cpp_persistence::host::StagedAppInputs;
/// fn encode(inputs: &StagedAppInputs) { let _ = serde_json::to_vec(inputs); }
/// ```
/// ```compile_fail
/// use espos_cpp_persistence::host::StagedAppInputs;
/// fn decode() { let _: StagedAppInputs = serde_json::from_str("{}").unwrap(); }
/// ```
/// ```compile_fail
/// use espos_cpp_persistence::host::StagedAppInputs;
/// fn from_path(path: &std::path::Path) { let _ = StagedAppInputs::from_path(path); }
/// ```
pub struct StagedAppInputs {
    staged: Option<HeldApp>,
    namespace: Option<StageNamespace>,
    root: PathBuf,
    baseline: [Revision; 4],
    source: SavedAppLease,
}

impl StagedAppInputs {
    pub fn cancel_requested(&self) -> bool {
        self.source.cancel_requested()
    }
    /// Recheck source ownership/version/draft/metadata, staged bytes and both
    /// namespaces before downstream use. Cancellation does not release Busy.
    pub fn validate(&mut self) -> Result<(), Code> {
        self.source.validate()?;
        let result = (|| {
            self.namespace.as_mut().ok_or(Code::Unavailable)?.check()?;
            self.staged
                .as_mut()
                .ok_or(Code::Unavailable)?
                .check(&self.baseline)?;
            self.namespace.as_mut().ok_or(Code::Unavailable)?.check()
        })();
        if result.is_err() {
            self.source.ownership.cancel.store(true, Ordering::Release);
        }
        result?;
        self.source.validate()
    }
    /// Native-only seam for a future owned build. Exposes ONLY the generated
    /// input directory, never the original source project. Keep this object
    /// through real child-process drain; validate again before use/publication.
    /// This path is not a constructor, renderer grant or successful build.
    pub fn native_stage_path(&mut self) -> Result<&Path, Code> {
        self.validate()?;
        Ok(&self.root)
    }
}
impl Drop for StagedAppInputs {
    fn drop(&mut self) {
        // Release every staged handle before source Drop drains owner Busy.
        drop(self.staged.take());
        drop(self.namespace.take());
    }
}

fn io<T>(value: std::io::Result<T>) -> Result<T, Code> {
    value.map_err(|e| match e.raw_os_error() {
        Some(32 | 33) => Code::Busy,
        _ => match e.kind() {
            std::io::ErrorKind::AlreadyExists => Code::Conflict,
            std::io::ErrorKind::PermissionDenied => Code::Denied,
            _ => Code::IOFailure,
        },
    })
}

// Pins already enforce NTFS, directory identity/ACL/attributes and ancestry.
// Additionally inspect directory streams via a bounded held-handle query;
// directories may have no default stream, but must have no named streams.
#[link(name = "kernel32")]
extern "system" {
    fn GetFileInformationByHandleEx(h: *mut c_void, class: i32, data: *mut c_void, len: u32)
        -> i32;
}
struct DirectoryPin {
    pins: Pins,
    handle: File,
}
impl DirectoryPin {
    fn open(path: &Path) -> Result<Self, Code> {
        let pins = Pins::open(path)?;
        let handle = io(OpenOptions::new()
            .access_mode(0x00020081)
            .share_mode(3)
            .custom_flags(REPARSE | DIRECTORY)
            .open(path))?;
        let value = Self { pins, handle };
        value.check()?;
        Ok(value)
    }
    fn check(&self) -> Result<(), Code> {
        self.pins.check()?;
        // Aligned, fixed 4096 bytes, no retry. FILE_STREAM_INFO (7), borrowed
        // live directory handle and writable buffer.
        let mut buffer = [0u64; 512];
        if unsafe {
            GetFileInformationByHandleEx(
                self.handle.as_raw_handle(),
                7,
                buffer.as_mut_ptr().cast(),
                4096,
            )
        } == 0
        {
            // NTFS reports ERROR_HANDLE_EOF for a directory with no streams.
            // No other failure admits the directory or triggers a fallback.
            if std::io::Error::last_os_error().raw_os_error() == Some(38) {
                return Ok(());
            }
            return Err(Code::UnsupportedPath);
        }
        let bytes = unsafe { std::slice::from_raw_parts(buffer.as_ptr().cast::<u8>(), 4096) };
        let next = u32::from_le_bytes(bytes[0..4].try_into().unwrap());
        let len = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
        // Zeroed FILE_STREAM_INFO denotes a directory with no streams.
        if next == 0 && len == 0 {
            return Ok(());
        }
        let default: Vec<u8> = "::$DATA"
            .encode_utf16()
            .flat_map(u16::to_le_bytes)
            .collect();
        if next != 0 || len != default.len() || bytes[24..24 + default.len()] != default {
            return Err(Code::UnsupportedPath);
        }
        Ok(())
    }
}

fn read_control(path: &Path, expected: &[u8]) -> Result<File, Code> {
    let mut file = io(OpenOptions::new()
        .read(true)
        .share_mode(1)
        .custom_flags(REPARSE)
        .open(path))?;
    if windows_write::fresh_project_snapshot(&mut file, expected.len())? != expected {
        return Err(Code::Conflict);
    }
    Ok(file)
}
#[repr(C)]
#[derive(Default, PartialEq, Eq)]
struct CreationStamp {
    created: i64,
    access: i64,
    write: i64,
    change: i64,
    attributes: u32,
    padding: u32,
}
fn creation_stamp(file: &File) -> Result<CreationStamp, Code> {
    let mut value = CreationStamp::default();
    if unsafe {
        GetFileInformationByHandleEx(
            file.as_raw_handle(),
            0,
            (&mut value as *mut CreationStamp).cast(),
            std::mem::size_of::<CreationStamp>() as u32,
        )
    } == 0
    {
        return Err(Code::IOFailure);
    }
    // Reads may advance access time; it is not mutation evidence.
    value.access = 0;
    Ok(value)
}
struct CreatedFile {
    pin: File,
    stamp: CreationStamp,
}
impl CreatedFile {
    fn check(&self) -> Result<(), Code> {
        if creation_stamp(&self.pin)? != self.stamp {
            return Err(Code::Conflict);
        }
        Ok(())
    }
}
fn create_bytes(path: &Path, bytes: &[u8], lease: &SavedAppLease) -> Result<CreatedFile, Code> {
    cancelled(lease)?;
    let mut file = io(OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .share_mode(1)
        .custom_flags(REPARSE)
        .open(path))?;
    for chunk in bytes.chunks(8192) {
        cancelled(lease)?;
        io(file.write_all(chunk))?;
        step(12, lease, path)?;
    }
    io(file.sync_all())?;
    if windows_write::fresh_project_snapshot(&mut file, bytes.len())? != bytes {
        return Err(Code::Conflict);
    }
    cancelled(lease)?;
    created_file_pin(path)
}

fn created_file_pin(path: &Path) -> Result<CreatedFile, Code> {
    // READ_DATA pin acquired while CREATE_NEW is still held. Metadata-only
    // handles do not exclude NTFS renames. SHARE_READ|WRITE permits this
    // existing writer, but omits SHARE_DELETE, excluding replacements across
    // handoff. The creation stamp detects same-object edits before SHARE_READ
    // fixed-role locks take over, even if an actor restores identical bytes.
    let pin = io(OpenOptions::new()
        .read(true)
        .share_mode(3)
        .custom_flags(REPARSE)
        .open(path))?;
    let stamp = creation_stamp(&pin)?;
    Ok(CreatedFile { pin, stamp })
}

enum BootstrapControl {
    Budget,
    Owner,
}
fn create_bootstrap_control(
    storage: &Path,
    control: BootstrapControl,
) -> Result<CreatedFile, Code> {
    // Once a fresh shared namespace exists, finish these two fixed controls as
    // a bounded critical section. No caller bytes, stages or build outcome are
    // admitted here. Cancellation is honored before admitting any stage below.
    let (name, bytes): (&str, &[u8]) = match control {
        BootstrapControl::Budget => ("budget.lock", b""),
        BootstrapControl::Owner => ("owner.bin", OWNER),
    };
    let path = storage.join(name);
    let mut file = io(OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .share_mode(1)
        .custom_flags(REPARSE)
        .open(&path))?;
    io(file.write_all(bytes))?;
    io(file.sync_all())?;
    if windows_write::fresh_project_snapshot(&mut file, bytes.len())? != bytes {
        return Err(Code::Conflict);
    }
    created_file_pin(&path)
}
fn cancelled(lease: &SavedAppLease) -> Result<(), Code> {
    if lease.cancel_requested() {
        Err(Code::Revoked)
    } else {
        Ok(())
    }
}
fn stage_name(name: &str) -> bool {
    name.strip_prefix("stage-").is_some_and(|v| {
        v.len() == 32
            && v.bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    })
}
fn capacity(root: &Path) -> Result<usize, Code> {
    let mut count = 0;
    let mut controls = 0;
    for entry in io(fs::read_dir(root))? {
        let entry = io(entry)?;
        let name = entry
            .file_name()
            .into_string()
            .map_err(|_| Code::UnsupportedPath)?;
        let meta = io(fs::symlink_metadata(entry.path()))?;
        if meta.file_attributes() & 0x400 != 0 {
            return Err(Code::UnsupportedPath);
        }
        if name == "owner.bin" || name == "budget.lock" {
            if !meta.is_file() {
                return Err(Code::Conflict);
            }
            controls += 1;
        } else if stage_name(&name) && meta.is_dir() {
            count += 1;
            if count > MAX_STAGES {
                return Err(Code::TooLarge);
            }
        } else {
            return Err(Code::Conflict);
        }
    }
    if controls != 2 {
        return Err(Code::Conflict);
    }
    Ok(count)
}

struct StageNamespace {
    storage: PathBuf,
    directories: Vec<DirectoryPin>,
    owner: File,
    budget: CreatedFile,
}
impl StageNamespace {
    fn check(&mut self) -> Result<(), Code> {
        for pin in &self.directories {
            pin.check()?;
        }
        if windows_write::fresh_project_snapshot(&mut self.owner, OWNER.len())? != OWNER {
            return Err(Code::Conflict);
        }
        self.budget.check()?;
        windows_write::fresh_project_snapshot(&mut self.budget.pin, 0)?;
        self.budget.check()?;
        capacity(&self.storage)?;
        Ok(())
    }
}

pub(super) fn stage(mut lease: SavedAppLease) -> Result<StagedAppInputs, Code> {
    lease.validate()?;
    // The existing Host's native storage, NEVER a source ancestor or journal
    // intent path. The two recovery catalogues enumerate different siblings.
    let parent = lease
        .ownership
        .host
        .project_storage
        .parent()
        .ok_or(Code::Unavailable)?;
    let parent = parent.to_path_buf();
    let parent_pin = DirectoryPin::open(&parent)?;
    let storage = parent.join(STORAGE_NAME);
    let mut creation_pins = Vec::new();
    step(0, &lease, &storage)?;
    cancelled(&lease)?;
    match fs::create_dir(&storage) {
        Ok(()) => {
            let pin = DirectoryPin::open(&storage)?;
            step(13, &lease, &storage)?;
            // Only a freshly created namespace gets controls. Finish its fixed
            // bootstrap despite cancellation; never copy app inputs or mint a
            // stage after revocation. IO-failure partials remain preserved.
            creation_pins.push(create_bootstrap_control(
                &storage,
                BootstrapControl::Budget,
            )?);
            step(14, &lease, &storage)?;
            creation_pins.push(create_bootstrap_control(&storage, BootstrapControl::Owner)?);
            pin.check()?;
        }
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => (),
        Err(e) => return io::<StagedAppInputs>(Err(e)),
    }
    cancelled(&lease)?;
    let storage_pin = DirectoryPin::open(&storage)?;
    let owner = read_control(&storage.join("owner.bin"), OWNER)?;
    for created in &creation_pins {
        created.check()?;
    }
    // Controls revalidated below; owner is read-locked.
    creation_pins.clear();
    // Serialize capacity+mkdir across native callers. OPEN_EXISTING only: never
    // repair missing/corrupt controls or truncate anything in trusted userdata.
    let mut budget = io(OpenOptions::new()
        .read(true)
        .write(true)
        .share_mode(1)
        .custom_flags(REPARSE)
        .open(storage.join("budget.lock")))?;
    if !windows_write::fresh_project_snapshot(&mut budget, 0)?.is_empty() {
        return Err(Code::Conflict);
    }
    // Read pin permits the next cooperating admission writer, whose SHARE_READ
    // excludes other writers. It prevents replacement across the staged
    // lifetime and validates metadata/streams/links before every use.
    let mut budget_pin = io(OpenOptions::new()
        .read(true)
        .share_mode(3)
        .custom_flags(REPARSE)
        .open(storage.join("budget.lock")))?;
    windows_write::fresh_project_snapshot(&mut budget_pin, 0)?;
    let stamp = creation_stamp(&budget_pin)?;
    let mut namespace = StageNamespace {
        storage: storage.clone(),
        directories: vec![parent_pin, storage_pin],
        owner,
        budget: CreatedFile {
            pin: budget_pin,
            stamp,
        },
    };
    namespace.check()?;
    if capacity(&storage)? >= MAX_STAGES {
        return Err(Code::TooLarge);
    }
    lease.validate()?;
    step(1, &lease, &storage)?;
    namespace.check()?;
    cancelled(&lease)?;
    let root = storage.join(format!("stage-{}", windows_read::random_hex()?));
    for role in crate::fresh_project::ROLES {
        windows_read::validate_path(&member(&root, role))?;
    }
    // CREATE_NEW equivalent for directories; no collision retries or adoption.
    io(fs::create_dir(&root))?;
    namespace.directories.push(DirectoryPin::open(&root)?);
    step(2, &lease, &root)?;
    for relative in &DIRECTORIES[1..] {
        namespace.check()?;
        cancelled(&lease)?;
        let path = member(&root, relative);
        io(fs::create_dir(&path))?;
        namespace.directories.push(DirectoryPin::open(&path)?);
    }
    let mut handles = Vec::new();
    for index in 0..4 {
        namespace.check()?;
        lease.validate()?;
        let bytes = &lease.held.as_ref().ok_or(Code::Unavailable)?.members[index].bytes;
        creation_pins.push(create_bytes(
            &member(&root, crate::fresh_project::ROLES[index]),
            bytes,
            &lease,
        )?);
        step(3 + index * 2, &lease, &root)?;
        // Fixed-role read methods check bounded ordinary NTFS, streams, links
        // and namespace. Hold each lock as soon as that member is captured.
        let mut held = HeldTarget::read_project_member(&root, index)?;
        let cap = if index == 0 { MAX_SOURCE_BYTES } else { 65_536 };
        if held.project_snapshot_bounded(cap)?.bytes != *bytes {
            return Err(Code::Conflict);
        }
        creation_pins.last().ok_or(Code::Unavailable)?.check()?;
        handles.push(held);
        step(4 + index * 2, &lease, &root)?;
    }
    lease.validate()?;
    namespace.check()?;
    let staged = HeldApp::open(&root)?;
    let baseline = staged.members.clone();
    for (index, revision) in baseline.iter().enumerate() {
        if revision.bytes != lease.held.as_ref().ok_or(Code::Unavailable)?.members[index].bytes {
            return Err(Code::Conflict);
        }
    }
    step(11, &lease, &root)?;
    for created in &creation_pins {
        created.check()?;
    }
    // Drain all temporary handles while the original lease still owns Busy.
    // After transfer, even final-validation failure must release EVERY staged
    // lock before source Drop clears that same owner's busy reservation.
    drop(handles);
    drop(creation_pins);
    drop(budget);
    let mut result = StagedAppInputs {
        staged: Some(staged),
        namespace: Some(namespace),
        root,
        baseline,
        source: lease,
    };
    result.validate()?;
    // All members now read-locked. No success marker or journal registration.
    Ok(result)
}

fn step(_step: usize, _lease: &SavedAppLease, _path: &Path) -> Result<(), Code> {
    #[cfg(test)]
    return TEST_STEP.with(|hook| match &mut *hook.borrow_mut() {
        Some(hook) => hook(_step, _lease, _path),
        None => Ok(()),
    });
    #[cfg(not(test))]
    Ok(())
}
#[cfg(test)]
type TestHook = Box<dyn FnMut(usize, &SavedAppLease, &Path) -> Result<(), Code>>;
#[cfg(test)]
thread_local! { static TEST_STEP: std::cell::RefCell<Option<TestHook>> = const { std::cell::RefCell::new(None) }; }
#[cfg(test)]
#[path = "host_project_stage_tests.rs"]
mod tests;
