//! Actual CREATE_NEW path in the SAME writer/Journal, never a second owner.
//! Uses the host-resolved local-cooperative journal; no atomic overwrite/retry.
use crate::windows_write::{self, CreateNamespace, HeldTarget, Journal, Prepared, Revision, Scope};
use crate::{Code, MAX_SOURCE_BYTES};
use std::sync::atomic::{AtomicBool, Ordering};

pub(crate) enum CreatedEffect {
    Existing(Revision),
    Written(Prepared, crate::windows_read::Selection),
}
/// uncertain is set BEFORE marker publication and BEFORE CREATE_NEW syscall.
/// Errors beyond it remain Unknown; never delete a partial file or retry.
pub(crate) fn execute_create(
    scope: &Scope,
    path: &std::path::Path,
    selected_parent: &crate::windows_read::Identity,
    bytes: &[u8],
    cancel: &AtomicBool,
    journal: &Journal,
    artifacts: &mut Option<Prepared>,
    uncertain: &mut bool,
) -> Result<CreatedEffect, Code> {
    if bytes.len() > MAX_SOURCE_BYTES
        || bytes.len() != scope.source_bytes
        || windows_write::digest(bytes) != scope.source_hash
    {
        return Err(Code::InvalidInput);
    }
    if cancel.load(Ordering::Acquire) {
        return Err(Code::Revoked);
    }
    let namespace = CreateNamespace::open(path)?;
    namespace.check_selected_parent(selected_parent)?;
    // An existing file is an EXPLICIT conflict, never CREATE_ALWAYS/truncate.
    if let Some(mut existing) = HeldTarget::probe_existing(path)? {
        let external = existing.snapshot()?;
        existing.check_namespace()?;
        if !external.ordinary() {
            return Err(Code::UnsupportedPath);
        }
        return Ok(CreatedEffect::Existing(external));
    }
    journal.check_create_domain(&namespace)?;
    namespace.check_absent()?;
    let prepared = journal.prepare_create(scope, &namespace, bytes)?;
    *artifacts = Some(prepared.clone());
    namespace.check_absent()?;
    journal.check_create_domain(&namespace)?;
    if cancel.load(Ordering::Acquire) {
        return Err(Code::Revoked);
    }
    *uncertain = true;
    journal.mark_create_may_write(scope, &prepared)?;
    namespace.check_absent()?;
    // One syscall attempt, create_new(true) => CREATE_NEW; an appearance race
    // stops Unknown after may-write, NEVER retries/overwrites the winning file.
    let mut target = HeldTarget::create_new(namespace)?;
    let created = target.snapshot()?;
    target.check_namespace()?;
    if !created.ordinary() || !created.bytes.is_empty() {
        return Err(Code::Conflict);
    }
    journal.record_created(scope, &prepared, &created)?;
    target.recheck(&created)?;
    target.update(bytes, cancel)?;
    let after = target.snapshot()?;
    target.check_namespace()?;
    if !after.same_object_metadata(&created) || !after.ordinary() || after.bytes != bytes {
        return Err(Code::Conflict);
    }
    // Flush the actual file and recheck its namespace. This is not a promise of
    // directory-entry/cross-file transaction durability under sudden power loss.
    journal.persist_created_namespace(&target)?;
    target.recheck(&after)?;
    journal.record_create_written(scope, &prepared, &after)?;
    target.recheck(&after)?;
    let selection = target.selection(&after)?;
    journal.finish_verified(scope)?;
    Ok(CreatedEffect::Written(prepared, selection))
}
