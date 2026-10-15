//! Native-only saved-app admission through the existing Host/Registry owner.
//! These capabilities are not DTOs and have no renderer dispatch route. A local
//! consumer must validate before consuming/publishing, retain the lease through
//! actual work drain, and stop on cancellation. Drop reports no build outcome.
use super::*;
pub use crate::project_snapshot::ProjectRevision;
use crate::project_snapshot::{HeldApp, Provenance};
use std::{
    path::PathBuf,
    sync::atomic::{AtomicBool, Ordering},
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SavedAppRole {
    Source,
    Manifest,
    CMake,
    Traceability,
}
impl SavedAppRole {
    fn index(self) -> usize {
        match self {
            Self::Source => 0,
            Self::Manifest => 1,
            Self::CMake => 2,
            Self::Traceability => 3,
        }
    }
    pub fn relative_name(self) -> &'static str {
        crate::fresh_project::ROLES[self.index()]
    }
}

/// Trusted native root-folder picker. Production must obtain user selection
/// natively; no caller root/path DTO, historical journal or source-ancestor use.
pub trait ProjectRootPicker {
    fn select_root(&mut self) -> Result<Option<PathBuf>, Code>;
}

/// Non-Clone work reserves the same owner's busy lifetime before any IO.
pub struct SavedAppWork {
    host: NativeHost,
    binding: Binding,
    document: DocumentId,
    version: Version,
    draft_revision: u64,
    provenance: Provenance,
    cancel: Arc<AtomicBool>,
}
/// Non-Clone immutable four-member snapshot plus held OS locks and work owner.
/// No root getter, constructor, Serialize/Deserialize, write grant or IPC route.
pub struct SavedAppLease {
    held: Option<HeldApp>,
    ownership: SavedAppWork,
}
pub struct ProjectReopenWork {
    host: NativeHost,
    binding: Binding,
    job: Option<ReadJob>,
}

impl NativeHost {
    /// Capture the current editor draft on the SAME saved native document.
    /// Correlation revision/bytes never create project authority. Capture edits
    /// cancel an existing lease but keep its owner busy until real Drop.
    pub fn capture_saved_app_draft(
        &self,
        binding: &Binding,
        document: &DocumentId,
        version: &Version,
        revision: u64,
        bytes: Vec<u8>,
    ) -> Result<(), Code> {
        if revision > 9_007_199_254_740_991 {
            return Err(Code::InvalidInput);
        }
        if bytes.len() > MAX_SOURCE_BYTES {
            return Err(Code::TooLarge);
        }
        let mut state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.authorized(&state, binding)?;
        let caller = state.registrations[index].caller.clone();
        let doc = state.registry.document(&caller, document)?;
        if doc.project.is_none() {
            return Err(Code::Unavailable);
        }
        if doc.version.as_ref() != Some(version) {
            return Err(Code::Conflict);
        }
        if let Some(old) = &doc.draft_capture {
            if revision < old.revision || (revision == old.revision && bytes != old.bytes) {
                return Err(Code::Conflict);
            }
        }
        let changed = doc
            .draft_capture
            .as_ref()
            .is_none_or(|c| c.revision != revision || c.bytes != bytes);
        let doc = state
            .registry
            .documents
            .get_mut(document)
            .ok_or(Code::Denied)?;
        if changed {
            if let Some(cancel) = &doc.project_lease {
                cancel.store(true, Ordering::Release);
            }
        }
        doc.draft_capture = Some(save_as::CapturedDraft { revision, bytes });
        Ok(())
    }

    pub fn prepare_saved_app_snapshot(
        &self,
        binding: &Binding,
        document: &DocumentId,
        version: &Version,
        draft_revision: u64,
    ) -> Result<SavedAppWork, Code> {
        let mut state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.authorized(&state, binding)?;
        let caller = state.registrations[index].caller.clone();
        state.registry.document(&caller, document)?;
        if state.registry.has_saved_app_work(&caller)
            || state
                .projects
                .values()
                .any(|r| r.owner == caller && r.pending())
            || state
                .registry
                .operations
                .values()
                .any(|e| e.owner == caller && !e.phase.is_terminal())
        {
            return Err(Code::Busy);
        }
        let doc = state.registry.document(&caller, document)?;
        if doc.version.as_ref() != Some(version) {
            return Err(Code::Conflict);
        }
        let provenance = doc.project.clone().ok_or(Code::Unavailable)?;
        Self::saved_draft(doc, version, draft_revision)?;
        let cancel = Arc::new(AtomicBool::new(false));
        state
            .registry
            .documents
            .get_mut(document)
            .ok_or(Code::Denied)?
            .project_lease = Some(cancel.clone());
        Ok(SavedAppWork {
            host: self.clone(),
            binding: binding.clone(),
            document: document.clone(),
            version: version.clone(),
            draft_revision,
            provenance,
            cancel,
        })
    }
    fn saved_draft(doc: &Document, version: &Version, revision: u64) -> Result<(), Code> {
        if doc.version.as_ref() != Some(version) {
            return Err(Code::Conflict);
        }
        let draft = doc.draft_capture.as_ref().ok_or(Code::Conflict)?;
        let source = doc.selection.as_ref().ok_or(Code::Unavailable)?;
        if draft.revision != revision || draft.bytes != source.bytes {
            return Err(Code::Conflict);
        }
        Ok(())
    }
    pub fn validate_saved_app_lease(
        &self,
        binding: &Binding,
        lease: &mut SavedAppLease,
    ) -> Result<(), Code> {
        if !Arc::ptr_eq(&self.identity, &lease.ownership.host.identity)
            || !Arc::ptr_eq(&binding.identity, &lease.ownership.binding.identity)
            || !Arc::ptr_eq(&binding.host, &lease.ownership.binding.host)
        {
            return Err(Code::Denied);
        }
        lease.validate()
    }
    /// Native startup/open action only. Reserves an ordinary same-registry Open
    /// lifetime; the trusted picker, not a path argument, admits the project.
    pub fn prepare_project_reopen(&self, binding: &Binding) -> Result<ProjectReopenWork, Code> {
        let mut state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.authorized(&state, binding)?;
        let caller = state.registrations[index].caller.clone();
        if state
            .projects
            .values()
            .any(|r| r.owner == caller && r.pending())
            || state.registry.has_saved_app_work(&caller)
            || state
                .registry
                .operations
                .values()
                .any(|e| e.owner == caller && !e.phase.is_terminal())
        {
            return Err(Code::Busy);
        }
        let id = state.registry.reserve(&caller, Operation::Open)?;
        let Start::Work(job) = state.registry.open(&caller, Request { request_id: id })? else {
            return Err(Code::Unavailable);
        };
        Ok(ProjectReopenWork {
            host: self.clone(),
            binding: binding.clone(),
            job: Some(job),
        })
    }
}
impl SavedAppWork {
    fn validate(&self, state: &State) -> Result<(), Code> {
        if self.cancel.load(Ordering::Acquire) {
            return Err(Code::Revoked);
        }
        let index = self.host.authorized(state, &self.binding)?;
        let doc = state
            .registry
            .document(&state.registrations[index].caller, &self.document)?;
        if !doc
            .project_lease
            .as_ref()
            .is_some_and(|c| Arc::ptr_eq(c, &self.cancel))
        {
            return Err(Code::Denied);
        }
        if !doc
            .project
            .as_ref()
            .is_some_and(|p| p.revision == self.provenance.revision)
        {
            return Err(Code::Conflict);
        }
        NativeHost::saved_draft(doc, &self.version, self.draft_revision)
    }
    pub fn run(self) -> Result<SavedAppLease, Code> {
        {
            let state = self.host.state.lock().map_err(|_| Code::Unavailable)?;
            self.validate(&state)?;
        }
        let held = HeldApp::from_provenance(&self.provenance)?;
        {
            let state = self.host.state.lock().map_err(|_| Code::Unavailable)?;
            self.validate(&state)?;
        }
        Ok(SavedAppLease {
            held: Some(held),
            ownership: self,
        })
    }
}
impl Drop for SavedAppWork {
    fn drop(&mut self) {
        // Only bookkeeping lives in State: no lease object is dropped under the
        // mutex. Revoked grants remain until the actual work/lease drains.
        if let Ok(mut state) = self.host.state.lock() {
            if let Some(doc) = state.registry.documents.get_mut(&self.document) {
                if doc
                    .project_lease
                    .as_ref()
                    .is_some_and(|c| Arc::ptr_eq(c, &self.cancel))
                {
                    doc.project_lease = None;
                }
            }
            let owner = state.registrations[self.binding.slot].caller.clone();
            state.registry.release_drained_writer_grants(&owner);
        }
    }
}
impl SavedAppLease {
    pub fn document_id(&self) -> &DocumentId {
        &self.ownership.document
    }
    pub fn version(&self) -> &Version {
        &self.ownership.version
    }
    pub fn draft_revision(&self) -> u64 {
        self.ownership.draft_revision
    }
    pub fn project_revision(&self) -> &ProjectRevision {
        &self.ownership.provenance.revision
    }
    /// Immutable bytes for a local native consumer; validate before use and
    /// retain this lease through its real downstream lifetime.
    pub fn bytes(&self, role: SavedAppRole) -> &[u8] {
        &self.held.as_ref().expect("live lease").members[role.index()].bytes
    }
    pub fn cancel_requested(&self) -> bool {
        self.ownership.cancel.load(Ordering::Acquire)
    }
    pub fn validate(&mut self) -> Result<(), Code> {
        {
            let state = self
                .ownership
                .host
                .state
                .lock()
                .map_err(|_| Code::Unavailable)?;
            self.ownership.validate(&state)?;
        }
        if let Err(code) = self
            .held
            .as_mut()
            .ok_or(Code::Unavailable)?
            .check(&self.ownership.provenance.members)
        {
            self.ownership.cancel.store(true, Ordering::Release);
            return Err(code);
        }
        let state = self
            .ownership
            .host
            .state
            .lock()
            .map_err(|_| Code::Unavailable)?;
        self.ownership.validate(&state)
    }
}
impl Drop for SavedAppLease {
    fn drop(&mut self) {
        // Release OS read locks BEFORE the ownership field drops and clears
        // Busy. No success/completion/compiler receipt is minted by Drop.
        drop(self.held.take());
    }
}
impl ProjectReopenWork {
    pub fn run(mut self, picker: &mut impl ProjectRootPicker) -> Result<Option<Candidate>, Code> {
        let result = (|| {
            {
                let state = self.host.state.lock().map_err(|_| Code::Unavailable)?;
                self.host.authorized(&state, &self.binding)?;
            }
            let cancel = &self.job.as_ref().ok_or(Code::Unavailable)?.cancel;
            if cancel.load(Ordering::Acquire) {
                return Err(Code::Revoked);
            }
            let path =
                std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| picker.select_root()))
                    .map_err(|_| Code::IOFailure)??;
            if cancel.load(Ordering::Acquire) {
                return Err(Code::Revoked);
            }
            path.map(|p| HeldApp::open(&p)).transpose()
        })();
        let evidence = match &result {
            Ok(Some(held)) => Some((held.source()?, held.provenance()?)),
            _ => None,
        };
        let selection = match &result {
            Ok(Some(_)) => Ok(evidence.as_ref().map(|(s, _)| s.clone())),
            Ok(None) => Ok(None),
            Err(code) => Err(*code),
        };
        let job = self.job.take().ok_or(Code::Unavailable)?;
        let completion = Completion {
            request: job.request,
            cancel: job.cancel,
            result: selection,
        };
        let mut state = self.host.state.lock().map_err(|_| Code::Unavailable)?;
        let status = state.registry.complete(completion)?;
        match status {
            Status::Complete {
                result: Outcome::Opened { document },
                ..
            } => {
                let (source, project) = evidence.ok_or(Code::Unavailable)?;
                let doc = state
                    .registry
                    .documents
                    .get_mut(&document.document_id)
                    .ok_or(Code::Denied)?;
                doc.draft_capture = Some(save_as::CapturedDraft {
                    revision: 0,
                    bytes: source.bytes,
                });
                doc.project = Some(project);
                Ok(Some(document))
            }
            Status::Complete {
                result: Outcome::Cancelled { .. },
                ..
            } => Ok(None),
            Status::Complete {
                result: Outcome::Failed { code, .. },
                ..
            } => Err(code),
            _ => Err(Code::Unavailable),
        }
    }
}
impl Drop for ProjectReopenWork {
    fn drop(&mut self) {
        if let Some(job) = self.job.take() {
            if let Ok(mut state) = self.host.state.lock() {
                let _ = state.registry.complete(Completion {
                    request: job.request,
                    cancel: job.cancel,
                    result: Err(Code::Unavailable),
                });
            }
        }
    }
}

#[cfg(test)]
#[path = "host_project_snapshot_tests.rs"]
mod tests;
