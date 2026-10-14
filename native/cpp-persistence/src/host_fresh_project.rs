//! Native-only same-Registry project work. No JSON path or renderer route here.
use super::*;
use crate::fresh_project::{Files, Plan};
use crate::windows_write::{digest, Pins, Scope};
use std::{
    fs,
    path::PathBuf,
    sync::atomic::{AtomicBool, Ordering},
};

const MAX_PENDING: usize = 32;
const MAX_HISTORY: usize = 128;

pub trait ProjectParentPicker {
    /// Real native parent-folder selection. Tests explicitly label their seam.
    fn select_parent(&mut self) -> Result<Option<PathBuf>, Code>;
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectFileProof {
    pub role: &'static str,
    pub bytes: usize,
    pub sha256: String,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectRecoveryView {
    pub operation_id: RequestId,
    pub historical_phase: &'static str,
    pub invalid_code: Option<Code>,
    pub payload_proofs: Vec<ProjectFileProof>,
    pub current_file_proof: bool,
}

pub(super) fn catalogue(root: &Path) -> Result<HashMap<RequestId, PathBuf>, Code> {
    let mut result = HashMap::new();
    match fs::symlink_metadata(root) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(result),
        Err(_) => return Err(Code::IOFailure),
        Ok(_) => (),
    }
    let pins = Pins::open(root)?;
    for entry in fs::read_dir(root).map_err(|_| Code::IOFailure)? {
        let entry = entry.map_err(|_| Code::IOFailure)?;
        if result.len() >= MAX_HISTORY {
            return Err(Code::TooLarge);
        }
        let name = entry
            .file_name()
            .into_string()
            .map_err(|_| Code::UnsupportedPath)?;
        let id_text = name.strip_suffix("-project").ok_or(Code::InvalidInput)?;
        let id: RequestId = serde_json::from_value(serde_json::Value::String(id_text.into()))
            .map_err(|_| Code::InvalidInput)?;
        let path = root.join(&name);
        Pins::open(&path)?.check()?;
        if result.insert(id, path).is_some() {
            return Err(Code::InvalidInput);
        }
    }
    pins.check()?;
    Ok(result)
}
#[derive(Clone, Debug, Serialize)]
#[serde(tag = "status", rename_all = "camelCase")]
pub enum ProjectStatus {
    Reserved {},
    Running {},
    Created {
        document: Candidate,
        files: Vec<ProjectFileProof>,
    },
    Cancelled {
        commit: &'static str,
    },
    Incomplete {
        code: Code,
        #[serde(rename = "mayHaveWritten")]
        may_have_written: bool,
    },
}
pub(super) struct Record {
    pub(super) owner: Caller,
    pub(super) cancel: Arc<AtomicBool>,
    document: DocumentId,
    revision: u64,
    source_hash: String,
    status: ProjectStatus,
}
impl Record {
    pub(super) fn pending(&self) -> bool {
        matches!(
            self.status,
            ProjectStatus::Reserved {} | ProjectStatus::Running {}
        )
    }
}

/// Non-Clone owned work; keeps cancellation/lifetime and the captured bytes.
pub struct ProjectWork {
    host: NativeHost,
    binding: Binding,
    request: RequestId,
    files: Option<Files>,
    directory: String,
    scope: Scope,
    cancel: Arc<AtomicBool>,
    armed: bool,
}

impl NativeHost {
    pub fn project_recovery_ids(&self, binding: &Binding) -> Result<Vec<RequestId>, Code> {
        let state = self.state.lock().map_err(|_| Code::Unavailable)?;
        self.authorized(&state, binding)?;
        Ok(self.project_ids_locked())
    }

    pub(super) fn project_ids_locked(&self) -> Vec<RequestId> {
        let mut ids: Vec<_> = self.project_catalogue.keys().cloned().collect();
        ids.sort_by(|a, b| a.as_str().cmp(b.as_str()));
        ids
    }

    pub fn inspect_project_recovery(
        &self,
        binding: &Binding,
        operation: &RequestId,
    ) -> Result<ProjectRecoveryView, Code> {
        {
            let state = self.state.lock().map_err(|_| Code::Unavailable)?;
            self.authorized(&state, binding)?;
        }
        let path = self
            .project_catalogue
            .get(operation)
            .ok_or(Code::UnknownRequest)?;
        let item =
            crate::fresh_project_recovery::CataloguedOperation::from_host_catalogued_directory(
                path, operation,
            )?;
        let inspected = item.inspect();
        use crate::fresh_project_recovery::HistoricalPhase;
        let phase = match inspected.phase {
            HistoricalPhase::Prepared => "prepared",
            HistoricalPhase::MayWrite => "may-write",
            HistoricalPhase::Verified => "verified",
            HistoricalPhase::Invalid => "invalid",
        };
        let files = inspected
            .payload_proofs
            .into_iter()
            .flatten()
            .map(|f| ProjectFileProof {
                role: f.role,
                bytes: f.bytes,
                sha256: f.sha256,
            })
            .collect();
        let state = self.state.lock().map_err(|_| Code::Unavailable)?;
        self.authorized(&state, binding)?;
        Ok(ProjectRecoveryView {
            operation_id: operation.clone(),
            historical_phase: phase,
            invalid_code: inspected.invalid_code,
            payload_proofs: files,
            current_file_proof: inspected.current_file_proof,
        })
    }

    pub fn prepare_fresh_project(
        &self,
        binding: &Binding,
        document: &DocumentId,
        revision: u64,
        directory: String,
        companions: [Vec<u8>; 3],
    ) -> Result<ProjectWork, Code> {
        let mut state = self.state.lock().map_err(|_| Code::Unavailable)?;
        self.prepare_fresh_project_locked(
            &mut state, binding, document, revision, directory, companions,
        )
    }

    pub(super) fn prepare_fresh_project_locked(
        &self,
        state: &mut State,
        binding: &Binding,
        document: &DocumentId,
        revision: u64,
        directory: String,
        companions: [Vec<u8>; 3],
    ) -> Result<ProjectWork, Code> {
        if revision > 9_007_199_254_740_991 {
            return Err(Code::InvalidInput);
        }
        if directory.is_empty()
            || directory.len() > 64
            || !directory
                .bytes()
                .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'_' | b'-'))
        {
            return Err(Code::InvalidInput);
        }
        let index = self.authorized(state, binding)?;
        let caller = state.registrations[index].caller.clone();
        if state.projects.values().filter(|r| r.pending()).count() >= MAX_PENDING
            || state
                .projects
                .values()
                .any(|r| r.owner == caller && r.pending())
            || state
                .registry
                .operations
                .values()
                .any(|e| e.owner == caller && !e.phase.is_terminal())
            || state
                .registry
                .callers
                .get(&caller)
                .is_some_and(|c| c.dialog.is_some())
        {
            return Err(Code::Busy);
        }
        let doc = state.registry.document(&caller, document)?;
        if doc.selection.is_some() || doc.version.is_some() {
            return Err(Code::InvalidInput);
        }
        let captured = doc.draft_capture.as_ref().ok_or(Code::Unavailable)?;
        if captured.revision != revision {
            return Err(Code::Conflict);
        }
        let source = captured.bytes.clone();
        let [manifest, cmake, traceability] = companions;
        let files = Files::new([source.clone(), manifest, cmake, traceability])?;
        let request = RequestId::mint()?;
        let cancel = Arc::new(AtomicBool::new(false));
        let scope = Scope {
            schema: 1,
            operation: request.clone(),
            session: caller.session.clone(),
            incarnation: caller.incarnation.clone(),
            document: document.clone(),
            version: None,
            source_bytes: source.len(),
            source_hash: digest(&source),
        };
        if state.projects.len() >= MAX_HISTORY {
            let old = state
                .projects
                .iter()
                .find(|(_, r)| !r.pending())
                .map(|(id, _)| id.clone())
                .ok_or(Code::Busy)?;
            state.projects.remove(&old);
        }
        state.projects.insert(
            request.clone(),
            Record {
                owner: caller,
                cancel: cancel.clone(),
                document: document.clone(),
                revision,
                source_hash: scope.source_hash.clone(),
                status: ProjectStatus::Reserved {},
            },
        );
        Ok(ProjectWork {
            host: self.clone(),
            binding: binding.clone(),
            request,
            files: Some(files),
            directory,
            scope,
            cancel,
            armed: true,
        })
    }

    pub fn project_status(
        &self,
        binding: &Binding,
        operation: &RequestId,
    ) -> Result<ProjectStatus, Code> {
        let state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.authorized(&state, binding)?;
        Self::project_status_locked(&state, &state.registrations[index].caller, operation, false)
    }

    pub(super) fn project_status_locked(
        state: &State,
        caller: &Caller,
        operation: &RequestId,
        cancel: bool,
    ) -> Result<ProjectStatus, Code> {
        let record = state.projects.get(operation).ok_or(Code::UnknownRequest)?;
        if &record.owner != caller {
            return Err(Code::Denied);
        }
        if cancel && record.pending() {
            record.cancel.store(true, Ordering::Release);
        }
        Ok(record.status.clone())
    }

    pub fn cancel_project(
        &self,
        binding: &Binding,
        operation: &RequestId,
    ) -> Result<ProjectStatus, Code> {
        let state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.authorized(&state, binding)?;
        // Intent does not fabricate completed cancellation.
        Self::project_status_locked(&state, &state.registrations[index].caller, operation, true)
    }

    pub fn has_project_work(&self, binding: &Binding) -> Result<bool, Code> {
        let state = self.state.lock().map_err(|_| Code::Unavailable)?;
        let index = self.index(&state, binding)?;
        let caller = &state.registrations[index].caller;
        Ok(state
            .projects
            .values()
            .any(|r| &r.owner == caller && r.pending()))
    }
}

impl ProjectWork {
    pub fn request_id(&self) -> &RequestId {
        &self.request
    }
    fn validate(&self, state: &State) -> Result<(), Code> {
        if self.cancel.load(Ordering::Acquire) {
            return Err(Code::Revoked);
        }
        let index = self.host.authorized(state, &self.binding)?;
        let record = state
            .projects
            .get(&self.request)
            .ok_or(Code::UnknownRequest)?;
        if record.owner != state.registrations[index].caller
            || !Arc::ptr_eq(&record.cancel, &self.cancel)
            || !record.pending()
        {
            return Err(Code::Denied);
        }
        let doc = state.registry.document(&record.owner, &record.document)?;
        let capture = doc.draft_capture.as_ref().ok_or(Code::Conflict)?;
        if doc.selection.is_some()
            || capture.revision != record.revision
            || digest(&capture.bytes) != record.source_hash
        {
            return Err(Code::Conflict);
        }
        Ok(())
    }
    fn settle(&mut self, status: ProjectStatus) -> Result<ProjectStatus, Code> {
        let mut state = self.host.state.lock().map_err(|_| Code::Unavailable)?;
        let record = state
            .projects
            .get_mut(&self.request)
            .ok_or(Code::UnknownRequest)?;
        record.status = status.clone();
        self.armed = false;
        Ok(status)
    }
    pub fn run(mut self, picker: &mut impl ProjectParentPicker) -> Result<ProjectStatus, Code> {
        {
            let mut state = self.host.state.lock().map_err(|_| Code::Unavailable)?;
            if let Err(code) = self.validate(&state) {
                drop(state);
                return self.settle(ProjectStatus::Incomplete {
                    code,
                    may_have_written: false,
                });
            }
            state
                .projects
                .get_mut(&self.request)
                .ok_or(Code::UnknownRequest)?
                .status = ProjectStatus::Running {};
        }
        let picked =
            std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| picker.select_parent()));
        let parent = match picked {
            Ok(Ok(Some(parent))) => parent,
            Ok(Ok(None)) => {
                return self.settle(ProjectStatus::Cancelled {
                    commit: "not-started",
                })
            }
            Ok(Err(code)) => {
                return self.settle(ProjectStatus::Incomplete {
                    code,
                    may_have_written: false,
                })
            }
            Err(_) => {
                return self.settle(ProjectStatus::Incomplete {
                    code: Code::IOFailure,
                    may_have_written: false,
                })
            }
        };
        {
            let state = self.host.state.lock().map_err(|_| Code::Unavailable)?;
            if let Err(code) = self.validate(&state) {
                drop(state);
                return self.settle(ProjectStatus::Incomplete {
                    code,
                    may_have_written: false,
                });
            }
        }
        let outcome = (|| {
            let storage_parent = self
                .host
                .project_storage
                .parent()
                .ok_or(Code::Unavailable)?;
            let parent_pins = Pins::open(storage_parent)?;
            match fs::create_dir(self.host.project_storage.as_path()) {
                Ok(()) => (),
                Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => (),
                Err(_) => return Err(Code::IOFailure),
            }
            parent_pins.check()?;
            Pins::open(self.host.project_storage.as_path())?.check()?;
            Plan::new(
                self.scope.clone(),
                &parent,
                &self.directory,
                self.host.project_storage.as_path(),
                self.files.take().ok_or(Code::Unavailable)?,
            )
        })();
        let plan = match outcome {
            Ok(plan) => plan,
            Err(code) => {
                return self.settle(ProjectStatus::Incomplete {
                    code,
                    may_have_written: false,
                })
            }
        };
        let created = match plan.execute(&self.cancel) {
            Ok(created) => created,
            Err(failure) => {
                return self.settle(ProjectStatus::Incomplete {
                    code: failure.code,
                    may_have_written: failure.may_have_written,
                })
            }
        };
        // Keep all result locks alive across SAME-document baseline adoption.
        let mut state = self.host.state.lock().map_err(|_| Code::Unavailable)?;
        if let Err(code) = self.validate(&state) {
            drop(state);
            return self.settle(ProjectStatus::Incomplete {
                code,
                may_have_written: true,
            });
        }
        let version = Version::mint()?;
        let document = state
            .registry
            .documents
            .get_mut(&self.scope.document)
            .ok_or(Code::Revoked)?;
        document.selection = Some(created.source.clone());
        document.version = Some(version.clone());
        document.draft_capture = None;
        let candidate = Candidate {
            document_id: self.scope.document.clone(),
            source_base64: STANDARD.encode(&created.source.bytes),
            saved_base64: Some(STANDARD.encode(&created.source.bytes)),
            binding: Some(crate::types::Binding {
                version,
                display_name: crate::display(&created.source),
            }),
        };
        let files = created
            .files
            .iter()
            .map(|f| ProjectFileProof {
                role: f.role,
                bytes: f.bytes,
                sha256: f.sha256.clone(),
            })
            .collect();
        let status = ProjectStatus::Created {
            document: candidate,
            files,
        };
        state
            .projects
            .get_mut(&self.request)
            .ok_or(Code::UnknownRequest)?
            .status = status.clone();
        self.armed = false;
        Ok(status)
    }
}
impl Drop for ProjectWork {
    fn drop(&mut self) {
        if self.armed {
            if let Ok(mut state) = self.host.state.lock() {
                if let Some(record) = state.projects.get_mut(&self.request) {
                    record.cancel.store(true, Ordering::Release);
                    record.status = ProjectStatus::Incomplete {
                        code: Code::Unavailable,
                        may_have_written: matches!(record.status, ProjectStatus::Running {}),
                    };
                }
            }
        }
    }
}

#[cfg(test)]
#[path = "host_fresh_project_tests.rs"]
mod tests;
