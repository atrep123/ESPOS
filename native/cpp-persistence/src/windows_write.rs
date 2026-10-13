//! Conventional local-cooperative Windows editor persistence.
//! Same-held-data-handle writes, NOT atomic replacement/CAS, same-user attacker
//! exclusion, or proof of joint power-loss namespace durability.
use crate::windows_read;
use crate::{Code, DocumentId, RequestId, Version, MAX_SOURCE_BYTES};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    ffi::c_void,
    fs::{File, OpenOptions},
    io::{Read, Seek, SeekFrom, Write},
    os::windows::{
        fs::{MetadataExt, OpenOptionsExt},
        io::AsRawHandle,
    },
    path::{Path, PathBuf},
    sync::atomic::{AtomicBool, Ordering},
};

const META: u32 = 0x00020080; // READ_CONTROL | FILE_READ_ATTRIBUTES
const REPARSE: u32 = 0x00200000;
const DIRECTORY: u32 = 0x02000000;
const WRITE_THROUGH: u32 = 0x80000000;
const BAD: u32 = 1 | 0x10 | 0x200 | 0x400 | 0x800 | 0x1000 | 0x4000;
const MAX_RECORD: usize = 8 * 1024 * 1024;
fn valid_artifact_kind(kind: &str) -> bool {
    matches!(
        kind,
        "backup.bin"
            | "payload.bin"
            | "intent.json"
            | "may-write.json"
            | "written.json"
            | "create-intent.json"
            | "create-payload.bin"
            | "create-may-write.json"
            | "created.json"
            | "create-written.json"
    )
}
#[cfg(test)]
#[path = "inspection_tests.rs"]
mod inspection_tests;
#[cfg(test)]
#[path = "journal_tests.rs"]
mod journal_tests;

#[link(name = "kernel32")]
extern "system" {
    fn GetFileInformationByHandleEx(
        h: *mut c_void,
        class: i32,
        data: *mut c_void,
        length: u32,
    ) -> i32;
    fn GetFileType(h: *mut c_void) -> u32;
    fn GetVolumeInformationByHandleW(
        h: *mut c_void,
        name: *mut u16,
        name_len: u32,
        serial: *mut u32,
        component: *mut u32,
        flags: *mut u32,
        fs: *mut u16,
        fs_len: u32,
    ) -> i32;
}

impl Journal {
    #[cfg(test)]
    fn scan_recovery(&self) -> Result<Vec<RecoveryRecord>, Code> {
        Ok(self.scan_recovery_evidence()?.0)
    }
    fn scan_recovery_evidence(
        &self,
    ) -> Result<
        (
            Vec<RecoveryRecord>,
            std::collections::HashMap<RequestId, PriorIntent>,
        ),
        Code,
    > {
        // Bounded, native-only enumeration. Keep every orphan; absence of an
        // intent/marker cannot prove that an interrupted operation never wrote.
        let mut operations = std::collections::BTreeMap::<String, bool>::new();
        for entry in io(std::fs::read_dir(&self.root))? {
            let name = io(entry)?
                .file_name()
                .into_string()
                .map_err(|_| Code::InvalidInput)?;
            if name == "host.lock" {
                continue;
            }
            let (id, kind) = name.split_once('.').ok_or(Code::InvalidInput)?;
            let _: RequestId = serde_json::from_value(serde_json::Value::String(id.into()))
                .map_err(|_| Code::InvalidInput)?;
            if !valid_artifact_kind(kind) {
                return Err(Code::InvalidInput);
            }
            let create = kind.starts_with("create-") || kind == "created.json";
            if let Some(previous) = operations.insert(id.into(), create) {
                if previous != create {
                    return Err(Code::Conflict);
                }
            }
        }
        let mut recovered = Vec::new();
        let mut evidence = std::collections::HashMap::new();
        for (id, create) in operations {
            let request: RequestId = serde_json::from_value(serde_json::Value::String(id))
                .map_err(|_| Code::InvalidInput)?;
            // Parse only a native-published intent. A missing/corrupt one fails
            // startup closed; no invented caller/grant/status is reconstituted.
            let kind = if create {
                "create-intent.json"
            } else {
                "intent.json"
            };
            let mut f = io(OpenOptions::new()
                .read(true)
                .share_mode(0)
                .custom_flags(REPARSE)
                .open(self.root.join(format!("{}.{}", request.as_str(), kind))))?;
            let (intent_artifact, bytes) = Self::observe(&mut f, MAX_RECORD)?;
            drop(f);
            let (scope, path, prepared, backup_available) = if create {
                let intent: CreateIntent =
                    serde_json::from_slice(&bytes).map_err(|_| Code::InvalidInput)?;
                (
                    intent.scope,
                    intent.path,
                    Prepared {
                        intent: intent_artifact,
                        backup: None,
                        payload: intent.payload,
                        create: true,
                    },
                    false,
                )
            } else {
                let intent: Intent =
                    serde_json::from_slice(&bytes).map_err(|_| Code::InvalidInput)?;
                let available = self
                    .read(&intent.scope, "backup.bin")
                    .is_ok_and(|(a, b)| a == intent.backup && b == intent.external.bytes);
                (
                    intent.scope,
                    intent.path,
                    Prepared {
                        intent: intent_artifact,
                        backup: Some(intent.backup),
                        payload: intent.payload,
                        create: false,
                    },
                    available,
                )
            };
            if scope.schema != 1 || scope.operation != request {
                return Err(Code::Denied);
            }
            admit_source_path(&path)?;
            let written = self
                .verify_historical_receipt(&scope, &prepared, &path)
                .is_ok();
            evidence.insert(
                request.clone(),
                PriorIntent {
                    scope: scope.clone(),
                    path: path.clone(),
                    prepared,
                },
            );
            recovered.push(RecoveryRecord {
                operation_id: request,
                document_id: scope.document,
                source_hash: scope.source_hash,
                source_bytes: scope.source_bytes,
                display_name: path
                    .file_name()
                    .and_then(|v| v.to_str())
                    .ok_or(Code::InvalidInput)?
                    .into(),
                phase: if written {
                    "written-receipt"
                } else {
                    "recovery-required"
                },
                backup_available,
            });
        }
        self.pins.check()?;
        Ok((recovered, evidence))
    }
    fn verify_historical_receipt(
        &self,
        s: &Scope,
        p: &Prepared,
        path: &Path,
    ) -> Result<Revision, Code> {
        // Proves a retained historical receipt, NOT current target bytes or
        // authority to adopt a prior session's document into a fresh editor.
        let payload_kind = if p.create {
            "create-payload.bin"
        } else {
            "payload.bin"
        };
        let (payload, bytes) = self.read(s, payload_kind)?;
        if payload != p.payload || bytes.len() != s.source_bytes || digest(&bytes) != s.source_hash
        {
            return Err(Code::Conflict);
        }
        let (created, after) = if p.create {
            let (artifact, bytes) = self.read(s, "create-intent.json")?;
            if artifact != p.intent {
                return Err(Code::Conflict);
            }
            let i: CreateIntent = serde_json::from_slice(&bytes).map_err(|_| Code::InvalidInput)?;
            if i.scope != *s || i.path != path || i.payload != p.payload || p.backup.is_some() {
                return Err(Code::Denied);
            }
            if self
                .read_create_marker(s, p, "create-may-write.json", "may-create")?
                .after
                .is_some()
            {
                return Err(Code::Denied);
            }
            let created = self
                .read_create_marker(s, p, "created.json", "held-created")?
                .after
                .ok_or(Code::Conflict)?;
            if !created.bytes.is_empty() || created.parents != i.parents {
                return Err(Code::Conflict);
            }
            let after = self
                .read_create_marker(s, p, "create-written.json", "verified-created-write")?
                .after
                .ok_or(Code::Conflict)?;
            (created, after)
        } else {
            let (artifact, bytes) = self.read(s, "intent.json")?;
            if artifact != p.intent {
                return Err(Code::Conflict);
            }
            let i: Intent = serde_json::from_slice(&bytes).map_err(|_| Code::InvalidInput)?;
            if i.scope != *s
                || i.path != path
                || Some(i.backup.clone()) != p.backup
                || i.payload != p.payload
            {
                return Err(Code::Denied);
            }
            let (backup, external) = self.read(s, "backup.bin")?;
            if backup != i.backup || external != i.external.bytes {
                return Err(Code::Conflict);
            }
            let (_, bytes) = self.read(s, "may-write.json")?;
            let marker: Marker = serde_json::from_slice(&bytes).map_err(|_| Code::InvalidInput)?;
            if marker.scope != *s
                || marker.intent_hash != p.intent.hash
                || marker.kind != "may-have-written"
                || marker.after.is_some()
            {
                return Err(Code::Denied);
            }
            let (_, bytes) = self.read(s, "written.json")?;
            let receipt: Marker = serde_json::from_slice(&bytes).map_err(|_| Code::InvalidInput)?;
            if receipt.scope != *s
                || receipt.intent_hash != p.intent.hash
                || receipt.kind != "verified-held-write"
            {
                return Err(Code::Denied);
            }
            (i.external, receipt.after.ok_or(Code::Conflict)?)
        };
        if !created.ordinary()
            || !after.ordinary()
            || !after.same_object_metadata(&created)
            || after.bytes != bytes
        {
            return Err(Code::Conflict);
        }
        Ok(after)
    }
}
#[link(name = "advapi32")]
extern "system" {
    fn GetKernelObjectSecurity(
        h: *mut c_void,
        requested: u32,
        data: *mut c_void,
        length: u32,
        needed: *mut u32,
    ) -> i32;
}

fn io<T>(result: std::io::Result<T>) -> Result<T, Code> {
    result.map_err(|e| match e.raw_os_error() {
        Some(5) => Code::Denied,
        Some(32) | Some(33) => Code::Busy,
        _ => Code::IOFailure,
    })
}
fn checked(ok: i32) -> Result<(), Code> {
    if ok == 0 {
        Err(Code::IOFailure)
    } else {
        Ok(())
    }
}
pub(crate) fn digest_raw(bytes: &[u8]) -> [u8; 32] {
    Sha256::digest(bytes).into()
}
pub(crate) fn digest(bytes: &[u8]) -> String {
    digest_raw(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

#[repr(C)]
#[derive(Default, Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(crate) struct FileId {
    volume: u64,
    id: [u8; 16],
}
#[repr(C)]
#[derive(Default)]
struct Basic {
    created: i64,
    access: i64,
    write: i64,
    change: i64,
    attributes: u32,
    padding: u32,
}
#[repr(C)]
#[derive(Default)]
struct Standard {
    allocation: i64,
    eof: i64,
    links: u32,
    delete_pending: u8,
    directory: u8,
    padding: [u8; 2],
}
fn query<T: Default>(file: &File, class: i32) -> Result<T, Code> {
    let mut data = T::default();
    checked(unsafe {
        GetFileInformationByHandleEx(
            file.as_raw_handle(),
            class,
            (&mut data as *mut T).cast(),
            std::mem::size_of::<T>() as u32,
        )
    })?;
    Ok(data)
}
fn identity(file: &File) -> Result<FileId, Code> {
    query(file, 18)
} // FileIdInfo, 128-bit ID
fn ntfs(file: &File) -> Result<(), Code> {
    let mut name = [0u16; 32];
    let mut flags = 0;
    checked(unsafe {
        GetVolumeInformationByHandleW(
            file.as_raw_handle(),
            std::ptr::null_mut(),
            0,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            &mut flags,
            name.as_mut_ptr(),
            32,
        )
    })?;
    let end = name
        .iter()
        .position(|c| *c == 0)
        .ok_or(Code::UnsupportedPath)?;
    if String::from_utf16(&name[..end]).map_err(|_| Code::UnsupportedPath)? != "NTFS"
        || flags & 8 == 0
        || flags & 0x40000 == 0
    {
        return Err(Code::UnsupportedPath);
    }
    Ok(())
}
fn security(file: &File) -> Result<String, Code> {
    // One bounded aligned buffer; no ACL edit, privileges, fallback or retry.
    let mut data = vec![0u64; 8192];
    let mut needed = 0;
    checked(unsafe {
        GetKernelObjectSecurity(
            file.as_raw_handle(),
            7,
            data.as_mut_ptr().cast(),
            65536,
            &mut needed,
        )
    })?;
    if needed == 0 || needed > 65536 {
        return Err(Code::UnsupportedPath);
    }
    let bytes = unsafe { std::slice::from_raw_parts(data.as_ptr().cast::<u8>(), needed as usize) };
    Ok(digest(bytes))
}
fn streams(file: &File) -> Result<bool, Code> {
    let mut data = vec![0u64; 8192];
    checked(unsafe {
        GetFileInformationByHandleEx(file.as_raw_handle(), 7, data.as_mut_ptr().cast(), 65536)
    })?;
    let bytes = unsafe { std::slice::from_raw_parts(data.as_ptr().cast::<u8>(), 65536) };
    let mut offset = 0;
    let mut count = 0;
    loop {
        if offset + 24 > bytes.len() || count >= 128 {
            return Err(Code::UnsupportedPath);
        }
        let next = u32::from_le_bytes(
            bytes[offset..offset + 4]
                .try_into()
                .map_err(|_| Code::UnsupportedPath)?,
        ) as usize;
        let len = u32::from_le_bytes(
            bytes[offset + 4..offset + 8]
                .try_into()
                .map_err(|_| Code::UnsupportedPath)?,
        ) as usize;
        if len % 2 != 0 || len > 65536 || offset + 24 + len > bytes.len() {
            return Err(Code::UnsupportedPath);
        }
        let name: Vec<_> = bytes[offset + 24..offset + 24 + len]
            .chunks_exact(2)
            .map(|b| u16::from_le_bytes([b[0], b[1]]))
            .collect();
        if String::from_utf16(&name).map_err(|_| Code::UnsupportedPath)? != "::$DATA" {
            return Ok(false);
        }
        count += 1;
        if next == 0 {
            return Ok(count == 1);
        }
        if next < 24 + len || next % 8 != 0 {
            return Err(Code::UnsupportedPath);
        }
        offset = offset.checked_add(next).ok_or(Code::UnsupportedPath)?;
    }
}
fn read_bytes(file: &mut File, cap: usize) -> Result<Vec<u8>, Code> {
    io(file.seek(SeekFrom::Start(0)))?;
    let mut bytes = Vec::new();
    let mut chunk = [0u8; 8192];
    loop {
        let n = io(file.read(&mut chunk))?;
        if n == 0 {
            break;
        }
        if bytes.len() + n > cap {
            return Err(Code::TooLarge);
        }
        bytes.extend_from_slice(&chunk[..n]);
    }
    Ok(bytes)
}
pub(crate) fn admit_source_path(path: &Path) -> Result<(), Code> {
    windows_read::validate_path(path)?;
    let ext = path
        .extension()
        .and_then(|v| v.to_str())
        .map(str::to_ascii_lowercase);
    if !matches!(ext.as_deref(), Some("cpp" | "cc" | "cxx")) {
        return Err(Code::Denied);
    }
    Ok(())
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Parent {
    id: FileId,
    security: String,
    attributes: u32,
}
// Keep the native ancestor handles alive even when only the captured facts are
// read. Their lifetime pins the namespace; it is not metadata actor exclusion.
struct Pins {
    paths: Vec<PathBuf>,
    _handles: Vec<File>,
    facts: Vec<Parent>,
}
impl Pins {
    fn open(parent: &Path) -> Result<Self, Code> {
        // Reuse conservative lexical validator with a non-secret sentinel name.
        windows_read::validate_path(&parent.join("namespace-check.cpp"))?;
        let mut paths: Vec<_> = parent.ancestors().map(Path::to_path_buf).collect();
        paths.reverse();
        if paths.len() > 33 {
            return Err(Code::UnsupportedPath);
        }
        let mut handles = Vec::new();
        let mut facts = Vec::new();
        for path in &paths {
            let file = io(OpenOptions::new()
                .access_mode(META)
                .share_mode(3)
                .custom_flags(DIRECTORY | REPARSE)
                .open(path))?;
            ntfs(&file)?;
            let basic: Basic = query(&file, 0)?;
            if basic.attributes & 0x10 == 0 || basic.attributes & 0x400 != 0 {
                return Err(Code::UnsupportedPath);
            }
            facts.push(Parent {
                id: identity(&file)?,
                security: security(&file)?,
                attributes: basic.attributes,
            });
            handles.push(file);
        }
        Ok(Self {
            paths,
            _handles: handles,
            facts,
        })
    }
    fn check(&self) -> Result<(), Code> {
        let fresh = Self::open(self.paths.last().ok_or(Code::UnsupportedPath)?)?;
        if fresh.facts != self.facts {
            return Err(Code::Conflict);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(crate) struct Revision {
    id: FileId,
    parents: Vec<Parent>,
    security: String,
    attributes: u32,
    links: u32,
    delete_pending: bool,
    streams_ok: bool,
    created: i64,
    write: i64,
    change: i64,
    pub(crate) bytes: Vec<u8>,
}
impl Revision {
    pub(crate) fn ordinary(&self) -> bool {
        self.attributes & BAD == 0 && self.links == 1 && !self.delete_pending && self.streams_ok
    }
    pub(crate) fn same_revision(&self, other: &Self) -> bool {
        self == other
    }
    pub(crate) fn same_object_metadata(&self, other: &Self) -> bool {
        self.id == other.id
            && self.parents == other.parents
            && self.security == other.security
            && self.attributes == other.attributes
            && self.links == other.links
            && self.created == other.created
            && self.delete_pending == other.delete_pending
            && self.streams_ok == other.streams_ok
    }
}
pub(crate) struct HeldTarget {
    path: PathBuf,
    file: File,
    pins: Pins,
}
pub(crate) fn capture_read_grant(path: &Path, file: &File) -> Result<Revision, Code> {
    admit_source_path(path)?;
    let pins = Pins::open(path.parent().ok_or(Code::UnsupportedPath)?)?;
    // try_clone duplicates the original READ-ONLY grant handle. It cannot
    // acquire WRITE permission, and never creates/truncates a file.
    let mut held = HeldTarget {
        path: path.to_path_buf(),
        file: io(file.try_clone())?,
        pins,
    };
    let revision = held.snapshot()?;
    held.check_namespace()?;
    if !revision.ordinary() {
        return Err(Code::UnsupportedPath);
    }
    Ok(revision)
}
impl HeldTarget {
    pub(crate) fn open(path: &Path) -> Result<Self, Code> {
        admit_source_path(path)?;
        let pins = Pins::open(path.parent().ok_or(Code::UnsupportedPath)?)?;
        // OPEN_EXISTING, NEVER truncate/create/rename/reopen for target writes.
        let file = io(OpenOptions::new()
            .read(true)
            .write(true)
            .share_mode(0)
            .custom_flags(REPARSE | WRITE_THROUGH)
            .open(path))?;
        ntfs(&file)?;
        Ok(Self {
            path: path.to_path_buf(),
            file,
            pins,
        })
    }
    pub(crate) fn snapshot(&mut self) -> Result<Revision, Code> {
        if unsafe { GetFileType(self.file.as_raw_handle()) } != 1 {
            return Err(Code::UnsupportedPath);
        }
        self.pins.check()?;
        let id = identity(&self.file)?;
        let basic: Basic = query(&self.file, 0)?;
        let standard: Standard = query(&self.file, 1)?;
        if standard.eof < 0 || standard.eof > MAX_SOURCE_BYTES as i64 || standard.directory != 0 {
            return Err(Code::UnsupportedPath);
        }
        let security = security(&self.file)?;
        let streams_ok = streams(&self.file)?;
        let bytes = read_bytes(&mut self.file, MAX_SOURCE_BYTES)?;
        let after: Basic = query(&self.file, 0)?;
        let after_std: Standard = query(&self.file, 1)?;
        if id != identity(&self.file)?
            || basic.write != after.write
            || basic.change != after.change
            || basic.attributes != after.attributes
            || standard.eof != after_std.eof
            || standard.links != after_std.links
            || standard.delete_pending != after_std.delete_pending
            || bytes.len() != standard.eof as usize
            || security != self::security(&self.file)?
            || streams_ok != streams(&self.file)?
        {
            return Err(Code::Conflict);
        }
        Ok(Revision {
            id,
            parents: self.pins.facts.clone(),
            security,
            attributes: basic.attributes,
            links: standard.links,
            delete_pending: standard.delete_pending != 0,
            streams_ok,
            created: basic.created,
            write: basic.write,
            change: basic.change,
            bytes,
        })
    }
    pub(crate) fn check_namespace(&self) -> Result<(), Code> {
        self.pins.check()?;
        let fresh = io(OpenOptions::new()
            .access_mode(0)
            .share_mode(7)
            .custom_flags(REPARSE)
            .open(&self.path))?;
        let basic: Basic = query(&fresh, 0)?;
        if identity(&fresh)? != identity(&self.file)? || basic.attributes & 0x400 != 0 {
            return Err(Code::Conflict);
        }
        Ok(())
    }
    pub(crate) fn selection(&self, revision: &Revision) -> Result<windows_read::Selection, Code> {
        // Called under the SAME held handle after durable verification/recheck.
        Ok(windows_read::Selection {
            path: self.path.clone(),
            parent: self.legacy_parent()?,
            file: Some(windows_read::writer_identity(&self.file)?),
            sha256: Some(digest_raw(&revision.bytes)),
            bytes: revision.bytes.clone(),
            writer_revision: Some(revision.clone()),
        })
    }
    pub(crate) fn legacy_parent(&self) -> Result<windows_read::Identity, Code> {
        self.pins.check()?;
        windows_read::capture_parent_identity(&self.path)
    }
    pub(crate) fn recheck(&mut self, expected: &Revision) -> Result<(), Code> {
        if !self.snapshot()?.same_revision(expected) {
            return Err(Code::Conflict);
        }
        self.check_namespace()
    }
    pub(crate) fn update(&mut self, bytes: &[u8], cancel: &AtomicBool) -> Result<(), Code> {
        io(self.file.seek(SeekFrom::Start(0)))?;
        for chunk in bytes.chunks(8192) {
            if cancel.load(Ordering::Acquire) {
                return Err(Code::Revoked);
            }
            io(self.file.write_all(chunk))?;
        }
        if cancel.load(Ordering::Acquire) {
            return Err(Code::Revoked);
        }
        // set_len uses SAME held target handle; even empty saves mutate here.
        io(self.file.set_len(bytes.len() as u64))?;
        io(self.file.sync_all())?;
        Ok(()) // actual FlushFileBuffers via std
    }
}

#[cfg(test)]
mod tests {
    // Pure metadata/codec fixtures, not a same-user actor-exclusion test or
    // power-loss experiment. Native filesystem cases are in journal_tests.
    use super::*;
    fn revision() -> Revision {
        Revision {
            id: FileId {
                volume: 1,
                id: [2; 16],
            },
            parents: vec![],
            security: digest(b"TEST_ONLY_SD"),
            attributes: 32,
            links: 1,
            delete_pending: false,
            streams_ok: true,
            created: 1,
            write: 2,
            change: 3,
            bytes: b"ACTUAL_E".to_vec(),
        }
    }
    #[test]
    fn bytes_are_part_of_confirmed_revision() {
        let a = revision();
        let mut b = a.clone();
        b.bytes = b"LATER_E".to_vec();
        assert!(!a.same_revision(&b));
    }
    #[test]
    fn late_hardlink_is_metadata_conflict_not_excluded_actor() {
        let a = revision();
        let mut b = a.clone();
        b.links = 2;
        assert!(!b.ordinary());
        assert!(!a.same_object_metadata(&b));
    }
    #[test]
    fn late_acl_is_metadata_conflict_not_excluded_actor() {
        let a = revision();
        let mut b = a.clone();
        b.security = digest(b"LATE_SD");
        assert!(!a.same_object_metadata(&b));
    }
    #[test]
    fn new_bytes_may_preserve_object_but_not_revision() {
        let a = revision();
        let mut b = a.clone();
        b.bytes = b"N".to_vec();
        b.write += 1;
        b.change += 1;
        assert!(a.same_object_metadata(&b));
        assert!(!a.same_revision(&b));
    }
    #[test]
    fn namespace_parent_identity_is_confirmed_evidence() {
        let a = revision();
        let mut b = a.clone();
        b.parents.push(Parent {
            id: FileId::default(),
            security: "x".into(),
            attributes: 16,
        });
        assert!(!a.same_object_metadata(&b));
    }
    #[test]
    fn named_stream_or_delete_pending_denies_write_domain() {
        let mut a = revision();
        a.streams_ok = false;
        assert!(!a.ordinary());
        a.streams_ok = true;
        a.delete_pending = true;
        assert!(!a.ordinary());
    }
    #[test]
    fn unsupported_attributes_are_not_silently_normalized() {
        for bit in [1, 16, 0x200, 0x400, 0x800, 0x1000, 0x4000] {
            let mut a = revision();
            a.attributes |= bit;
            assert!(!a.ordinary());
        }
    }
    #[test]
    fn durable_marker_rejects_caller_chosen_status_field() {
        let value = serde_json::json!({"scope":{},"intent_hash":"x","kind":"verified-held-write","after":null,"status":"saved"});
        assert!(serde_json::from_value::<Marker>(value).is_err());
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(crate) struct Scope {
    pub(crate) schema: u8,
    pub(crate) operation: RequestId,
    pub(crate) session: String,
    pub(crate) incarnation: String,
    pub(crate) document: DocumentId,
    pub(crate) version: Option<Version>,
    pub(crate) source_hash: String,
    pub(crate) source_bytes: usize,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Artifact {
    id: FileId,
    security: String,
    hash: String,
    size: usize,
}
#[derive(Clone)]
pub(crate) struct Prepared {
    intent: Artifact,
    backup: Option<Artifact>,
    payload: Artifact,
    create: bool,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Intent {
    scope: Scope,
    path: PathBuf,
    external: Revision,
    backup: Artifact,
    payload: Artifact,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Marker {
    scope: Scope,
    intent_hash: String,
    kind: String,
    after: Option<Revision>,
}

/// Artifact component of the same native host registry, not an editable owner.
/// Host chooses app-local storage; no journal root comes from IPC/project data.
pub(crate) struct Journal {
    root: PathBuf,
    pins: Pins,
    _host_lock: File,
    prior_recovery: Vec<RecoveryRecord>,
    prior_intents: std::collections::HashMap<RequestId, PriorIntent>,
    reservations: std::sync::Mutex<std::collections::HashMap<RequestId, Budget>>,
    file_limit: usize,
    byte_limit: u64,
}
struct PriorIntent {
    scope: Scope,
    path: PathBuf,
    prepared: Prepared,
}
struct Budget {
    files: usize,
    bytes: u64,
}
/// Historical native journal evidence. It never grants an old caller/session
/// authority to a newly attached editor or automatically retries/restores bytes.
#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RecoveryRecord {
    pub operation_id: RequestId,
    pub document_id: DocumentId,
    pub source_hash: String,
    pub source_bytes: usize,
    pub display_name: String,
    pub phase: &'static str,
    pub backup_available: bool,
}
/// Detached native historical data, never a caller, grant, or editable owner.
/// Deliberately has no IPC codec or conversion into live registry authority.
#[derive(Clone, Debug)]
pub struct RecoveryScope {
    pub schema: u8,
    pub operation_id: RequestId,
    pub session: String,
    pub incarnation: String,
    pub document_id: DocumentId,
    pub captured_version: Option<Version>,
    pub source_hash: String,
    pub source_bytes: usize,
}
/// Observed under a read-only handle. Comparison uses a verified historical
/// receipt if available, otherwise the overwrite intent's external revision.
/// Present means no historical target revision exists (unfinished create).
#[derive(Clone, Debug)]
pub enum CurrentTargetObservation {
    Unchanged { bytes: Vec<u8>, hash: String },
    Changed { bytes: Vec<u8>, hash: String },
    Present { bytes: Vec<u8>, hash: String },
    Missing,
    Busy,
    Denied,
    Error { code: Code },
}
/// Host-only inspection, not persistence success or authority to restore/adopt.
/// Every byte vector is detached and at most MAX_SOURCE_BYTES raw bytes.
#[derive(Clone, Debug)]
pub struct RecoveryInspection {
    pub prior_record: RecoveryRecord,
    pub scope: RecoveryScope,
    pub native_path: PathBuf,
    pub payload: Vec<u8>,
    /// None only for a create intent, which has no actual external backup.
    pub backup: Option<Vec<u8>>,
    pub current: CurrentTargetObservation,
}
fn inspect_current_target(path: &Path, reference: Option<&Revision>) -> CurrentTargetObservation {
    let observed = (|| -> Result<Option<Revision>, Code> {
        admit_source_path(path)?;
        let pins = Pins::open(path.parent().ok_or(Code::UnsupportedPath)?)?;
        // OPEN_EXISTING read-only; no write access, CREATE_NEW, truncation, flush,
        // version/grant minting or registry adoption. Held handle is temporary.
        let file = match OpenOptions::new()
            .read(true)
            .share_mode(1)
            .custom_flags(REPARSE)
            .open(path)
        {
            Ok(file) => file,
            Err(e) if e.raw_os_error() == Some(2) => {
                pins.check()?;
                return Ok(None);
            }
            Err(e) => return io(Err(e)),
        };
        ntfs(&file)?;
        let standard: Standard = query(&file, 1)?;
        if standard.eof < 0 || standard.eof > MAX_SOURCE_BYTES as i64 {
            return Err(Code::TooLarge);
        }
        let mut target = HeldTarget {
            path: path.into(),
            file,
            pins,
        };
        let revision = target.snapshot()?;
        // A read-only attribute is acceptable for read-only inspection.
        if revision.attributes & (BAD & !1) != 0
            || revision.links != 1
            || revision.delete_pending
            || !revision.streams_ok
        {
            return Err(Code::UnsupportedPath);
        }
        target.recheck(&revision)?;
        Ok(Some(revision))
    })();
    match observed {
        Ok(None) => CurrentTargetObservation::Missing,
        Ok(Some(revision)) => {
            let hash = digest(&revision.bytes);
            match reference {
                Some(expected) if revision.same_revision(expected) => {
                    CurrentTargetObservation::Unchanged {
                        bytes: revision.bytes,
                        hash,
                    }
                }
                Some(_) => CurrentTargetObservation::Changed {
                    bytes: revision.bytes,
                    hash,
                },
                None => CurrentTargetObservation::Present {
                    bytes: revision.bytes,
                    hash,
                },
            }
        }
        Err(Code::Busy) => CurrentTargetObservation::Busy,
        Err(Code::Denied) => CurrentTargetObservation::Denied,
        Err(code) => CurrentTargetObservation::Error { code },
    }
}
const MAX_JOURNAL_FILES: usize = 4096;
const MAX_JOURNAL_BYTES: u64 = 512 * 1024 * 1024;

impl crate::writer::WriterEnvironment {
    /// The native app resolves its existing app-local storage directory. This
    /// native-only constructor accepts no IPC DTO and establishes no broker,
    /// principal isolation, or same-user attacker/power-loss guarantee.
    pub fn open_local(app_storage: &Path) -> Result<Self, Code> {
        Ok(Self {
            journal: Journal::open_local(app_storage)?,
        })
    }
    pub fn recovery_records(&self) -> &[RecoveryRecord] {
        &self.journal.prior_recovery
    }
    /// Trusted native host only; ID must already be in this startup catalog.
    /// No path/status DTO, retry, registration, admission change, or cleanup.
    pub fn inspect_recovery(&self, operation: &RequestId) -> Result<RecoveryInspection, Code> {
        self.journal.inspect_recovery(operation)
    }
}
impl Journal {
    fn inspect_recovery(&self, operation: &RequestId) -> Result<RecoveryInspection, Code> {
        // Check membership BEFORE deriving/opening any path. Live operations and
        // syntactically valid but unlisted IDs cannot expand the startup catalog.
        let record = self
            .prior_recovery
            .iter()
            .find(|r| &r.operation_id == operation)
            .ok_or(Code::Denied)?;
        let prior = self.prior_intents.get(operation).ok_or(Code::Denied)?;
        let s = &prior.scope;
        let p = &prior.prepared;
        if s.schema != 1
            || &s.operation != operation
            || s.document != record.document_id
            || s.source_hash != record.source_hash
            || s.source_bytes != record.source_bytes
        {
            return Err(Code::Denied);
        }
        if s.source_bytes > MAX_SOURCE_BYTES {
            return Err(Code::TooLarge);
        }
        admit_source_path(&prior.path)?;
        let kind = if p.create {
            "create-intent.json"
        } else {
            "intent.json"
        };
        let (artifact, encoded) = self.read(s, kind)?;
        // Includes held file identity, security, hash and serialized byte size
        // captured at startup. A new valid-looking intent cannot redirect us.
        if artifact != p.intent {
            return Err(Code::Conflict);
        }
        let (payload_kind, backup, external) = if p.create {
            let i: CreateIntent =
                serde_json::from_slice(&encoded).map_err(|_| Code::InvalidInput)?;
            if i.scope != *s || i.path != prior.path || i.payload != p.payload || p.backup.is_some()
            {
                return Err(Code::Denied);
            }
            ("create-payload.bin", None, None)
        } else {
            let i: Intent = serde_json::from_slice(&encoded).map_err(|_| Code::InvalidInput)?;
            if i.scope != *s
                || i.path != prior.path
                || i.payload != p.payload
                || Some(i.backup.clone()) != p.backup
            {
                return Err(Code::Denied);
            }
            if i.external.bytes.len() > MAX_SOURCE_BYTES || i.backup.size > MAX_SOURCE_BYTES {
                return Err(Code::TooLarge);
            }
            if !i.external.ordinary() {
                return Err(Code::UnsupportedPath);
            }
            let (actual, bytes) = self.read_capped(s, "backup.bin", MAX_SOURCE_BYTES)?;
            if actual != i.backup || bytes != i.external.bytes {
                return Err(Code::Conflict);
            }
            ("payload.bin", Some(bytes), Some(i.external))
        };
        if p.payload.size > MAX_SOURCE_BYTES {
            return Err(Code::TooLarge);
        }
        let (actual, payload) = self.read_capped(s, payload_kind, MAX_SOURCE_BYTES)?;
        if actual != p.payload
            || payload.len() != s.source_bytes
            || digest(&payload) != s.source_hash
        {
            return Err(Code::Conflict);
        }
        // Revalidate previously verified historical receipts; never upgrade an
        // unknown catalog entry or release its admission block while inspecting.
        let reference = if record.phase == "written-receipt" {
            Some(self.verify_historical_receipt(s, p, &prior.path)?)
        } else {
            external
        };
        let current = inspect_current_target(&prior.path, reference.as_ref());
        self.pins.check()?;
        Ok(RecoveryInspection {
            prior_record: record.clone(),
            scope: RecoveryScope {
                schema: s.schema,
                operation_id: s.operation.clone(),
                session: s.session.clone(),
                incarnation: s.incarnation.clone(),
                document_id: s.document.clone(),
                captured_version: s.version.clone(),
                source_hash: s.source_hash.clone(),
                source_bytes: s.source_bytes,
            },
            native_path: prior.path.clone(),
            payload,
            backup,
            current,
        })
    }
    fn open_local(storage: &Path) -> Result<Self, Code> {
        // Existing host-selected parent only. Never create arbitrary ancestors.
        let _parent = Pins::open(storage)?;
        let root = storage.join("cpp-recovery-v1");
        match std::fs::create_dir(&root) {
            Ok(()) => {}
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(e) => return io::<Self>(Err(e)),
        }
        let pins = Pins::open(&root)?;
        // Cooperative single-host lease; share0 excludes another cooperating
        // host. File is never truncated and its held identity is checked.
        let mut lock = io(OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .share_mode(0)
            .custom_flags(REPARSE | WRITE_THROUGH)
            .open(root.join("host.lock")))?;
        let (_, bytes) = Self::observe(&mut lock, 1)?;
        if !bytes.is_empty() {
            return Err(Code::Conflict);
        }
        let mut journal = Self {
            root,
            pins,
            _host_lock: lock,
            prior_recovery: vec![],
            prior_intents: std::collections::HashMap::new(),
            reservations: std::sync::Mutex::new(std::collections::HashMap::new()),
            file_limit: MAX_JOURNAL_FILES,
            byte_limit: MAX_JOURNAL_BYTES,
        };
        journal.check_quota(0, 0)?;
        let (records, evidence) = journal.scan_recovery_evidence()?;
        journal.prior_recovery = records;
        journal.prior_intents = evidence;
        Ok(journal)
    }
    fn admit_new_write(&self) -> Result<(), Code> {
        if self
            .prior_recovery
            .iter()
            .any(|r| r.phase == "recovery-required")
        {
            return Err(Code::Unavailable);
        }
        if !self
            .reservations
            .lock()
            .map_err(|_| Code::Unavailable)?
            .is_empty()
        {
            return Err(Code::Unavailable);
        }
        self.check_quota(0, 0)
    }
    fn check_quota(&self, additional: u64, additional_files: usize) -> Result<(), Code> {
        self.pins.check()?;
        let mut count = additional_files;
        let mut total = additional;
        for budget in self
            .reservations
            .lock()
            .map_err(|_| Code::Unavailable)?
            .values()
        {
            count = count.checked_add(budget.files).ok_or(Code::TooLarge)?;
            total = total.checked_add(budget.bytes).ok_or(Code::TooLarge)?;
        }
        for entry in io(std::fs::read_dir(&self.root))? {
            let entry = io(entry)?;
            let meta = io(entry.path().symlink_metadata())?;
            if !meta.is_file() || meta.file_attributes() & 0x400 != 0 {
                return Err(Code::UnsupportedPath);
            }
            count += 1;
            total = total.checked_add(meta.len()).ok_or(Code::TooLarge)?;
            if count > self.file_limit || total > self.byte_limit {
                return Err(Code::TooLarge);
            }
        }
        Ok(())
    }
    fn reserve_budget(&self, scope: &Scope) -> Result<(), Code> {
        self.admit_new_write()?;
        // Both operation kinds publish exactly five bounded artifacts. Reserve
        // worst-case serialization bytes, including all post-effect receipts,
        // BEFORE the first artifact and before any target mutation/create.
        let bytes = 5 * MAX_RECORD as u64;
        self.check_quota(bytes, 5)?;
        let mut reservations = self.reservations.lock().map_err(|_| Code::Unavailable)?;
        if !reservations.is_empty() {
            return Err(Code::Unavailable);
        }
        reservations.insert(scope.operation.clone(), Budget { files: 5, bytes });
        Ok(())
    }
    pub(crate) fn finish_verified(&self, scope: &Scope) -> Result<(), Code> {
        // Native writer calls only after final held-target verification or
        // status-only recovery of this exact receipt. Failure/Unknown never
        // releases live admission just because a receipt file exists.
        self.reservations
            .lock()
            .map_err(|_| Code::Unavailable)?
            .remove(&scope.operation);
        Ok(())
    }
    pub(crate) fn check_domain(&self, target: &HeldTarget) -> Result<(), Code> {
        self.pins.check()?;
        target.pins.check()?;
        Ok(())
    }
    fn path(&self, scope: &Scope, kind: &str) -> Result<PathBuf, Code> {
        if scope.schema != 1 || !valid_artifact_kind(kind) {
            return Err(Code::InvalidInput);
        }
        // operation is a native minted opaque RequestId, never arbitrary path.
        Ok(self
            .root
            .join(format!("{}.{}", scope.operation.as_str(), kind)))
    }
    fn observe(file: &mut File, cap: usize) -> Result<(Artifact, Vec<u8>), Code> {
        ntfs(file)?;
        let id = identity(file)?;
        let basic: Basic = query(file, 0)?;
        let standard: Standard = query(file, 1)?;
        if basic.attributes & BAD != 0
            || standard.links != 1
            || standard.delete_pending != 0
            || !streams(file)?
        {
            return Err(Code::UnsupportedPath);
        }
        let security = security(file)?;
        let bytes = read_bytes(file, cap)?;
        if id != identity(file)? || security != self::security(file)? {
            return Err(Code::Conflict);
        }
        Ok((
            Artifact {
                id,
                security,
                hash: digest(&bytes),
                size: bytes.len(),
            },
            bytes,
        ))
    }
    fn create(&self, scope: &Scope, kind: &str, bytes: &[u8]) -> Result<Artifact, Code> {
        if bytes.len() > MAX_RECORD {
            return Err(Code::TooLarge);
        }
        self.check_quota(0, 0)?;
        {
            let mut reservations = self.reservations.lock().map_err(|_| Code::Unavailable)?;
            let budget = reservations
                .get_mut(&scope.operation)
                .ok_or(Code::Unavailable)?;
            if budget.files == 0 || budget.bytes < bytes.len() as u64 {
                return Err(Code::TooLarge);
            }
            budget.files -= 1;
            budget.bytes -= bytes.len() as u64;
        }
        let path = self.path(scope, kind)?;
        // CREATE_NEW only; collision/denial is a stop, no suffix/overwrite retry.
        // Inherited ACL is ordinary app-local storage, not a security boundary
        // against another process with the same Windows user's authority.
        let mut file = io(OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .share_mode(0)
            .custom_flags(REPARSE | WRITE_THROUGH)
            .open(&path))?;
        io(file.write_all(bytes))?;
        io(file.sync_all())?;
        let (artifact, actual) = Self::observe(&mut file, MAX_RECORD)?;
        if actual != bytes {
            return Err(Code::Conflict);
        }
        self.pins.check()?;
        Ok(artifact)
    }
    fn read(&self, scope: &Scope, kind: &str) -> Result<(Artifact, Vec<u8>), Code> {
        self.read_capped(scope, kind, MAX_RECORD)
    }
    fn read_capped(
        &self,
        scope: &Scope,
        kind: &str,
        cap: usize,
    ) -> Result<(Artifact, Vec<u8>), Code> {
        self.pins.check()?;
        let mut file = io(OpenOptions::new()
            .read(true)
            .share_mode(0)
            .custom_flags(REPARSE)
            .open(self.path(scope, kind)?))?;
        let standard: Standard = query(&file, 1)?;
        if standard.eof < 0 || standard.eof as u64 > cap as u64 {
            return Err(Code::TooLarge);
        }
        let result = Self::observe(&mut file, cap)?;
        self.pins.check()?;
        Ok(result)
    }
    pub(crate) fn prepare(
        &self,
        scope: &Scope,
        path: &Path,
        external: &Revision,
        new: &[u8],
    ) -> Result<Prepared, Code> {
        if new.len() != scope.source_bytes
            || digest(new) != scope.source_hash
            || !external.ordinary()
        {
            return Err(Code::InvalidInput);
        }
        self.reserve_budget(scope)?;
        // Backup actual E bytes, NOT stale editor baseline.
        let backup = self.create(scope, "backup.bin", &external.bytes)?;
        let payload = self.create(scope, "payload.bin", new)?;
        let bytes = serde_json::to_vec(&Intent {
            scope: scope.clone(),
            path: path.into(),
            external: external.clone(),
            backup: backup.clone(),
            payload: payload.clone(),
        })
        .map_err(|_| Code::InvalidInput)?;
        let intent = self.create(scope, "intent.json", &bytes)?;
        Ok(Prepared {
            intent,
            backup: Some(backup),
            payload,
            create: false,
        })
    }
    pub(crate) fn mark_may_write(&self, scope: &Scope, prepared: &Prepared) -> Result<(), Code> {
        let bytes = serde_json::to_vec(&Marker {
            scope: scope.clone(),
            intent_hash: prepared.intent.hash.clone(),
            kind: "may-have-written".into(),
            after: None,
        })
        .map_err(|_| Code::InvalidInput)?;
        self.create(scope, "may-write.json", &bytes)?;
        Ok(())
    }
    pub(crate) fn record_written(
        &self,
        scope: &Scope,
        prepared: &Prepared,
        after: &Revision,
    ) -> Result<(), Code> {
        let bytes = serde_json::to_vec(&Marker {
            scope: scope.clone(),
            intent_hash: prepared.intent.hash.clone(),
            kind: "verified-held-write".into(),
            after: Some(after.clone()),
        })
        .map_err(|_| Code::InvalidInput)?;
        self.create(scope, "written.json", &bytes)?;
        Ok(())
    }
    pub(crate) fn verify_written_selection(
        &self,
        scope: &Scope,
        prepared: &Prepared,
        target_path: &Path,
    ) -> Result<windows_read::Selection, Code> {
        let (target, after) = self.verify_written_held(scope, prepared, target_path)?;
        target.selection(&after)
    }
    fn verify_written_held(
        &self,
        scope: &Scope,
        prepared: &Prepared,
        target_path: &Path,
    ) -> Result<(HeldTarget, Revision), Code> {
        if prepared.create {
            return self.verify_created(scope, prepared, target_path);
        }
        let (artifact, bytes) = self.read(scope, "intent.json")?;
        if artifact != prepared.intent {
            return Err(Code::Conflict);
        }
        let intent: Intent = serde_json::from_slice(&bytes).map_err(|_| Code::InvalidInput)?;
        if intent.scope != *scope
            || intent.path != target_path
            || Some(intent.backup.clone()) != prepared.backup
            || intent.payload != prepared.payload
        {
            return Err(Code::Denied);
        }
        let (backup, external) = self.read(scope, "backup.bin")?;
        let (payload, next) = self.read(scope, "payload.bin")?;
        if backup != intent.backup
            || payload != intent.payload
            || external != intent.external.bytes
            || next.len() != scope.source_bytes
            || digest(&next) != scope.source_hash
        {
            return Err(Code::Conflict);
        }
        let (_, marker_bytes) = self.read(scope, "may-write.json")?;
        let marker: Marker =
            serde_json::from_slice(&marker_bytes).map_err(|_| Code::InvalidInput)?;
        if marker.scope != *scope
            || marker.intent_hash != artifact.hash
            || marker.kind != "may-have-written"
            || marker.after.is_some()
        {
            return Err(Code::Denied);
        }
        let (_, receipt_bytes) = self.read(scope, "written.json")?;
        let receipt: Marker =
            serde_json::from_slice(&receipt_bytes).map_err(|_| Code::InvalidInput)?;
        if receipt.scope != *scope
            || receipt.intent_hash != artifact.hash
            || receipt.kind != "verified-held-write"
        {
            return Err(Code::Denied);
        }
        let after = receipt.after.ok_or(Code::Conflict)?;
        if !after.ordinary() || !after.same_object_metadata(&intent.external) || after.bytes != next
        {
            return Err(Code::Conflict);
        }
        // A byte-equal target alone is NEVER a receipt. All durable scope and
        // artifact evidence above must verify first, then current namespace.
        let mut target = HeldTarget::open(target_path)?;
        self.check_domain(&target)?;
        target.recheck(&after)?;
        Ok((target, after))
    }
}
pub(crate) struct CreateNamespace {
    path: PathBuf,
    pins: Pins,
}
impl CreateNamespace {
    pub(crate) fn open(path: &Path) -> Result<Self, Code> {
        admit_source_path(path)?;
        Ok(Self {
            path: path.into(),
            pins: Pins::open(path.parent().ok_or(Code::UnsupportedPath)?)?,
        })
    }
    pub(crate) fn check_selected_parent(
        &self,
        expected: &windows_read::Identity,
    ) -> Result<(), Code> {
        self.pins.check()?;
        // Parent entry timestamps/size change when an unrelated sibling or the
        // selected target appears. Compare directory object identity, while the
        // full pinned chain still checks identities/security/attributes.
        if !windows_read::capture_parent_identity(&self.path)?.same_object(expected) {
            return Err(Code::Conflict);
        }
        Ok(())
    }
    pub(crate) fn check_absent(&self) -> Result<(), Code> {
        self.pins.check()?;
        match OpenOptions::new()
            .access_mode(0)
            .share_mode(7)
            .custom_flags(REPARSE)
            .open(&self.path)
        {
            Err(e) if e.raw_os_error() == Some(2) => {}
            Err(e) => return io::<()>(Err(e)),
            Ok(_) => return Err(Code::Conflict),
        }
        self.pins.check()
    }
}
impl HeldTarget {
    pub(crate) fn probe_existing(path: &Path) -> Result<Option<Self>, Code> {
        admit_source_path(path)?;
        let pins = Pins::open(path.parent().ok_or(Code::UnsupportedPath)?)?;
        let file = match OpenOptions::new()
            .read(true)
            .write(true)
            .share_mode(0)
            .custom_flags(REPARSE | WRITE_THROUGH)
            .open(path)
        {
            Ok(file) => file,
            Err(e) if e.raw_os_error() == Some(2) => return Ok(None),
            Err(e) => return io::<Option<Self>>(Err(e)),
        };
        ntfs(&file)?;
        Ok(Some(Self {
            path: path.into(),
            file,
            pins,
        }))
    }
    pub(crate) fn create_new(namespace: CreateNamespace) -> Result<Self, Code> {
        namespace.check_absent()?;
        // One CREATE_NEW syscall, no overwrite, deletion, fallback or retry.
        let file = io(OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .share_mode(0)
            .custom_flags(REPARSE | WRITE_THROUGH)
            .open(&namespace.path))?;
        ntfs(&file)?;
        Ok(Self {
            path: namespace.path,
            file,
            pins: namespace.pins,
        })
    }
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct CreateIntent {
    scope: Scope,
    path: PathBuf,
    parents: Vec<Parent>,
    payload: Artifact,
}
impl Journal {
    pub(crate) fn check_create_domain(&self, n: &CreateNamespace) -> Result<(), Code> {
        self.pins.check()?;
        n.pins.check()?;
        Ok(())
    }
    pub(crate) fn persist_created_namespace(&self, t: &HeldTarget) -> Result<(), Code> {
        self.check_domain(t)?;
        // File sync and namespace recheck are real operations. We explicitly do
        // NOT promise a parent-directory or cross-file power-loss transaction.
        io(t.file.sync_all())?;
        t.check_namespace()
    }
    pub(crate) fn prepare_create(
        &self,
        s: &Scope,
        n: &CreateNamespace,
        b: &[u8],
    ) -> Result<Prepared, Code> {
        if b.len() != s.source_bytes || digest(b) != s.source_hash {
            return Err(Code::InvalidInput);
        }
        self.reserve_budget(s)?;
        let payload = self.create(s, "create-payload.bin", b)?;
        let bytes = serde_json::to_vec(&CreateIntent {
            scope: s.clone(),
            path: n.path.clone(),
            parents: n.pins.facts.clone(),
            payload: payload.clone(),
        })
        .map_err(|_| Code::InvalidInput)?;
        let intent = self.create(s, "create-intent.json", &bytes)?;
        Ok(Prepared {
            intent,
            backup: None,
            payload,
            create: true,
        })
    }
    fn create_marker(
        &self,
        s: &Scope,
        p: &Prepared,
        file: &str,
        kind: &str,
        after: Option<Revision>,
    ) -> Result<(), Code> {
        if !p.create || p.backup.is_some() {
            return Err(Code::Denied);
        }
        let bytes = serde_json::to_vec(&Marker {
            scope: s.clone(),
            intent_hash: p.intent.hash.clone(),
            kind: kind.into(),
            after,
        })
        .map_err(|_| Code::InvalidInput)?;
        self.create(s, file, &bytes)?;
        Ok(())
    }
    pub(crate) fn mark_create_may_write(&self, s: &Scope, p: &Prepared) -> Result<(), Code> {
        self.create_marker(s, p, "create-may-write.json", "may-create", None)
    }
    pub(crate) fn record_created(&self, s: &Scope, p: &Prepared, r: &Revision) -> Result<(), Code> {
        self.create_marker(s, p, "created.json", "held-created", Some(r.clone()))
    }
    pub(crate) fn record_create_written(
        &self,
        s: &Scope,
        p: &Prepared,
        r: &Revision,
    ) -> Result<(), Code> {
        self.create_marker(
            s,
            p,
            "create-written.json",
            "verified-created-write",
            Some(r.clone()),
        )?;
        Ok(())
    }
    fn read_create_marker(
        &self,
        s: &Scope,
        p: &Prepared,
        file: &str,
        kind: &str,
    ) -> Result<Marker, Code> {
        let (_, bytes) = self.read(s, file)?;
        let m: Marker = serde_json::from_slice(&bytes).map_err(|_| Code::InvalidInput)?;
        if m.scope != *s || m.intent_hash != p.intent.hash || m.kind != kind {
            return Err(Code::Denied);
        }
        Ok(m)
    }
    fn verify_created(
        &self,
        s: &Scope,
        p: &Prepared,
        path: &Path,
    ) -> Result<(HeldTarget, Revision), Code> {
        if p.backup.is_some() {
            return Err(Code::Denied);
        }
        let (a, bytes) = self.read(s, "create-intent.json")?;
        let i: CreateIntent = serde_json::from_slice(&bytes).map_err(|_| Code::InvalidInput)?;
        if a != p.intent || i.scope != *s || i.path != path || i.payload != p.payload {
            return Err(Code::Denied);
        }
        let (payload, next) = self.read(s, "create-payload.bin")?;
        if payload != p.payload || next.len() != s.source_bytes || digest(&next) != s.source_hash {
            return Err(Code::Conflict);
        }
        if self
            .read_create_marker(s, p, "create-may-write.json", "may-create")?
            .after
            .is_some()
        {
            return Err(Code::Denied);
        }
        let created = self
            .read_create_marker(s, p, "created.json", "held-created")?
            .after
            .ok_or(Code::Conflict)?;
        let after = self
            .read_create_marker(s, p, "create-written.json", "verified-created-write")?
            .after
            .ok_or(Code::Conflict)?;
        if !created.ordinary()
            || !created.bytes.is_empty()
            || created.parents != i.parents
            || !after.ordinary()
            || !after.same_object_metadata(&created)
            || after.bytes != next
        {
            return Err(Code::Conflict);
        }
        let mut t = HeldTarget::open(path)?;
        self.check_domain(&t)?;
        t.recheck(&after)?;
        Ok((t, after))
    }
}
