//! Pure native inspection-to-wire conversion. No filesystem work, restoration,
//! grant creation, or interpretation of a historical receipt as current Saved.
use crate::windows_write::digest;
use crate::{Code, CurrentTargetObservation, RecoveryInspection, RequestId, MAX_SOURCE_BYTES};
use base64::{engine::general_purpose::STANDARD, Engine};
use serde::Serialize;

/// Output only: the input is a native RecoveryInspection, never an IPC DTO.
#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RecoveryComparison {
    schema_version: u8,
    operation_id: RequestId,
    display_name: String,
    historical_phase: HistoricalPhase,
    payload: ByteRevision,
    backup: Option<ByteRevision>,
    current: CurrentRevision,
}

#[derive(Clone, Copy, Debug, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum HistoricalPhase {
    WrittenReceipt,
    RecoveryRequired,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ByteRevision {
    source_base64: String,
    source_hash: String,
    source_bytes: usize,
}

#[derive(Clone, Debug, Serialize)]
#[serde(tag = "status", rename_all = "camelCase")]
pub enum CurrentRevision {
    Unchanged {
        #[serde(flatten)]
        revision: ByteRevision,
    },
    Changed {
        #[serde(flatten)]
        revision: ByteRevision,
    },
    Present {
        #[serde(flatten)]
        revision: ByteRevision,
    },
    Missing,
    Busy,
    Denied,
    Error {
        code: Code,
    },
}

fn lower_hex(value: &str, length: usize) -> bool {
    value.len() == length
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn valid_id(value: &str, prefix: &str) -> bool {
    value
        .strip_prefix(prefix)
        .is_some_and(|suffix| lower_hex(suffix, 32))
}

/// Shared bounded exact-byte conversion for payload, backup and current reads.
/// Expected metadata is checked before emitting any wire revision.
fn checked_source(
    bytes: &[u8],
    expected_hash: Option<&str>,
    expected_count: Option<usize>,
) -> Result<ByteRevision, Code> {
    if bytes.len() > MAX_SOURCE_BYTES
        || expected_count.is_some_and(|count| count > MAX_SOURCE_BYTES)
    {
        return Err(Code::TooLarge);
    }
    if expected_hash.is_some_and(|hash| !lower_hex(hash, 64)) {
        return Err(Code::InvalidInput);
    }
    let hash = digest(bytes);
    if expected_count.is_some_and(|count| count != bytes.len())
        || expected_hash.is_some_and(|expected| expected != hash)
    {
        return Err(Code::Conflict);
    }
    Ok(ByteRevision {
        source_base64: STANDARD.encode(bytes),
        source_hash: hash,
        source_bytes: bytes.len(),
    })
}

/// Convert already inspected historical evidence to its narrow comparison wire
/// view. This does not inspect a path or authenticate a caller. Native callers
/// must obtain the inspection from the existing startup-catalog inspector.
pub fn comparison_view(inspection: RecoveryInspection) -> Result<RecoveryComparison, Code> {
    let record = &inspection.prior_record;
    let scope = &inspection.scope;
    if scope.schema != 1
        || !valid_id(scope.operation_id.as_str(), "request_")
        || !valid_id(record.operation_id.as_str(), "request_")
        || !valid_id(scope.document_id.as_str(), "doc_")
        || !valid_id(record.document_id.as_str(), "doc_")
        || !lower_hex(&scope.session, 32)
        || !lower_hex(&scope.incarnation, 32)
        || scope
            .captured_version
            .as_ref()
            .is_some_and(|version| !valid_id(version.as_str(), "version_"))
        || record.display_name.is_empty()
        || record.display_name.encode_utf16().count() > 240
        || record
            .display_name
            .chars()
            .any(|c| c.is_control() || matches!(c, '/' | '\\' | ':'))
        || inspection
            .native_path
            .file_name()
            .and_then(|name| name.to_str())
            != Some(record.display_name.as_str())
    {
        return Err(Code::InvalidInput);
    }
    let historical_phase = match record.phase {
        "written-receipt" => HistoricalPhase::WrittenReceipt,
        "recovery-required" => HistoricalPhase::RecoveryRequired,
        _ => return Err(Code::InvalidInput),
    };
    if scope.source_bytes > MAX_SOURCE_BYTES || record.source_bytes > MAX_SOURCE_BYTES {
        return Err(Code::TooLarge);
    }
    if !lower_hex(&scope.source_hash, 64) || !lower_hex(&record.source_hash, 64) {
        return Err(Code::InvalidInput);
    }
    if scope.operation_id != record.operation_id
        || scope.document_id != record.document_id
        || scope.source_hash != record.source_hash
        || scope.source_bytes != record.source_bytes
    {
        return Err(Code::Conflict);
    }
    // None is a create intent, not an empty overwrite backup. Present is only
    // possible for an unfinished create without a historical target revision.
    if record.backup_available != inspection.backup.is_some()
        || matches!(
            &inspection.current,
            CurrentTargetObservation::Present { .. }
        ) && (inspection.backup.is_some()
            || !matches!(historical_phase, HistoricalPhase::RecoveryRequired))
        || matches!(
            &inspection.current,
            CurrentTargetObservation::Unchanged { .. } | CurrentTargetObservation::Changed { .. }
        ) && inspection.backup.is_none()
            && matches!(historical_phase, HistoricalPhase::RecoveryRequired)
    {
        return Err(Code::InvalidInput);
    }
    let payload = checked_source(
        &inspection.payload,
        Some(&scope.source_hash),
        Some(scope.source_bytes),
    )?;
    let backup = inspection
        .backup
        .as_deref()
        .map(|bytes| checked_source(bytes, None, None))
        .transpose()?;
    let current = match inspection.current {
        CurrentTargetObservation::Unchanged { bytes, hash } => {
            let reference = match historical_phase {
                HistoricalPhase::WrittenReceipt => inspection.payload.as_slice(),
                HistoricalPhase::RecoveryRequired => {
                    inspection.backup.as_deref().ok_or(Code::InvalidInput)?
                }
            };
            let revision = checked_source(&bytes, Some(&hash), None)?;
            if bytes != reference {
                return Err(Code::Conflict);
            }
            CurrentRevision::Unchanged { revision }
        }
        CurrentTargetObservation::Changed { bytes, hash } => CurrentRevision::Changed {
            revision: checked_source(&bytes, Some(&hash), None)?,
        },
        CurrentTargetObservation::Present { bytes, hash } => CurrentRevision::Present {
            revision: checked_source(&bytes, Some(&hash), None)?,
        },
        CurrentTargetObservation::Missing => CurrentRevision::Missing,
        CurrentTargetObservation::Busy => CurrentRevision::Busy,
        CurrentTargetObservation::Denied => CurrentRevision::Denied,
        CurrentTargetObservation::Error { code } => CurrentRevision::Error { code },
    };
    Ok(RecoveryComparison {
        schema_version: 1,
        operation_id: inspection.prior_record.operation_id,
        display_name: inspection.prior_record.display_name,
        historical_phase,
        payload,
        backup,
        current,
    })
}

#[cfg(test)]
#[path = "recovery_view_tests.rs"]
mod recovery_view_tests;
