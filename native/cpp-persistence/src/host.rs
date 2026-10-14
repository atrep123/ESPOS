//! Native host coordination over the SAME Registry. Not a second source owner.
//! Physical view/document/resource authentication belongs to the Tauri adapter;
//! a native Binding/LoadTicket below cannot be constructed from an IPC DTO.
use crate::{
    save_as::DraftBinding,
    writer::{ConflictDecision, SaveStart, SaveView, WriteJob, WriterEnvironment},
    *,
};
use serde::{Deserialize, Serialize};
use std::{
    collections::HashMap,
    path::Path,
    sync::{Arc, Mutex},
};

#[path = "host_fresh_project.rs"]
mod fresh_project_host;
pub use fresh_project_host::{
    ProjectFileProof, ProjectParentPicker, ProjectRecoveryView, ProjectStatus, ProjectWork,
};

pub const MAX_HOST_REQUEST_BYTES: usize = MAX_SOURCE_BYTES.div_ceil(3) * 4 + 4096;
#[cfg(test)]
#[path = "host_tests.rs"]
mod host_tests;
const MAX_CALLS: usize = 4096;
const MAX_NATIVE_REGISTRATIONS: usize = 256;

/// Correlation/replay key only, NEVER sender/document/file authority.
#[derive(Clone, Debug, PartialEq, Eq, Hash, Deserialize)]
#[serde(try_from = "String")]
pub struct CallId(String);
impl TryFrom<String> for CallId {
    type Error = &'static str;
    fn try_from(value: String) -> Result<Self, Self::Error> {
        let suffix = value.strip_prefix("call_").ok_or("invalid call ID")?;
        if suffix.len() != 32
            || !suffix
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err("invalid call ID");
        }
        Ok(Self(value))
    }
}
impl CallId {
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct HostRequest {
    pub call_id: CallId,
    pub command: HostCommand,
}
#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "camelCase", deny_unknown_fields)]
pub enum HostCommand {
    Reserve {
        intent: ReserveRequest,
    },
    New {
        #[serde(rename = "requestId")]
        request_id: RequestId,
    },
    Open {
        #[serde(rename = "requestId")]
        request_id: RequestId,
    },
    ChooseTarget {
        #[serde(rename = "requestId")]
        request_id: RequestId,
        #[serde(rename = "documentId")]
        document_id: DocumentId,
    },
    Status {
        #[serde(rename = "requestId")]
        request_id: RequestId,
    },
    Cancel {
        #[serde(rename = "requestId")]
        request_id: RequestId,
    },
    Release {
        grant: Release,
    },
    BindDraft {
        revision: u64,
        #[serde(rename = "sourceBase64")]
        source_base64: String,
    },
    ReserveSave {
        #[serde(rename = "documentId")]
        document_id: DocumentId,
        version: Version,
        #[serde(rename = "sourceBase64")]
        source_base64: String,
    },
    ReserveSaveAs {
        #[serde(rename = "documentId")]
        document_id: DocumentId,
        #[serde(rename = "targetGrantId")]
        target_grant_id: TargetId,
        revision: u64,
        #[serde(rename = "sourceBase64")]
        source_base64: String,
    },
    BeginSave {
        #[serde(rename = "requestId")]
        request_id: RequestId,
    },
    ConfirmSave {
        #[serde(rename = "requestId")]
        request_id: RequestId,
        decision: ConflictDecision,
    },
    RecoverSave {
        #[serde(rename = "requestId")]
        request_id: RequestId,
    },
    ListRecovery {
        offset: u32,
        limit: u32,
    },
    CompareRecovery {
        #[serde(rename = "operationId")]
        operation_id: RequestId,
    },
    CreateProject {
        #[serde(rename = "documentId")]
        document_id: DocumentId,
        revision: u64,
        #[serde(rename = "directoryName")]
        directory_name: String,
        #[serde(rename = "manifestBase64")]
        manifest_base64: String,
        #[serde(rename = "cmakeBase64")]
        cmake_base64: String,
        #[serde(rename = "traceabilityBase64")]
        traceability_base64: String,
    },
    ProjectStatus {
        #[serde(rename = "requestId")]
        request_id: RequestId,
    },
    CancelProject {
        #[serde(rename = "requestId")]
        request_id: RequestId,
    },
    ListProjectRecovery {},
    InspectProjectRecovery {
        #[serde(rename = "operationId")]
        operation_id: RequestId,
    },
}
pub fn decode_host_request(raw: &[u8]) -> Result<HostRequest, Code> {
    if raw.len() > MAX_HOST_REQUEST_BYTES {
        return Err(Code::TooLarge);
    }
    let request: HostRequest = serde_json::from_slice(raw).map_err(|_| Code::InvalidInput)?;
    match &request.command {
        HostCommand::BindDraft { revision, .. }
        | HostCommand::ReserveSaveAs { revision, .. }
        | HostCommand::CreateProject { revision, .. }
            if *revision > 9_007_199_254_740_991 =>
        {
            return Err(Code::InvalidInput)
        }
        HostCommand::ListRecovery { limit, .. } if !(1..=32).contains(limit) => {
            return Err(Code::InvalidInput)
        }
        _ => {}
    }
    Ok(request)
}

#[derive(Clone)]
pub struct Binding {
    host: Arc<()>,
    identity: Arc<()>,
    slot: usize,
}
pub struct LoadTicket {
    binding: Binding,
    identity: Arc<()>,
}
enum Admission {
    Quarantined,
    Loading(Arc<()>),
    Active,
    Revoked,
}
struct Registration {
    identity: Arc<()>,
    caller: Caller,
    admission: Admission,
    calls: HashMap<CallId, RecordedCall>,
}
struct RecordedCall {
    hash: [u8; 32],
    result: RecordedResult,
}
enum RecordedResult {
    Request(RequestId),
    Project(RequestId),
    Draft(DraftBinding),
    Released,
    Failed(Code),
}
struct State {
    registry: Registry,
    registrations: Vec<Registration>,
    projects: HashMap<RequestId, fresh_project_host::Record>,
}
#[derive(Clone)]
pub struct NativeHost {
    identity: Arc<()>,
    state: Arc<Mutex<State>>,
    environment: Arc<Mutex<WriterEnvironment>>,
    project_storage: Arc<std::path::PathBuf>,
    project_catalogue: Arc<HashMap<RequestId, std::path::PathBuf>>,
}

#[derive(Clone, Serialize)]
#[serde(tag = "kind", rename_all = "camelCase")]
pub enum HostReply {
    Reservation {
        #[serde(rename = "requestId")]
        request_id: RequestId,
        state: Status,
    },
    State {
        state: Status,
    },
    Draft {
        binding: DraftBinding,
    },
    Released {},
    RecoveryList {
        offset: u32,
        total: usize,
        items: Vec<RecoveryListItem>,
    },
    RecoveryComparison {
        comparison: crate::recovery_view::RecoveryComparison,
    },
    ProjectState {
        #[serde(rename = "requestId")]
        request_id: RequestId,
        state: ProjectStatus,
    },
    ProjectRecoveryIds {
        items: Vec<RequestId>,
    },
    ProjectRecoveryView {
        inspection: ProjectRecoveryView,
    },
}
/// Historical metadata only. Neither a file path nor an old live document grant.
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RecoveryListItem {
    operation_id: RequestId,
    display_name: String,
    historical_phase: String,
    backup_available: bool,
    source_hash: String,
    source_bytes: usize,
}
/// Work remains owned until real completion or an explicit undispatched drain.
pub enum HostDispatch {
    Reply(HostReply),
    Read(ReadWork),
    Write(WriteWork),
    Project(ProjectWork),
}
pub struct ReadWork {
    host: NativeHost,
    request: RequestId,
    job: Option<ReadJob>,
}
pub struct WriteWork {
    host: NativeHost,
    request: RequestId,
    job: Option<WriteJob>,
}
impl NativeHost {
    pub fn open_local(storage: &Path) -> Result<Self, Code> {
        let project_storage = storage.join("cpp-fresh-project-v1");
        let project_catalogue = fresh_project_host::catalogue(&project_storage)?;
        Ok(Self {
            identity: Arc::new(()),
            state: Arc::new(Mutex::new(State {
                registry: Registry::new()?,
                registrations: vec![],
                projects: HashMap::new(),
            })),
            environment: Arc::new(Mutex::new(WriterEnvironment::open_local(storage)?)),
            project_storage: Arc::new(project_storage),
            project_catalogue: Arc::new(project_catalogue),
        })
    }
    /// Native startup/inspection seam only, not an IPC command or fresh grant.
    pub fn recovery_records(&self) -> Result<Vec<RecoveryRecord>, Code> {
        let env = self.environment.lock().map_err(|_| Code::Unavailable)?;
        Ok(env.recovery_records().to_vec())
    }
    /// Read-only historical evidence. No automatic restore, retry or adoption.
    pub fn inspect_recovery(&self, operation: &RequestId) -> Result<RecoveryInspection, Code> {
        let env = self.environment.lock().map_err(|_| Code::Unavailable)?;
        env.inspect_recovery(operation)
    }
    /// Trusted native window construction only. Doesn't authenticate a document.
    pub fn prepare_native_view(&self) -> Result<Binding, Code> {
        let mut state = self.state.lock().map_err(|_| Code::Unavailable)?;
        if state.registrations.len() >= MAX_NATIVE_REGISTRATIONS {
            return Err(Code::Busy);
        }
        let caller = state.registry.attach_caller()?;
        let identity = Arc::new(());
        let slot = state.registrations.len();
        state.registrations.push(Registration {
            identity: identity.clone(),
            caller,
            admission: Admission::Quarantined,
            calls: HashMap::new(),
        });
        Ok(Binding {
            host: self.identity.clone(),
            identity,
            slot,
        })
    }
    /// Native main-document callback only. A second document permanently revokes
    /// this view; delayed old-page requests cannot gain a fresh incarnation.
    pub fn native_document_started(&self, binding: &Binding) -> Result<LoadTicket, Code> {
        let mut state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.index(&state, binding)?;
        if !matches!(state.registrations[index].admission, Admission::Quarantined) {
            Self::revoke_locked(&mut state, index)?;
            return Err(Code::Revoked);
        }
        let identity = Arc::new(());
        state.registrations[index].admission = Admission::Loading(identity.clone());
        Ok(LoadTicket {
            binding: binding.clone(),
            identity,
        })
    }
    pub fn native_document_finished(&self, ticket: LoadTicket) -> Result<(), Code> {
        let mut state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.index(&state, &ticket.binding)?;
        match &state.registrations[index].admission {
            Admission::Loading(identity) if Arc::ptr_eq(identity, &ticket.identity) => {
                state.registrations[index].admission = Admission::Active;
                Ok(())
            }
            Admission::Revoked => Err(Code::Revoked),
            _ => Err(Code::Denied),
        }
    }
    pub fn revoke_native_view(&self, binding: &Binding) -> Result<(), Code> {
        let mut state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.index(&state, binding)?;
        Self::revoke_locked(&mut state, index)
    }
    fn revoke_locked(state: &mut State, index: usize) -> Result<(), Code> {
        if matches!(state.registrations[index].admission, Admission::Revoked) {
            return Ok(());
        }
        let caller = state.registrations[index].caller.clone();
        for record in state
            .projects
            .values_mut()
            .filter(|record| record.owner == caller)
        {
            record
                .cancel
                .store(true, std::sync::atomic::Ordering::Release);
        }
        state.registrations[index].admission = Admission::Revoked;
        state.registry.revoke_caller(&caller)
    }
    fn index(&self, state: &State, binding: &Binding) -> Result<usize, Code> {
        if !Arc::ptr_eq(&self.identity, &binding.host) {
            return Err(Code::Denied);
        }
        let registration = state.registrations.get(binding.slot).ok_or(Code::Denied)?;
        if !Arc::ptr_eq(&registration.identity, &binding.identity) {
            return Err(Code::Denied);
        }
        Ok(binding.slot)
    }
    fn authorized(&self, state: &State, binding: &Binding) -> Result<usize, Code> {
        let index = self.index(state, binding)?;
        match state.registrations[index].admission {
            Admission::Active => Ok(index),
            Admission::Revoked => Err(Code::Revoked),
            _ => Err(Code::Unavailable),
        }
    }
    /// Strict raw DTO dispatch. Replay key never authenticates; the actual
    /// native binding must be active first. Cache only mutation identities,
    /// not unbounded source/status snapshots. Read-only status isn't retained.
    pub fn dispatch(&self, binding: &Binding, raw: &[u8]) -> Result<HostDispatch, Code> {
        let request = decode_host_request(raw)?;
        let hash = owned_job_digest(raw);
        let mut state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.authorized(&state, binding)?;
        let caller = state.registrations[index].caller.clone();
        let mutating = matches!(
            &request.command,
            HostCommand::Reserve { .. }
                | HostCommand::BindDraft { .. }
                | HostCommand::ReserveSave { .. }
                | HostCommand::ReserveSaveAs { .. }
                | HostCommand::Release { .. }
                | HostCommand::CreateProject { .. }
        );
        if let Some(recorded) = state.registrations[index].calls.get(&request.call_id) {
            if recorded.hash != hash {
                return Err(Code::InvalidInput);
            }
            return match &recorded.result {
                RecordedResult::Request(id) => Ok(HostDispatch::Reply(HostReply::Reservation {
                    request_id: id.clone(),
                    state: state.registry.status(&caller, id)?,
                })),
                RecordedResult::Project(id) => Ok(HostDispatch::Reply(HostReply::ProjectState {
                    request_id: id.clone(),
                    state: Self::project_status_locked(&state, &caller, id, false)?,
                })),
                RecordedResult::Draft(draft) => {
                    // Render original native request to check grant revocation;
                    // no new draft is minted after Release/eviction.
                    let current = state.registry.status(&caller, &draft.request_id)?;
                    if !matches!(
                        current,
                        Status::Complete {
                            result: Outcome::Created { .. },
                            ..
                        }
                    ) {
                        return Err(Code::Revoked);
                    }
                    let grant = state.registry.document(&caller, &draft.document_id)?;
                    if !grant.draft_capture.as_ref().is_some_and(|capture| {
                        capture.revision == draft.capture_revision
                            && capture.bytes.len() == draft.source_bytes
                            && crate::windows_write::digest(&capture.bytes) == draft.source_hash
                    }) {
                        return Err(Code::Revoked);
                    }
                    Ok(HostDispatch::Reply(HostReply::Draft {
                        binding: draft.clone(),
                    }))
                }
                RecordedResult::Released => Ok(HostDispatch::Reply(HostReply::Released {})),
                RecordedResult::Failed(code) => Err(*code),
            };
        }
        if state
            .projects
            .values()
            .any(|record| record.owner == caller && record.pending())
            && !matches!(
                &request.command,
                HostCommand::Status { .. }
                    | HostCommand::Cancel { .. }
                    | HostCommand::ListRecovery { .. }
                    | HostCommand::CompareRecovery { .. }
                    | HostCommand::ProjectStatus { .. }
                    | HostCommand::CancelProject { .. }
                    | HostCommand::ListProjectRecovery { .. }
                    | HostCommand::InspectProjectRecovery { .. }
            )
        {
            return Err(Code::Busy);
        }
        if mutating && state.registrations[index].calls.len() >= MAX_CALLS {
            return Err(Code::Busy);
        }
        let result = match request.command {
            HostCommand::CreateProject {
                document_id,
                revision,
                directory_name,
                manifest_base64,
                cmake_base64,
                traceability_base64,
            } => (|| {
                let companions = [
                    decode_project_companion(&manifest_base64)?,
                    decode_project_companion(&cmake_base64)?,
                    decode_project_companion(&traceability_base64)?,
                ];
                self.prepare_fresh_project_locked(
                    &mut state,
                    binding,
                    &document_id,
                    revision,
                    directory_name,
                    companions,
                )
                .map(HostDispatch::Project)
            })(),
            HostCommand::ProjectStatus { request_id } => {
                Self::project_status_locked(&state, &caller, &request_id, false)
                    .map(|state| HostDispatch::Reply(HostReply::ProjectState { request_id, state }))
            }
            HostCommand::CancelProject { request_id } => {
                Self::project_status_locked(&state, &caller, &request_id, true)
                    .map(|state| HostDispatch::Reply(HostReply::ProjectState { request_id, state }))
            }
            HostCommand::ListProjectRecovery {} => {
                Ok(HostDispatch::Reply(HostReply::ProjectRecoveryIds {
                    items: self.project_ids_locked(),
                }))
            }
            HostCommand::InspectProjectRecovery { operation_id } => {
                // No State mutex across filesystem inspection; the inspection
                // reauthenticates the actual native binding before returning.
                drop(state);
                return self
                    .inspect_project_recovery(binding, &operation_id)
                    .map(|inspection| {
                        HostDispatch::Reply(HostReply::ProjectRecoveryView { inspection })
                    });
            }
            command => self.execute_locked(&mut state, &caller, command),
        };
        if mutating {
            let saved = match &result {
                Ok(HostDispatch::Reply(HostReply::Reservation { request_id, .. })) => {
                    RecordedResult::Request(request_id.clone())
                }
                Ok(HostDispatch::Reply(HostReply::Draft { binding })) => {
                    RecordedResult::Draft(binding.clone())
                }
                Ok(HostDispatch::Reply(HostReply::Released {})) => RecordedResult::Released,
                Ok(HostDispatch::Project(work)) => {
                    RecordedResult::Project(work.request_id().clone())
                }
                Err(code) => RecordedResult::Failed(*code),
                _ => return Err(Code::Unavailable),
            };
            state.registrations[index].calls.insert(
                request.call_id,
                RecordedCall {
                    hash,
                    result: saved,
                },
            );
        }
        result
    }
    fn execute_locked(
        &self,
        state: &mut State,
        caller: &Caller,
        command: HostCommand,
    ) -> Result<HostDispatch, Code> {
        let r = &mut state.registry;
        let reply = match command {
            HostCommand::Reserve { intent } => {
                let id = r.reserve_request(caller, intent)?;
                HostReply::Reservation {
                    state: r.status(caller, &id)?,
                    request_id: id,
                }
            }
            HostCommand::New { request_id } => {
                match r.new_document(caller, Request { request_id })? {
                    Start::Ready(state) => HostReply::State { state },
                    Start::Work(_) => return Err(Code::Unavailable),
                }
            }
            HostCommand::Open { request_id } => {
                return self.read_dispatch(
                    caller,
                    request_id.clone(),
                    r.open(caller, Request { request_id })?,
                )
            }
            HostCommand::ChooseTarget {
                request_id,
                document_id,
            } => {
                return self.read_dispatch(
                    caller,
                    request_id.clone(),
                    r.choose_target(
                        caller,
                        TargetRequest {
                            request_id,
                            document_id,
                        },
                    )?,
                )
            }
            HostCommand::Status { request_id } => HostReply::State {
                state: r.status(caller, &request_id)?,
            },
            HostCommand::Cancel { request_id } => HostReply::State {
                state: r.cancel(caller, &request_id)?,
            },
            HostCommand::Release { grant } => {
                r.release(caller, grant)?;
                HostReply::Released {}
            }
            HostCommand::BindDraft {
                revision,
                source_base64,
            } => HostReply::Draft {
                binding: r.bind_captured_draft(caller, revision, decode_source(&source_base64)?)?,
            },
            HostCommand::ReserveSave {
                document_id,
                version,
                source_base64,
            } => {
                let id = r.reserve_save(
                    caller,
                    &document_id,
                    &version,
                    decode_source(&source_base64)?,
                )?;
                HostReply::Reservation {
                    state: r.status(caller, &id)?,
                    request_id: id,
                }
            }
            HostCommand::ReserveSaveAs {
                document_id,
                target_grant_id,
                revision,
                source_base64,
            } => {
                let id = r.reserve_save_as(
                    caller,
                    &document_id,
                    &target_grant_id,
                    revision,
                    decode_source(&source_base64)?,
                )?;
                HostReply::Reservation {
                    state: r.status(caller, &id)?,
                    request_id: id,
                }
            }
            HostCommand::BeginSave { request_id } => {
                return self.write_dispatch(
                    caller,
                    request_id.clone(),
                    r.begin_save(caller, &request_id)?,
                )
            }
            HostCommand::ConfirmSave {
                request_id,
                decision,
            } => {
                return self.write_dispatch(
                    caller,
                    request_id.clone(),
                    r.confirm_save(caller, &request_id, decision)?,
                )
            }
            HostCommand::RecoverSave { request_id } => {
                let mut env = self.environment.lock().map_err(|_| Code::Unavailable)?;
                HostReply::State {
                    state: Status::Save {
                        write: r.recover_save(caller, &request_id, &mut env)?,
                    },
                }
            }
            HostCommand::ListRecovery { offset, limit } => {
                let env = self.environment.lock().map_err(|_| Code::Unavailable)?;
                let records = env.recovery_records();
                let items = records
                    .iter()
                    .skip(offset as usize)
                    .take(limit as usize)
                    .map(|record| RecoveryListItem {
                        operation_id: record.operation_id.clone(),
                        display_name: record.display_name.clone(),
                        historical_phase: record.phase.into(),
                        backup_available: record.backup_available,
                        source_hash: record.source_hash.clone(),
                        source_bytes: record.source_bytes,
                    })
                    .collect();
                HostReply::RecoveryList {
                    offset,
                    total: records.len(),
                    items,
                }
            }
            HostCommand::CompareRecovery { operation_id } => {
                let env = self.environment.lock().map_err(|_| Code::Unavailable)?;
                HostReply::RecoveryComparison {
                    comparison: crate::recovery_view::comparison_view(
                        env.inspect_recovery(&operation_id)?,
                    )?,
                }
            }
            HostCommand::CreateProject { .. }
            | HostCommand::ProjectStatus { .. }
            | HostCommand::CancelProject { .. }
            | HostCommand::ListProjectRecovery { .. }
            | HostCommand::InspectProjectRecovery { .. } => return Err(Code::Unavailable),
        };
        Ok(HostDispatch::Reply(reply))
    }
    fn read_dispatch(
        &self,
        _caller: &Caller,
        id: RequestId,
        start: Start,
    ) -> Result<HostDispatch, Code> {
        Ok(match start {
            Start::Ready(state) => HostDispatch::Reply(HostReply::State { state }),
            Start::Work(job) => HostDispatch::Read(ReadWork {
                host: self.clone(),
                request: id,
                job: Some(job),
            }),
        })
    }
    fn write_dispatch(
        &self,
        _caller: &Caller,
        id: RequestId,
        start: SaveStart,
    ) -> Result<HostDispatch, Code> {
        Ok(match start {
            SaveStart::Ready(write) => HostDispatch::Reply(HostReply::State {
                state: Status::Save { write },
            }),
            SaveStart::Work(job) => HostDispatch::Write(WriteWork {
                host: self.clone(),
                request: id,
                job: Some(job),
            }),
        })
    }
    pub fn state(&self, binding: &Binding, id: &RequestId) -> Result<Status, Code> {
        let state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.authorized(&state, binding)?;
        state
            .registry
            .status(&state.registrations[index].caller, id)
    }
}

fn decode_project_companion(encoded: &str) -> Result<Vec<u8>, Code> {
    const CAP: usize = 65_536;
    if encoded.len() > CAP.div_ceil(3) * 4 {
        return Err(Code::TooLarge);
    }
    let bytes = decode_source(encoded)?;
    if bytes.len() > CAP {
        return Err(Code::TooLarge);
    }
    // Files::new performs the final nonempty/UTF-8/NUL checks as well.
    if bytes.is_empty() || bytes.contains(&0) {
        return Err(Code::InvalidInput);
    }
    Ok(bytes)
}
impl ReadWork {
    pub fn request_id(&self) -> &RequestId {
        &self.request
    }
    pub fn run(mut self, picker: &mut impl NativePicker) -> Result<Status, Code> {
        let completion = self.job.take().ok_or(Code::Unavailable)?.run(picker);
        self.host
            .state
            .lock()
            .map_err(|_| Code::Unavailable)?
            .registry
            .complete(completion)
    }
}
impl Drop for ReadWork {
    fn drop(&mut self) {
        struct Undispatched;
        impl NativePicker for Undispatched {
            fn select(&mut self, _: PickerKind) -> Result<Option<std::path::PathBuf>, Code> {
                Err(Code::Unavailable)
            }
        }
        if let Some(job) = self.job.take() {
            let completion = job.run(&mut Undispatched);
            if let Ok(mut state) = self.host.state.lock() {
                let _ = state.registry.complete(completion);
            }
        }
    }
}
impl WriteWork {
    pub fn request_id(&self) -> &RequestId {
        &self.request
    }
    pub fn run(mut self) -> Result<SaveView, Code> {
        let completion = {
            let mut env = self
                .host
                .environment
                .lock()
                .map_err(|_| Code::Unavailable)?;
            let job = self.job.take().ok_or(Code::Unavailable)?;
            job.run(&mut env)
        };
        self.host
            .state
            .lock()
            .map_err(|_| Code::Unavailable)?
            .registry
            .complete_save(completion)
    }
}
impl Drop for WriteWork {
    fn drop(&mut self) {
        if let Some(job) = self.job.take() {
            let completion = job.undispatched();
            if let Ok(mut state) = self.host.state.lock() {
                let _ = state.registry.complete_save(completion);
            }
        }
    }
}
