//! Real read-only Windows implementation. No write/create/truncate/rename APIs.
use crate::types::{Code, MAX_SOURCE_BYTES};
use sha2::{Digest, Sha256};
use std::{
    ffi::c_void,
    fs::{File, OpenOptions},
    io::Read,
    os::windows::{ffi::OsStrExt, fs::OpenOptionsExt, io::AsRawHandle},
    path::{Path, PathBuf},
    sync::atomic::{AtomicBool, Ordering},
};

const SHARE_READ: u32 = 1;
const SHARE_WRITE: u32 = 2;
const BACKUP_SEMANTICS: u32 = 0x02000000;
const OPEN_REPARSE_POINT: u32 = 0x00200000;
const DIRECTORY: u32 = 0x10;
const REPARSE_POINT: u32 = 0x400;
const READ_ATTRIBUTES: u32 = 0x80;

#[repr(C)]
#[derive(Default, Debug, Clone, Copy, PartialEq, Eq)]
struct FileTime {
    low: u32,
    high: u32,
}
#[repr(C)]
#[derive(Default, Debug, Clone, Copy)]
struct FileInfo {
    attributes: u32,
    creation: FileTime,
    access: FileTime,
    write: FileTime,
    volume: u32,
    size_high: u32,
    size_low: u32,
    links: u32,
    index_high: u32,
    index_low: u32,
}
#[link(name = "kernel32")]
extern "system" {
    fn GetFileInformationByHandle(file: *mut c_void, info: *mut FileInfo) -> i32;
    fn GetFileType(file: *mut c_void) -> u32;
    fn GetDriveTypeW(root: *const u16) -> u32;
}
#[link(name = "bcrypt")]
extern "system" {
    fn BCryptGenRandom(provider: *mut c_void, buffer: *mut u8, count: u32, flags: u32) -> i32;
}

pub(crate) fn random_hex() -> Result<String, Code> {
    let mut bytes = [0u8; 16];
    // Buffer is valid for 16 writable bytes; NULL provider required for flag 2.
    let status = unsafe { BCryptGenRandom(std::ptr::null_mut(), bytes.as_mut_ptr(), 16, 2) };
    if status < 0 {
        return Err(Code::Unavailable);
    }
    Ok(bytes.iter().map(|b| format!("{b:02x}")).collect())
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Identity {
    volume: u32,
    index: u64,
    size: u64,
    write: FileTime,
}
impl Identity {
    pub(crate) fn same_object(&self, other: &Self) -> bool {
        self.volume == other.volume && self.index == other.index
    }
}
fn info(file: &File) -> Result<(FileInfo, Identity), Code> {
    let mut raw = FileInfo::default();
    // Borrowed live std::File handle and correctly sized C layout output.
    if unsafe { GetFileType(file.as_raw_handle()) } != 1 {
        return Err(Code::UnsupportedPath);
    }
    if unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut raw) } == 0 {
        return Err(Code::IOFailure);
    }
    let id = Identity {
        volume: raw.volume,
        index: ((raw.index_high as u64) << 32) | raw.index_low as u64,
        size: ((raw.size_high as u64) << 32) | raw.size_low as u64,
        write: raw.write,
    };
    if raw.attributes & REPARSE_POINT != 0 {
        return Err(Code::UnsupportedPath);
    }
    Ok((raw, id))
}
fn io_code(error: std::io::Error) -> Code {
    match error.raw_os_error() {
        Some(32) | Some(33) => Code::Busy,
        Some(5) => Code::Denied,
        _ => Code::IOFailure,
    }
}

// Conservative first read surface: ordinary local drive-absolute Unicode paths.
// Reject normalization aliases before ANY OS call. Display names are not authority.
pub(crate) fn validate_path(path: &Path) -> Result<(), Code> {
    let s = path.to_str().ok_or(Code::UnsupportedPath)?;
    let b = s.as_bytes();
    if b.len() < 4
        || !b[0].is_ascii_alphabetic()
        || b[1] != b':'
        || b[2] != b'\\'
        || s.contains('/')
        || s[3..].contains(':')
        || s.encode_utf16().count() > 240
    {
        return Err(Code::UnsupportedPath);
    }
    let components: Vec<_> = s[3..].split('\\').collect();
    if components.len() > 32 {
        return Err(Code::UnsupportedPath);
    }
    for component in components {
        let upper = component
            .split('.')
            .next()
            .unwrap_or("")
            .trim_end_matches(' ')
            .to_ascii_uppercase();
        // Windows also treats superscript 1/2/3 as DOS device digits. Refuse
        // all numeric COM/LPT stems conservatively, BEFORE opening any handle.
        let numeric_device = upper
            .strip_prefix("COM")
            .or_else(|| upper.strip_prefix("LPT"))
            .is_some_and(|suffix| {
                !suffix.is_empty()
                    && suffix
                        .chars()
                        .all(|c| c.is_ascii_digit() || matches!(c, '¹' | '²' | '³'))
            });
        if component.is_empty()
            || component == "."
            || component == ".."
            || component.ends_with(['.', ' '])
            || component.chars().any(|c| c < ' ' || "<>\"|?*".contains(c))
            || matches!(
                upper.as_str(),
                "CON" | "PRN" | "AUX" | "NUL" | "CONIN$" | "CONOUT$"
            )
            || numeric_device
        {
            return Err(Code::UnsupportedPath);
        }
    }
    Ok(())
}

struct ParentPins {
    _handles: Vec<File>,
    identity: Identity,
}
fn pin_parent(path: &Path) -> Result<ParentPins, Code> {
    validate_path(path)?;
    let s = path.to_str().ok_or(Code::UnsupportedPath)?;
    let root = PathBuf::from(&s[..3]);
    let wide: Vec<_> = root.as_os_str().encode_wide().chain(Some(0)).collect();
    if unsafe { GetDriveTypeW(wide.as_ptr()) } != 3 {
        return Err(Code::UnsupportedPath);
    }
    let parent = path.parent().ok_or(Code::UnsupportedPath)?;
    let mut paths: Vec<_> = parent.ancestors().map(Path::to_path_buf).collect();
    paths.reverse();
    let mut handles = Vec::new();
    let mut last = None;
    for part in paths {
        // Metadata-only parent handle, not directory-list/read-data permission.
        let handle = OpenOptions::new()
            .read(true)
            .access_mode(READ_ATTRIBUTES)
            .share_mode(SHARE_READ | SHARE_WRITE)
            .custom_flags(BACKUP_SEMANTICS | OPEN_REPARSE_POINT)
            .open(part)
            .map_err(io_code)?;
        let (raw, id) = info(&handle)?;
        if raw.attributes & DIRECTORY == 0 {
            return Err(Code::UnsupportedPath);
        }
        handles.push(handle);
        last = Some(id);
    }
    Ok(ParentPins {
        _handles: handles,
        identity: last.ok_or(Code::UnsupportedPath)?,
    })
}

#[derive(Clone)]
pub(crate) struct Selection {
    // Native-only evidence, never Serialize. A later writer MUST revalidate;
    // these captured identities are NOT a conditional replacement lock.
    pub(crate) path: PathBuf,
    pub(crate) parent: Identity, // retained evidence; intentionally no writer consumes it yet
    pub(crate) file: Option<Identity>,
    pub(crate) sha256: Option<[u8; 32]>, // retained evidence; no synthetic write receipt
    pub(crate) bytes: Vec<u8>,
    // Optional stricter writer evidence from this original read grant. Missing
    // evidence denies Save; legacy 64-bit identity is never upgraded by guess.
    pub(crate) writer_revision: Option<crate::windows_write::Revision>,
}

pub(crate) fn read_selected(
    path: PathBuf,
    allow_absent: bool,
    cancel: &AtomicBool,
) -> Result<Selection, Code> {
    if cancel.load(Ordering::Acquire) {
        return Err(Code::Revoked);
    }
    let pins = pin_parent(&path)?;
    let opened = OpenOptions::new()
        .read(true)
        .share_mode(SHARE_READ)
        .custom_flags(OPEN_REPARSE_POINT)
        .open(&path);
    let mut file = match opened {
        Ok(file) => file,
        Err(error) if allow_absent && error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(Selection {
                path,
                parent: pins.identity,
                file: None,
                sha256: None,
                bytes: Vec::new(),
                writer_revision: None,
            });
        }
        Err(error) => return Err(io_code(error)),
    };
    let (raw, before) = info(&file)?;
    if raw.attributes & DIRECTORY != 0 || raw.links != 1 {
        return Err(Code::UnsupportedPath);
    }
    if before.size > MAX_SOURCE_BYTES as u64 {
        return Err(Code::TooLarge);
    }
    let mut bytes = Vec::with_capacity(before.size as usize);
    let mut chunk = [0u8; 8192];
    loop {
        if cancel.load(Ordering::Acquire) {
            return Err(Code::Revoked);
        }
        let count = file.read(&mut chunk).map_err(io_code)?;
        if count == 0 {
            break;
        }
        if bytes.len() + count > MAX_SOURCE_BYTES {
            return Err(Code::TooLarge);
        }
        bytes.extend_from_slice(&chunk[..count]);
    }
    let (_, after) = info(&file)?;
    if before != after || before.size != bytes.len() as u64 {
        return Err(Code::Conflict);
    }
    let sha256 = Sha256::digest(&bytes).into();
    // Stricter Save evidence is optional: no Open/ChooseTarget fallback to a
    // fake writer proof. Only .cpp/.cc/.cxx Open grants are inspected here.
    let writer_revision = if !allow_absent && crate::windows_write::admit_source_path(&path).is_ok()
    {
        crate::windows_write::capture_read_grant(&path, &file)
            .ok()
            .filter(|r| r.bytes == bytes)
    } else {
        None
    };
    Ok(Selection {
        path,
        parent: pins.identity,
        file: Some(before),
        sha256: Some(sha256),
        bytes,
        writer_revision,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn dos_superscript_aliases_are_rejected_before_any_os_call() {
        for value in [
            r"C:\safe\COM¹.cpp",
            r"C:\safe\LPT².h",
            r"C:\safe\COM0.cpp",
            r"C:\safe\COM12.h",
        ] {
            assert_eq!(
                validate_path(Path::new(value)),
                Err(Code::UnsupportedPath),
                "{value}"
            );
        }
    }
    #[test]
    fn lexical_paths_reject_devices_network_ads_and_aliases() {
        for value in [
            "relative.cpp",
            r"\\server\x.cpp",
            r"\\?\C:\x.cpp",
            r"C:\x.cpp:stream",
            r"C:\..\x.cpp",
            r"C:\x.\y.cpp",
            r"C:\NUL.cpp",
            r"C:\COM1",
            r"C:\a\\b.cpp",
        ] {
            assert_eq!(
                validate_path(Path::new(value)),
                Err(Code::UnsupportedPath),
                "{value}"
            );
        }
    }
}

// Native read evidence helpers needed by the inherited held writer; not grants
// synthesized from frontend metadata. SAME real handle/pinned parent functions.
pub(crate) fn writer_identity(file: &File) -> Result<Identity, Code> {
    info(file).map(|(_, id)| id)
}
pub(crate) fn capture_parent_identity(path: &Path) -> Result<Identity, Code> {
    Ok(pin_parent(path)?.identity)
}
