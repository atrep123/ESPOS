//! Read-only historical inspection of ONE host-catalogued fresh-project journal.
//! Bootstrap/catalogue membership and caller admission belong to the host. This
//! component cannot discover operations, authenticate JSON, resume an operation,
//! register an owner, or grant access to a project. In particular intent.root
//! and intent.scope are historical, untrusted DATA, never filesystem authority.
//! Local-cooperative NTFS observations, not same-user attacker exclusion or a
//! joint power-loss transaction. No target-project files are opened here.

use crate::{
    fresh_project::FileProof,
    windows_read,
    windows_write::{self, Pins, Scope},
    Code, DocumentId, RequestId, Version, MAX_SOURCE_BYTES,
};
use serde::{Deserialize, Deserializer};
use std::{
    fs::{self, File, OpenOptions},
    os::windows::fs::{MetadataExt, OpenOptionsExt},
    path::{Path, PathBuf},
};

const RECORD_CAP: usize = 16 * 1024;
const COMPANION_CAP: usize = 64 * 1024;
const REPARSE: u32 = 0x00200000;
const ROLES: [&str; 4] = [
    "app/src/main.cpp",
    "tabos-app.json",
    "CMakeLists.txt",
    "docs/UI_BACKEND_TRACEABILITY.md",
];

/// No Deserialize, public constructor, path getter, or renderer path override.
/// Private fields ensure only the native constructor below establishes pins.
/// This wrapper does NOT itself establish catalogue membership: its constructor
/// must be called only after the host selected this operation from its trusted
/// bootstrap catalogue, including the independently catalogued operation ID.
pub(crate) struct CataloguedOperation {
    directory: PathBuf,
    operation: RequestId,
    pins: Pins,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum HistoricalPhase {
    /// Complete intent/payloads observed, optional markers absent. Absence is
    /// NOT proof that the interrupted operation had no filesystem effects.
    Prepared,
    MayWrite,
    Verified,
    Invalid,
}

#[derive(Debug)]
pub(crate) struct Inspection {
    pub(crate) phase: HistoricalPhase,
    pub(crate) invalid_code: Option<Code>,
    pub(crate) historical_scope: Option<Scope>,
    pub(crate) historical_root: Option<String>,
    /// Actual payload hashes, exposed only after ALL four roles validate.
    pub(crate) payload_proofs: Option<[FileProof; 4]>,
    /// Official currentFileProof statement: ALWAYS false. Verified describes
    /// journal evidence only, never current Saved, target contents, or a grant.
    pub(crate) current_file_proof: bool,
}

#[derive(Clone, Copy)]
enum Role {
    Source,
    Manifest,
    CMake,
    Traceability,
}
impl Role {
    const ALL: [Self; 4] = [
        Self::Source,
        Self::Manifest,
        Self::CMake,
        Self::Traceability,
    ];
    fn index(self) -> usize {
        match self {
            Self::Source => 0,
            Self::Manifest => 1,
            Self::CMake => 2,
            Self::Traceability => 3,
        }
    }
    fn cap(self) -> usize {
        match self {
            Self::Source => MAX_SOURCE_BYTES,
            _ => COMPANION_CAP,
        }
    }
}

// Closed fixed-name inventory. No arbitrary path or JSON role reaches open().
#[derive(Clone, Copy)]
enum FixedFile {
    Intent,
    MayWrite,
    Verified,
    Payload(Role),
}
impl FixedFile {
    fn name(self) -> &'static str {
        match self {
            Self::Intent => "intent.json",
            Self::MayWrite => "may-write.json",
            Self::Verified => "verified.json",
            Self::Payload(Role::Source) => "payload-0.bin",
            Self::Payload(Role::Manifest) => "payload-1.bin",
            Self::Payload(Role::CMake) => "payload-2.bin",
            Self::Payload(Role::Traceability) => "payload-3.bin",
        }
    }
    fn cap(self) -> usize {
        match self {
            Self::Payload(role) => role.cap(),
            _ => RECORD_CAP,
        }
    }
}

fn io_code(error: std::io::Error) -> Code {
    match error.raw_os_error() {
        Some(5) => Code::Denied,
        Some(32) | Some(33) => Code::Busy,
        _ => Code::IOFailure,
    }
}

/// Held read-only ordinary primary stream; no write/delete sharing. Each of the
/// four named roles uses this same strict existing NTFS snapshot helper.
struct NamedPrimary {
    file: File,
    bytes: Vec<u8>,
}
impl NamedPrimary {
    fn open(operation: &CataloguedOperation, kind: FixedFile) -> Result<Option<Self>, Code> {
        operation.pins.check()?;
        let path = operation.directory.join(kind.name());
        windows_read::validate_path(&path)?;
        // Cheap preflight denies an oversized artifact before opening its data
        // handle or allocating its contents. Repeat from the held handle below.
        match fs::symlink_metadata(&path) {
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(error) => return Err(io_code(error)),
            Ok(metadata) => {
                if metadata.file_attributes() & (0x10 | 0x400) != 0 {
                    return Err(Code::UnsupportedPath);
                }
                if metadata.len() > kind.cap() as u64 {
                    return Err(Code::TooLarge);
                }
            }
        }
        let mut file = OpenOptions::new()
            .read(true)
            .share_mode(1)
            .custom_flags(REPARSE)
            .open(path)
            .map_err(io_code)?;
        let before = file.metadata().map_err(io_code)?;
        if before.len() > kind.cap() as u64 {
            return Err(Code::TooLarge);
        }
        // Includes NTFS, single link, primary stream only, non-reparse/non-device
        // metadata, delete-pending refusal and bounded actual reads.
        let bytes = windows_write::fresh_project_snapshot(&mut file, kind.cap())?;
        let after = file.metadata().map_err(io_code)?;
        if before.len() != bytes.len() as u64
            || before.len() != after.len()
            || before.file_attributes() != after.file_attributes()
            || before.last_write_time() != after.last_write_time()
        {
            return Err(Code::Conflict);
        }
        operation.pins.check()?;
        Ok(Some(Self { file, bytes }))
    }
    fn required(operation: &CataloguedOperation, kind: FixedFile) -> Result<Self, Code> {
        Self::open(operation, kind)?.ok_or(Code::InvalidInput)
    }
    fn recheck(&mut self, cap: usize) -> Result<(), Code> {
        if self.file.metadata().map_err(io_code)?.len() > cap as u64 {
            return Err(Code::TooLarge);
        }
        if windows_write::fresh_project_snapshot(&mut self.file, cap)? != self.bytes {
            return Err(Code::Conflict);
        }
        Ok(())
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Intent {
    schema: String,
    scope: HistoricalScope,
    root: String,
    files: [Proof; 4],
}

// Match the engine's snake_case scope exactly. A custom Option deserializer
// makes the version KEY required even when its VALUE is null.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct HistoricalScope {
    schema: u8,
    operation: RequestId,
    session: String,
    incarnation: String,
    document: DocumentId,
    #[serde(deserialize_with = "required_version")]
    version: Option<Version>,
    source_hash: String,
    source_bytes: usize,
}
fn required_version<'de, D: Deserializer<'de>>(d: D) -> Result<Option<Version>, D::Error> {
    Option::<Version>::deserialize(d)
}

#[derive(Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Proof {
    role: String,
    bytes: usize,
    sha256: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct MayWrite {
    schema: String,
}
fn parse<T: serde::de::DeserializeOwned>(bytes: &[u8]) -> Result<T, Code> {
    serde_json::from_slice(bytes).map_err(|_| Code::InvalidInput)
}
fn hex(value: &str, count: usize) -> bool {
    value.len() == count
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
fn validate_proofs(proofs: &[Proof; 4]) -> Result<(), Code> {
    for role in Role::ALL {
        let proof = &proofs[role.index()];
        if proof.bytes > role.cap() {
            return Err(Code::TooLarge);
        }
        if proof.role != ROLES[role.index()] || proof.bytes == 0 || !hex(&proof.sha256, 64) {
            return Err(Code::InvalidInput);
        }
    }
    Ok(())
}

impl CataloguedOperation {
    /// Native host ONLY, after trusted catalogue membership has been checked.
    /// directory must come from that catalogue, NEVER an intent, IPC JSON,
    /// project root, role, or display string. No catalogue walk occurs here.
    pub(crate) fn from_host_catalogued_directory(
        directory: &Path,
        operation: &RequestId,
    ) -> Result<Self, Code> {
        // Validate ALL fixed paths before any directory/file handle is opened.
        for kind in [FixedFile::Intent, FixedFile::MayWrite, FixedFile::Verified] {
            windows_read::validate_path(&directory.join(kind.name()))?;
        }
        for role in Role::ALL {
            windows_read::validate_path(&directory.join(FixedFile::Payload(role).name()))?;
        }
        let pins = Pins::open(directory)?;
        pins.check()?;
        Ok(Self {
            directory: directory.to_path_buf(),
            operation: operation.clone(),
            pins,
        })
    }

    pub(crate) fn inspect(&self) -> Inspection {
        match self.inspect_inner() {
            Ok(inspection) => inspection,
            Err(code) => Inspection {
                phase: HistoricalPhase::Invalid,
                invalid_code: Some(code),
                historical_scope: None,
                historical_root: None,
                payload_proofs: None,
                current_file_proof: false,
            },
        }
    }

    fn inspect_inner(&self) -> Result<Inspection, Code> {
        self.pins.check()?;
        let mut intent_file = NamedPrimary::required(self, FixedFile::Intent)?;
        let intent: Intent = parse(&intent_file.bytes)?;
        validate_proofs(&intent.files)?;
        let scope = intent.scope;
        if scope.source_bytes > MAX_SOURCE_BYTES {
            return Err(Code::TooLarge);
        }
        if intent.schema != "espos.fresh-project-intent.v1"
            || scope.schema != 1
            || !hex(&scope.session, 32)
            || !hex(&scope.incarnation, 32)
            || !hex(&scope.source_hash, 64)
            || intent.root.is_empty()
            || intent.root.encode_utf16().count() > 240
        {
            return Err(Code::InvalidInput);
        }
        if scope.operation != self.operation
            || scope.source_bytes != intent.files[0].bytes
            || scope.source_hash != intent.files[0].sha256
        {
            return Err(Code::Conflict);
        }
        // Validate cached metadata BEFORE any payload open. Cached verified JSON
        // is never sufficient: below we hash all actual held payload snapshots.
        let mut may_write = NamedPrimary::open(self, FixedFile::MayWrite)?;
        if let Some(marker) = &may_write {
            if parse::<MayWrite>(&marker.bytes)?.schema != "espos.fresh-project-may-write.v1" {
                return Err(Code::InvalidInput);
            }
        }
        let mut verified = NamedPrimary::open(self, FixedFile::Verified)?;
        if let Some(marker) = &verified {
            let proofs: [Proof; 4] = parse(&marker.bytes)?;
            validate_proofs(&proofs)?;
            if may_write.is_none() || proofs != intent.files {
                return Err(Code::Conflict);
            }
        }
        // At most 1 MiB + 3 * 64 KiB of payload data; no whole-project quota or
        // generic directory enumeration. Keep every opened handle until done.
        let mut payloads = Vec::with_capacity(4);
        let mut proofs = Vec::with_capacity(4);
        for role in Role::ALL {
            let payload = NamedPrimary::required(self, FixedFile::Payload(role))?;
            let bytes = &payload.bytes;
            if bytes.is_empty() || bytes.contains(&0) || std::str::from_utf8(bytes).is_err() {
                return Err(Code::InvalidInput);
            }
            let hash = windows_write::digest(bytes);
            let expected = &intent.files[role.index()];
            if bytes.len() != expected.bytes || hash != expected.sha256 {
                return Err(Code::Conflict);
            }
            proofs.push(FileProof {
                role: ROLES[role.index()],
                bytes: bytes.len(),
                sha256: hash,
            });
            payloads.push(payload);
        }
        intent_file.recheck(RECORD_CAP)?;
        for marker in [&mut may_write, &mut verified].into_iter().flatten() {
            marker.recheck(RECORD_CAP)?;
        }
        for (role, payload) in Role::ALL.into_iter().zip(&mut payloads) {
            payload.recheck(role.cap())?;
        }
        // Recheck ABSENT markers too: an interrupted publisher cannot upgrade
        // phase underneath this inspection without a conflicting observation.
        for (kind, held) in [
            (FixedFile::MayWrite, &may_write),
            (FixedFile::Verified, &verified),
        ] {
            if held.is_none() && NamedPrimary::open(self, kind)?.is_some() {
                return Err(Code::Conflict);
            }
        }
        self.pins.check()?;
        Ok(Inspection {
            phase: if verified.is_some() {
                HistoricalPhase::Verified
            } else if may_write.is_some() {
                HistoricalPhase::MayWrite
            } else {
                HistoricalPhase::Prepared
            },
            invalid_code: None,
            historical_scope: Some(Scope {
                schema: scope.schema,
                operation: scope.operation,
                session: scope.session,
                incarnation: scope.incarnation,
                document: scope.document,
                version: scope.version,
                source_hash: scope.source_hash,
                source_bytes: scope.source_bytes,
            }),
            historical_root: Some(intent.root),
            payload_proofs: Some(proofs.try_into().map_err(|_| Code::InvalidInput)?),
            current_file_proof: false,
        })
    }
}

#[cfg(test)]
#[path = "fresh_project_recovery_tests.rs"]
mod tests;
