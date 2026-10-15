//! Canonical native core for C++ documents with conventional local persistence.
//! Native host APIs only; no installed Tauri handlers or IPC activation.
#[cfg(not(windows))]
compile_error!("Native C++ persistence requires Windows; no simulated fallback");
mod create_target;
mod fresh_project;
mod fresh_project_recovery;
pub mod host;
mod project_snapshot;
pub mod recovery_view;
pub mod save_as;
pub mod types;
mod windows_read;
mod windows_write;
pub mod writer;
pub use types::*;
pub use windows_write::{
    CurrentTargetObservation, RecoveryInspection, RecoveryRecord, RecoveryScope,
};

use base64::{engine::general_purpose::STANDARD, Engine};
use std::{
    collections::{HashMap, VecDeque},
    path::PathBuf,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
};
use windows_read::Selection;
// Sealed native-only capability: no Deserialize/path getter/public constructor.

#[derive(Clone)]
pub struct OwnedJobSourceGrant {
    owner: Caller,
    document: DocumentId,
    version: Version,
    selection: Selection,
}
impl OwnedJobSourceGrant {
    pub fn document_id(&self) -> &DocumentId {
        &self.document
    }
    pub fn version(&self) -> &Version {
        &self.version
    }
    pub fn bytes(&self) -> &[u8] {
        &self.selection.bytes
    }
    pub fn hash(&self) -> Result<[u8; 32], Code> {
        self.selection.sha256.ok_or(Code::Unavailable)
    }
}
/// Native host helper using an EXISTING pinned dependency, not SDK expansion.
pub fn owned_job_digest(bytes: &[u8]) -> [u8; 32] {
    use sha2::{Digest, Sha256};
    Sha256::digest(bytes).into()
}
pub fn owned_job_nonce() -> Result<String, Code> {
    windows_read::random_hex()
}

/// Host-only identity, NOT Deserialize/Serialize and not accepted from IPC.
/// Future Tauri host must allocate once per actual webview incarnation, not per invoke.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Caller {
    session: String,
    incarnation: String,
}
struct CallerState {
    active: bool,
    dialog: Option<RequestId>,
}
struct Document {
    owner: Caller,
    selection: Option<Selection>,
    version: Option<Version>,
    draft_capture: Option<save_as::CapturedDraft>,
    project: Option<project_snapshot::Provenance>,
    project_lease: Option<Arc<AtomicBool>>,
}
struct Target {
    owner: Caller,
    document: DocumentId,
    selection: Selection,
    version: Option<Version>,
}
#[derive(Clone)]
enum Settled {
    Created(DocumentId),
    Opened(DocumentId),
    Selected(TargetId),
    Cancelled,
    Failed(Code),
}
enum Phase {
    Reserved,
    Pending(Arc<AtomicBool>),
    Settled(Settled),
    Writer(Box<writer::Record>),
}
impl Phase {
    fn is_terminal(&self) -> bool {
        matches!(self, Self::Settled(_))
            || matches!(self,Self::Writer(r) if !r.blocks_replacement())
    }
}
struct Entry {
    owner: Caller,
    operation: Operation,
    phase: Phase,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PickerKind {
    Open,
    SaveTarget,
}
/// Trusted native-host seam. Production implementation must show a real picker.
/// Tests explicitly label their supplied caller/picker as TEST_ONLY.
pub trait NativePicker {
    fn select(&mut self, kind: PickerKind) -> Result<Option<PathBuf>, Code>;
}

pub struct ReadJob {
    request: RequestId,
    cancel: Arc<AtomicBool>,
    kind: PickerKind,
}
pub struct Completion {
    request: RequestId,
    cancel: Arc<AtomicBool>,
    result: Result<Option<Selection>, Code>,
}
impl ReadJob {
    /// Run away from the registry lock; only this non-Clone work item may launch
    /// a picker/read. Always return Completion, including cancellation/failure.
    pub fn run(self, picker: &mut impl NativePicker) -> Completion {
        let result = (|| {
            if self.cancel.load(Ordering::Acquire) {
                return Ok(None);
            }
            // A trusted picker can unwind without returning its ordinary error.
            // Convert only that seam's unwind into a failed completion so the
            // registry can settle the request and release its dialog lease.
            // Never mint a selection, retry the damaged picker, or acknowledge
            // persistence after this failure. Abort/process death needs host
            // lifecycle recovery; catch_unwind cannot handle either.
            let path = match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                picker.select(self.kind)
            })) {
                Ok(result) => result?,
                Err(_) => return Err(Code::IOFailure),
            };
            if self.cancel.load(Ordering::Acquire) {
                return Ok(None);
            }
            match path {
                None => Ok(None),
                Some(path) => windows_read::read_selected(
                    path,
                    self.kind == PickerKind::SaveTarget,
                    &self.cancel,
                )
                .map(Some),
            }
        })();
        Completion {
            request: self.request,
            cancel: self.cancel,
            result,
        }
    }
}

pub enum Start {
    Ready(Status),
    Work(ReadJob),
}

pub struct Registry {
    session: String,
    callers: HashMap<Caller, CallerState>,
    documents: HashMap<DocumentId, Document>,
    targets: HashMap<TargetId, Target>,
    operations: HashMap<RequestId, Entry>,
    settled: VecDeque<RequestId>,
}

impl Registry {
    pub fn new() -> Result<Self, Code> {
        Ok(Self {
            session: windows_read::random_hex()?,
            callers: HashMap::new(),
            documents: HashMap::new(),
            targets: HashMap::new(),
            operations: HashMap::new(),
            settled: VecDeque::new(),
        })
    }
    /// Trusted host lifecycle hook; actual ACL/caller authentication is NOT
    /// established merely by compiling this standalone library.
    pub fn attach_caller(&mut self) -> Result<Caller, Code> {
        if self.callers.len() >= MAX_CALLERS {
            return Err(Code::Busy);
        }
        let caller = Caller {
            session: self.session.clone(),
            incarnation: windows_read::random_hex()?,
        };
        if self.callers.contains_key(&caller) {
            return Err(Code::Unavailable);
        }
        self.callers.insert(
            caller.clone(),
            CallerState {
                active: true,
                dialog: None,
            },
        );
        Ok(caller)
    }
    fn authorize(&self, caller: &Caller) -> Result<(), Code> {
        if caller.session != self.session || !self.callers.get(caller).is_some_and(|s| s.active) {
            return Err(Code::Denied);
        }
        Ok(())
    }
    fn document(&self, caller: &Caller, id: &DocumentId) -> Result<&Document, Code> {
        self.documents
            .get(id)
            .filter(|d| d.owner == *caller)
            .ok_or(Code::Denied)
    }
    fn entry(&self, caller: &Caller, id: &RequestId) -> Result<&Entry, Code> {
        self.authorize(caller)?;
        let entry = self.operations.get(id).ok_or(Code::UnknownRequest)?;
        if entry.owner != *caller {
            return Err(Code::Denied);
        }
        Ok(entry)
    }
    /// Native reservation is bounded and operation-bound. It is NOT an installed
    /// IPC endpoint. Bridge/API review must expose a narrow way to obtain it.
    /// Never auto-reserve an unknown incoming ID: that would break replay safety.
    pub fn reserve_request(
        &mut self,
        caller: &Caller,
        input: ReserveRequest,
    ) -> Result<RequestId, Code> {
        self.reserve(caller, input.into())
    }
    pub fn reserve(&mut self, caller: &Caller, operation: Operation) -> Result<RequestId, Code> {
        self.authorize(caller)?;
        if let Operation::ChooseTarget(id) | Operation::Save(id) = &operation {
            self.document(caller, id)?;
        }
        if self
            .operations
            .values()
            .filter(|e| !e.phase.is_terminal())
            .count()
            >= MAX_UNRESOLVED_OPS
        {
            return Err(Code::Busy);
        }
        let id = RequestId::mint()?;
        if self.operations.contains_key(&id) {
            return Err(Code::Unavailable);
        }
        self.operations.insert(
            id.clone(),
            Entry {
                owner: caller.clone(),
                operation,
                phase: Phase::Reserved,
            },
        );
        Ok(id)
    }
    fn grants_full(&self) -> bool {
        self.documents.len() + self.targets.len() >= MAX_GRANTS
    }
    fn settle(&mut self, id: &RequestId, outcome: Settled) {
        self.operations
            .get_mut(id)
            .expect("internal live operation")
            .phase = Phase::Settled(outcome);
        self.remember_terminal(id);
    }
    // Writer terminal records keep their real SaveView in the shared bounded
    // history. Running, conflict and unknown effects never enter this queue.
    fn remember_terminal(&mut self, id: &RequestId) {
        if !self
            .operations
            .get(id)
            .is_some_and(|e| e.phase.is_terminal())
            || self.settled.contains(id)
        {
            return;
        }
        self.settled.push_back(id.clone());
        while self.settled.len() > MAX_SETTLED_OPS {
            let old = self.settled.pop_front().expect("settled queue nonempty");
            // Evicted IDs remain unknown; reservations never reuse input IDs.
            if self
                .operations
                .get(&old)
                .is_some_and(|e| e.phase.is_terminal())
            {
                self.operations.remove(&old);
            }
        }
    }
    fn release_drained_writer_grants(&mut self, owner: &Caller) {
        if self.authorize(owner).is_ok() {
            return;
        }
        let retained: Vec<_> = self
            .operations
            .values()
            .filter_map(|e| match &e.phase {
                Phase::Writer(r) if e.owner == *owner && r.blocks_replacement() => {
                    Some(r.document.clone())
                }
                _ => None,
            })
            .collect();
        self.documents.retain(|id, d| {
            d.owner != *owner || retained.contains(id) || d.project_lease.is_some()
        });
    }
    pub fn new_document(&mut self, caller: &Caller, input: Request) -> Result<Start, Code> {
        self.start(caller, input.request_id, Operation::New)
    }
    pub fn open(&mut self, caller: &Caller, input: Request) -> Result<Start, Code> {
        self.start(caller, input.request_id, Operation::Open)
    }
    pub fn choose_target(&mut self, caller: &Caller, input: TargetRequest) -> Result<Start, Code> {
        self.start(
            caller,
            input.request_id,
            Operation::ChooseTarget(input.document_id),
        )
    }
    fn start(
        &mut self,
        caller: &Caller,
        id: RequestId,
        operation: Operation,
    ) -> Result<Start, Code> {
        let entry = self.entry(caller, &id)?;
        if self.has_saved_app_work(caller) {
            return Err(Code::Busy);
        }
        if matches!(operation, Operation::Save(_)) {
            return Err(Code::InvalidInput);
        }
        if self.operations.values().any(|e| {
            e.owner == *caller && matches!(&e.phase,Phase::Writer(r) if r.blocks_replacement())
        }) {
            return Err(Code::Busy);
        }
        if entry.operation != operation {
            return Err(Code::InvalidInput);
        }
        if !matches!(entry.phase, Phase::Reserved) {
            return Ok(Start::Ready(self.status(caller, &id)?));
        }
        if let Operation::ChooseTarget(doc) = &operation {
            self.document(caller, doc)?;
        }
        if self.grants_full() {
            self.settle(&id, Settled::Failed(Code::Busy));
            return Ok(Start::Ready(self.status(caller, &id)?));
        }
        if operation == Operation::New {
            let document = DocumentId::mint()?;
            if self.documents.contains_key(&document) {
                return Err(Code::Unavailable);
            }
            self.documents.insert(
                document.clone(),
                Document {
                    owner: caller.clone(),
                    selection: None,
                    version: None,
                    draft_capture: None,
                    project: None,
                    project_lease: None,
                },
            );
            self.settle(&id, Settled::Created(document));
            return Ok(Start::Ready(self.status(caller, &id)?));
        }
        let state = self.callers.get_mut(caller).ok_or(Code::Denied)?;
        // Includes cancelled-but-not-yet-completed jobs: never open a second dialog.
        if state.dialog.is_some() {
            return Err(Code::Busy);
        }
        state.dialog = Some(id.clone());
        let cancel = Arc::new(AtomicBool::new(false));
        self.operations
            .get_mut(&id)
            .expect("authorized operation")
            .phase = Phase::Pending(cancel.clone());
        let kind = if operation == Operation::Open {
            PickerKind::Open
        } else {
            PickerKind::SaveTarget
        };
        Ok(Start::Work(ReadJob {
            request: id,
            cancel,
            kind,
        }))
    }
    /// Only a native ReadJob creates Completion. No paths or completion booleans
    /// can be supplied through a JSON request or substituted by the frontend.
    pub fn complete(&mut self, completion: Completion) -> Result<Status, Code> {
        let entry = self
            .operations
            .get(&completion.request)
            .ok_or(Code::UnknownRequest)?;
        let Phase::Pending(cancel) = &entry.phase else {
            return Err(Code::InvalidInput);
        };
        if !Arc::ptr_eq(cancel, &completion.cancel) {
            return Err(Code::Denied);
        }
        let owner = entry.owner.clone();
        let operation = entry.operation.clone();
        let cancelled = cancel.load(Ordering::Acquire) || self.authorize(&owner).is_err();
        let outcome = if cancelled {
            Settled::Cancelled
        } else {
            match completion.result {
                Ok(None) | Err(Code::Revoked) => Settled::Cancelled,
                Err(code) => Settled::Failed(code),
                Ok(Some(selection)) => self
                    .accept_selection(&owner, &operation, selection)
                    .unwrap_or_else(Settled::Failed),
            }
        };
        self.settle(&completion.request, outcome);
        if let Some(state) = self.callers.get_mut(&owner) {
            if state.dialog.as_ref() == Some(&completion.request) {
                state.dialog = None;
            }
            if !state.active {
                self.callers.remove(&owner);
            }
        }
        // Internal completion can finish a revoked caller; no caller API can read it.
        Ok(self.render(
            self.operations
                .get(&completion.request)
                .ok_or(Code::UnknownRequest)?,
        ))
    }
    fn accept_selection(
        &mut self,
        owner: &Caller,
        operation: &Operation,
        mut selection: Selection,
    ) -> Result<Settled, Code> {
        if self.grants_full() {
            return Err(Code::Busy);
        }
        match operation {
            Operation::Open => {
                if selection.file.is_none() {
                    return Err(Code::IOFailure);
                }
                let id = DocumentId::mint()?;
                let version = Version::mint()?;
                if self.documents.contains_key(&id) {
                    return Err(Code::Unavailable);
                }
                self.documents.insert(
                    id.clone(),
                    Document {
                        owner: owner.clone(),
                        selection: Some(selection),
                        version: Some(version),
                        draft_capture: None,
                        project: None,
                        project_lease: None,
                    },
                );
                Ok(Settled::Opened(id))
            }
            Operation::ChooseTarget(document) => {
                self.document(owner, document)?;
                let id = TargetId::mint()?;
                let version = if selection.file.is_some() {
                    Some(Version::mint()?)
                } else {
                    None
                };
                if self.targets.contains_key(&id) {
                    return Err(Code::Unavailable);
                }
                // A target grant retains evidence/hash, not another source draft.
                selection.bytes = Vec::new();
                self.targets.insert(
                    id.clone(),
                    Target {
                        owner: owner.clone(),
                        document: document.clone(),
                        selection,
                        version,
                    },
                );
                Ok(Settled::Selected(id))
            }
            Operation::New | Operation::Save(_) => Err(Code::InvalidInput),
        }
    }
    fn render(&self, entry: &Entry) -> Status {
        let operation = match entry.operation {
            Operation::New => "new",
            Operation::Open => "open",
            Operation::ChooseTarget(_) => "chooseTarget",
            Operation::Save(_) => "save",
        };
        let outcome = match &entry.phase {
            Phase::Writer(record) => {
                return Status::Save {
                    write: record.view(),
                }
            }
            Phase::Reserved => return Status::Reserved,
            Phase::Pending(flag) => {
                return Status::Pending {
                    cancel_requested: flag.load(Ordering::Acquire),
                }
            }
            Phase::Settled(result) => match result {
                Settled::Cancelled => Outcome::Cancelled {
                    commit: "not-started",
                },
                Settled::Failed(code) => Outcome::Failed {
                    commit: "not-started",
                    code: *code,
                },
                Settled::Created(id) | Settled::Opened(id) => match self.documents.get(id) {
                    None => Outcome::Revoked,
                    Some(doc) => {
                        let source = doc.selection.as_ref().map_or_else(
                            || {
                                doc.draft_capture
                                    .as_ref()
                                    .map_or_else(String::new, |c| STANDARD.encode(&c.bytes))
                            },
                            |s| STANDARD.encode(&s.bytes),
                        );
                        let binding =
                            doc.selection
                                .as_ref()
                                .zip(doc.version.as_ref())
                                .map(|(s, v)| Binding {
                                    version: v.clone(),
                                    display_name: display(s),
                                });
                        let candidate = Candidate {
                            document_id: id.clone(),
                            source_base64: source.clone(),
                            saved_base64: doc.selection.as_ref().map(|_| source),
                            binding,
                        };
                        if matches!(result, Settled::Created(_)) {
                            Outcome::Created {
                                document: candidate,
                            }
                        } else {
                            Outcome::Opened {
                                document: candidate,
                            }
                        }
                    }
                },
                Settled::Selected(id) => match self.targets.get(id) {
                    None => Outcome::Revoked,
                    Some(target) => Outcome::Selected {
                        target_grant_id: id.clone(),
                        document_id: target.document.clone(),
                        display_name: display(&target.selection),
                        target_state: target.version.as_ref().map_or(TargetState::Absent, |v| {
                            TargetState::Existing { version: v.clone() }
                        }),
                    },
                },
            },
        };
        Status::Complete {
            operation,
            result: outcome,
        }
    }
    pub fn status(&self, caller: &Caller, id: &RequestId) -> Result<Status, Code> {
        Ok(self.render(self.entry(caller, id)?))
    }
    pub fn cancel(&mut self, caller: &Caller, id: &RequestId) -> Result<Status, Code> {
        self.entry(caller, id)?;
        match &mut self
            .operations
            .get_mut(id)
            .ok_or(Code::UnknownRequest)?
            .phase
        {
            Phase::Reserved => self.settle(id, Settled::Cancelled),
            Phase::Pending(cancel) => cancel.store(true, Ordering::Release),
            Phase::Writer(record) => record.cancel_intent(),
            Phase::Settled(_) => {} // Already completed: return real outcome, not false cancellation.
        }
        self.remember_terminal(id);
        self.status(caller, id)
    }
    pub fn release(&mut self, caller: &Caller, input: Release) -> Result<(), Code> {
        self.authorize(caller)?;
        if self.has_saved_app_work(caller) {
            return Err(Code::Busy);
        }
        // A captured writer keeps its grant until native effect is resolved.
        if self.operations.values().any(|e| {
            e.owner == *caller && matches!(&e.phase,Phase::Writer(r) if r.blocks_replacement())
        }) {
            return Err(Code::Busy);
        }
        match input {
            Release::Document { document_id } => {
                self.document(caller, &document_id)?;
                self.documents.remove(&document_id);
                self.targets.retain(|_, t| t.document != document_id);
                let affected: Vec<_> = self
                    .operations
                    .iter()
                    .filter(|(_, e)| {
                        e.owner == *caller
                            && e.operation == Operation::ChooseTarget(document_id.clone())
                            && !matches!(e.phase, Phase::Settled(_))
                    })
                    .map(|(id, _)| id.clone())
                    .collect();
                for id in affected {
                    self.cancel(caller, &id)?;
                }
            }
            Release::Target { target_grant_id } => {
                if !self
                    .targets
                    .get(&target_grant_id)
                    .is_some_and(|t| t.owner == *caller)
                {
                    return Err(Code::Denied);
                }
                self.targets.remove(&target_grant_id);
            }
        }
        Ok(())
    }
    pub fn revoke_caller(&mut self, caller: &Caller) -> Result<(), Code> {
        self.authorize(caller)?;
        for d in self.documents.values().filter(|d| d.owner == *caller) {
            if let Some(cancel) = &d.project_lease {
                cancel.store(true, Ordering::Release);
            }
        }
        let ids: Vec<_> = self
            .operations
            .iter()
            .filter(|(_, e)| e.owner == *caller && !e.phase.is_terminal())
            .map(|(id, _)| id.clone())
            .collect();
        for id in ids {
            self.cancel(caller, &id)?;
        }
        // Writer records retain captured native evidence even after page revocation.
        // Revocation cancels work, never rewrites an actual effect as Cancelled.
        let retained: Vec<_> = self
            .operations
            .values()
            .filter_map(|e| match &e.phase {
                Phase::Writer(r) if r.blocks_replacement() => Some(r.document.clone()),
                _ => None,
            })
            .collect();
        self.documents.retain(|id, d| {
            d.owner != *caller || retained.contains(id) || d.project_lease.is_some()
        });
        self.targets.retain(|_, t| t.owner != *caller);
        let state = self.callers.get_mut(caller).ok_or(Code::Denied)?;
        state.active = false;
        if state.dialog.is_none() {
            self.callers.remove(caller);
        }
        Ok(())
    }

    /// Sealed capability from SAME existing document/grant registry. No caller
    /// path, picker or write. External file changes are conflicts, not new source.
    pub fn owned_job_source_grant(
        &self,
        caller: &Caller,
        id: &DocumentId,
        version: &Version,
    ) -> Result<OwnedJobSourceGrant, Code> {
        self.authorize(caller)?;
        let document = self.document(caller, id)?;
        if document.version.as_ref() != Some(version) {
            return Err(Code::Conflict);
        }
        let selection = document.selection.as_ref().ok_or(Code::Unavailable)?;
        if selection
            .path
            .file_name()
            .is_some_and(|name| name.to_string_lossy().eq_ignore_ascii_case("wifi_udaje.h"))
        {
            return Err(Code::Denied); // before any new OS read/hash
        }
        // Initial app-source admission only. Reject all headers (also DOS short
        // .h aliases), so the excluded credential header cannot be re-read via
        // a short-name spelling. Open/codegraph behavior itself is unchanged.
        let extension = selection
            .path
            .extension()
            .and_then(|s| s.to_str())
            .map(str::to_ascii_lowercase);
        if !matches!(extension.as_deref(), Some("cpp" | "cc" | "cxx")) {
            return Err(Code::Denied);
        }
        let fresh =
            windows_read::read_selected(selection.path.clone(), false, &AtomicBool::new(false))?;
        if fresh.parent != selection.parent
            || fresh.file != selection.file
            || fresh.sha256 != selection.sha256
            || fresh.bytes != selection.bytes
        {
            return Err(Code::Conflict);
        }
        Ok(OwnedJobSourceGrant {
            owner: caller.clone(),
            document: id.clone(),
            version: version.clone(),
            selection: fresh,
        })
    }
    pub fn validate_owned_job_source(
        &self,
        caller: &Caller,
        grant: &OwnedJobSourceGrant,
    ) -> Result<(), Code> {
        if grant.owner != *caller {
            return Err(Code::Denied);
        }
        let fresh = self.owned_job_source_grant(caller, &grant.document, &grant.version)?;
        if fresh.selection.parent != grant.selection.parent
            || fresh.selection.file != grant.selection.file
            || fresh.hash()? != grant.hash()?
            || fresh.bytes() != grant.bytes()
        {
            return Err(Code::Conflict);
        }
        Ok(())
    }

    pub fn counts(&self) -> (usize, usize, usize) {
        (
            self.documents.len() + self.targets.len(),
            self.settled.len(),
            self.operations.len() - self.settled.len(),
        )
    }
}
fn display(selection: &Selection) -> String {
    selection
        .path
        .file_name()
        .map(|v| v.to_string_lossy().into_owned())
        .unwrap_or_default()
}

#[cfg(test)]
mod tests;
