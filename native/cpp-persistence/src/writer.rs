//! Native writer inside the same Registry, not a second source owner/store.
//! No installed Tauri commands. Existing sender/navigation admission stays closed.
use crate::windows_read::Selection;
use crate::windows_write::{self, HeldTarget, Journal, Prepared, Revision, Scope};
use crate::{Caller, Code, DocumentId, Operation, Phase, Registry, RequestId, Version};
use serde::Serialize;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};

/// Native environment for human-selected files in a conventional local,
/// cooperative application. App storage is supplied by the trusted host.
/// Held handles and verified receipts detect conflicts within this model;
/// they do not promise service isolation, same-user exclusion or power-loss safety.
pub struct WriterEnvironment {
    pub(crate) journal: Journal,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Deserialize)]
pub enum ConflictDecision {
    Stop,
    OverwriteWithActualBackup,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SaveView {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub save_as: Option<SaveAsIdentity>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub adoption: Option<AdoptedBinding>,
    pub operation_id: RequestId,
    pub document_id: DocumentId,
    pub captured_version: Option<Version>,
    pub source_hash: String,
    pub source_bytes: usize,
    pub phase: &'static str,
    pub reason: Option<Code>,
    pub cancel_requested: bool,
    /// Hash is DISPLAY/observation only; a caller cannot install a revision.
    pub external_hash: Option<String>,
    pub external_bytes: Option<usize>,
    pub choices: Vec<&'static str>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SaveAsIdentity {
    pub target_grant_id: crate::TargetId,
    pub capture_revision: u64,
    pub target_absent: bool,
}
#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AdoptedBinding {
    pub document_id: DocumentId,
    pub version: Version,
}
struct SaveAsPlan {
    identity: SaveAsIdentity,
}

enum State {
    Ready,
    Running,
    Conflict(Revision),
    NotStarted(Code),
    Written,
    Unknown,
}
pub(crate) struct Record {
    pub(crate) document: DocumentId,
    save_as: Option<SaveAsPlan>,
    adopted: Option<AdoptedBinding>,
    verified_selection: Option<Selection>,
    new_version: Version,
    document_version: Option<Version>,
    document_capture: Option<crate::save_as::CapturedDraft>,
    scope: Scope,
    selection: Selection,
    bytes: Vec<u8>,
    state: State,
    pub(crate) cancel: Arc<AtomicBool>,
    attempt: Option<Arc<()>>,
    artifacts: Option<Prepared>,
}
impl Record {
    pub(crate) fn cancel_intent(&mut self) {
        self.cancel.store(true, Ordering::Release);
        if matches!(self.state, State::Ready | State::Conflict(_)) {
            self.state = State::NotStarted(Code::Revoked);
        }
    }
    pub(crate) fn blocks_replacement(&self) -> bool {
        !matches!(self.state, State::NotStarted(_) | State::Written)
    }
    pub(crate) fn view(&self) -> SaveView {
        let (phase, reason, external, choices) = match &self.state {
            State::Ready => ("reserved", None, None, vec!["stop"]),
            State::Running => ("pending", None, None, vec!["stop-and-recover"]),
            State::Conflict(revision) => (
                "external-conflict",
                Some(Code::Conflict),
                Some(revision),
                vec!["stop", "overwrite-with-actual-backup"],
            ),
            State::NotStarted(code) => (
                "not-started",
                Some(*code),
                None,
                vec!["stop", "new-confirmed-attempt"],
            ),
            State::Written => ("written", None, None, vec![]),
            State::Unknown => ("recovery-required", None, None, vec!["stop-and-recover"]),
        };
        SaveView {
            save_as: self.save_as.as_ref().map(|p| p.identity.clone()),
            adoption: self.adopted.clone(),
            operation_id: self.scope.operation.clone(),
            document_id: self.document.clone(),
            captured_version: self.scope.version.clone(),
            source_hash: windows_write::digest(&self.bytes),
            source_bytes: self.bytes.len(),
            phase,
            reason,
            cancel_requested: self.cancel.load(Ordering::Acquire),
            external_hash: external.map(|r| windows_write::digest(&r.bytes)),
            external_bytes: external.map(|r| r.bytes.len()),
            choices,
        }
    }
}

/// Non-clone work; original caller/grant/source/attempt are privately captured.
pub struct WriteJob {
    scope: Scope,
    selection: Selection,
    bytes: Vec<u8>,
    confirmed: Option<Revision>,
    cancel: Arc<AtomicBool>,
    attempt: Arc<()>,
    save_as: bool,
}
pub struct WriteCompletion {
    scope: Scope,
    attempt: Arc<()>,
    effect: Effect,
}
enum Effect {
    Conflict(Revision),
    NotStarted(Code),
    Written(Prepared, Selection),
    Unknown(Option<Prepared>),
}
pub enum SaveStart {
    Ready(SaveView),
    Work(WriteJob),
}

impl Registry {
    pub fn reserve_save(
        &mut self,
        caller: &Caller,
        document: &DocumentId,
        version: &Version,
        bytes: Vec<u8>,
    ) -> Result<RequestId, Code> {
        self.authorize(caller)?;
        if self.has_saved_app_work(caller) {
            return Err(Code::Busy);
        }
        if bytes.len() > crate::MAX_SOURCE_BYTES {
            return Err(Code::TooLarge);
        }
        if self.operations.values().any(|e| {
            e.owner == *caller && matches!(&e.phase,Phase::Writer(r) if r.blocks_replacement())
        }) {
            return Err(Code::Busy);
        }
        let grant = self.document(caller, document)?;
        if grant.version.as_ref() != Some(version) {
            return Err(Code::Conflict);
        }
        let selection = grant.selection.clone().ok_or(Code::Unavailable)?;
        // Same initial source surface as owned jobs: deny ALL headers and aliases
        // before a writer read/hash. No credential file is opened by this stage.
        windows_write::admit_source_path(&selection.path)?;
        if selection.writer_revision.is_none() {
            return Err(Code::Unavailable);
        }
        let document_capture = grant.draft_capture.clone();
        // Reserve the historical identity before the job can mutate any file.
        let new_version = Version::mint()?;
        let request = self.reserve(caller, Operation::Save(document.clone()))?;
        let scope = Scope {
            schema: 1,
            operation: request.clone(),
            session: caller.session.clone(),
            incarnation: caller.incarnation.clone(),
            document: document.clone(),
            version: Some(version.clone()),
            source_hash: windows_write::digest(&bytes),
            source_bytes: bytes.len(),
        };
        self.operations
            .get_mut(&request)
            .ok_or(Code::UnknownRequest)?
            .phase = Phase::Writer(Box::new(Record {
            document: document.clone(),
            save_as: None,
            adopted: None,
            verified_selection: None,
            scope,
            selection,
            bytes,
            state: State::Ready,
            new_version,
            document_version: Some(version.clone()),
            document_capture,
            cancel: Arc::new(AtomicBool::new(false)),
            attempt: None,
            artifacts: None,
        }));
        Ok(request)
    }
    pub fn save_view(&self, caller: &Caller, id: &RequestId) -> Result<SaveView, Code> {
        let Phase::Writer(record) = &self.entry(caller, id)?.phase else {
            return Err(Code::InvalidInput);
        };
        Ok(record.view())
    }
    /// Explicit first attempt only. Replay returns the actual state, NEVER writes.
    pub fn begin_save(&mut self, caller: &Caller, id: &RequestId) -> Result<SaveStart, Code> {
        self.entry(caller, id)?;
        let Phase::Writer(record) = &mut self
            .operations
            .get_mut(id)
            .ok_or(Code::UnknownRequest)?
            .phase
        else {
            return Err(Code::InvalidInput);
        };
        if !matches!(record.state, State::Ready) {
            return Ok(SaveStart::Ready(record.view()));
        }
        if record.cancel.load(Ordering::Acquire) {
            record.state = State::NotStarted(Code::Revoked);
            let view = record.view();
            self.remember_terminal(id);
            return Ok(SaveStart::Ready(view));
        }
        Ok(SaveStart::Work(record.work(None)))
    }
    /// This SAME operation's one native external observation is confirmed. It
    /// cannot be replaced by a caller revision/hash/path. Further change stops it.
    pub fn confirm_save(
        &mut self,
        caller: &Caller,
        id: &RequestId,
        decision: ConflictDecision,
    ) -> Result<SaveStart, Code> {
        self.entry(caller, id)?;
        let Phase::Writer(record) = &mut self
            .operations
            .get_mut(id)
            .ok_or(Code::UnknownRequest)?
            .phase
        else {
            return Err(Code::InvalidInput);
        };
        let State::Conflict(revision) = &record.state else {
            return Ok(SaveStart::Ready(record.view()));
        };
        if decision == ConflictDecision::Stop || record.cancel.load(Ordering::Acquire) {
            record.state = State::NotStarted(Code::Revoked);
            let view = record.view();
            self.remember_terminal(id);
            return Ok(SaveStart::Ready(view));
        }
        let revision = revision.clone();
        Ok(SaveStart::Work(record.work(Some(revision))))
    }
    /// Only native WriteJob can construct completion. Revocation does NOT change
    /// Written/Unknown to Cancelled; completion drains the original incarnation.
    pub fn complete_save(&mut self, completion: WriteCompletion) -> Result<SaveView, Code> {
        let entry = self
            .operations
            .get_mut(&completion.scope.operation)
            .ok_or(Code::UnknownRequest)?;
        if entry.owner.session != completion.scope.session
            || entry.owner.incarnation != completion.scope.incarnation
        {
            return Err(Code::Denied);
        }
        let owner = entry.owner.clone();
        let Phase::Writer(record) = &mut entry.phase else {
            return Err(Code::InvalidInput);
        };
        if record.scope != completion.scope
            || !matches!(record.state, State::Running)
            || !record
                .attempt
                .as_ref()
                .is_some_and(|a| Arc::ptr_eq(a, &completion.attempt))
        {
            return Err(Code::Denied);
        }
        record.attempt = None;
        match completion.effect {
            Effect::Conflict(revision) => record.state = State::Conflict(revision),
            Effect::NotStarted(code) => record.state = State::NotStarted(code),
            Effect::Unknown(artifacts) => {
                record.artifacts = artifacts;
                record.state = State::Unknown;
            }
            Effect::Written(artifacts, selection) => {
                record.artifacts = Some(artifacts);
                record.verified_selection = Some(selection);
                record.state = State::Written;
            }
        }
        let id = record.scope.operation.clone();
        self.adopt_saved_binding(&id)?;
        self.remember_terminal(&id);
        self.release_drained_writer_grants(&owner);
        let Phase::Writer(record) = &self.operations.get(&id).ok_or(Code::UnknownRequest)?.phase
        else {
            return Err(Code::InvalidInput);
        };
        Ok(record.view())
    }
    /// Status-only, explicit recovery. No retry/rollback/restore/target mutation.
    /// Missing/untrusted artifacts remain Unknown, not caller-chosen failed.
    pub fn recover_save(
        &mut self,
        caller: &Caller,
        id: &RequestId,
        environment: &mut WriterEnvironment,
    ) -> Result<SaveView, Code> {
        self.entry(caller, id)?;
        let Phase::Writer(record) = &mut self
            .operations
            .get_mut(id)
            .ok_or(Code::UnknownRequest)?
            .phase
        else {
            return Err(Code::InvalidInput);
        };
        if !matches!(record.state, State::Unknown | State::Written) {
            return Ok(record.view());
        }
        if matches!(record.state, State::Written) && record.adopted.is_some() {
            return Ok(record.view());
        }
        if let Some(artifacts) = &record.artifacts {
            if let Ok(selection) = environment.journal.verify_written_selection(
                &record.scope,
                artifacts,
                &record.selection.path,
            ) {
                environment.journal.finish_verified(&record.scope)?;
                record.verified_selection = Some(selection);
                record.state = State::Written;
            }
        }
        self.adopt_saved_binding(id)?;
        self.remember_terminal(id);
        let Phase::Writer(record) = &self.operations.get(id).ok_or(Code::UnknownRequest)?.phase
        else {
            return Err(Code::InvalidInput);
        };
        Ok(record.view())
    }
    /// Consume target ONCE. All validation/mint/reservation succeeds before
    /// removing it. No filesystem paths, external revisions or backup claims
    /// are accepted from caller/frontend inputs.
    pub fn reserve_save_as(
        &mut self,
        caller: &Caller,
        document: &DocumentId,
        target: &crate::TargetId,
        capture_revision: u64,
        bytes: Vec<u8>,
    ) -> Result<RequestId, Code> {
        self.authorize(caller)?;
        if self.has_saved_app_work(caller) {
            return Err(Code::Busy);
        }
        if self.operations.values().any(|e| {
            e.owner == *caller && matches!(&e.phase,Phase::Writer(r) if r.blocks_replacement())
        }) {
            return Err(Code::Busy);
        }
        let grant = self.document(caller, document)?;
        let capture = grant.draft_capture.as_ref().ok_or(Code::Denied)?;
        if capture.revision != capture_revision || capture.bytes != bytes {
            return Err(Code::Conflict);
        }
        let document_version = grant.version.clone();
        let document_capture = grant.draft_capture.clone();
        let selected = self
            .targets
            .get(target)
            .filter(|t| t.owner == *caller && t.document == *document)
            .ok_or(Code::Denied)?;
        // None is genuine absent selection, never a fabricated file Version.
        let version = selected.version.clone();
        let target_absent = selected.selection.file.is_none();
        if target_absent != version.is_none() {
            return Err(Code::Denied);
        }
        let selection = selected.selection.clone();
        windows_write::admit_source_path(&selection.path)?;
        let new_version = Version::mint()?;
        let request = self.reserve(caller, Operation::Save(document.clone()))?;
        let scope = Scope {
            schema: 1,
            operation: request.clone(),
            session: caller.session.clone(),
            incarnation: caller.incarnation.clone(),
            document: document.clone(),
            version,
            source_hash: windows_write::digest(&bytes),
            source_bytes: bytes.len(),
        };
        self.operations
            .get_mut(&request)
            .ok_or(Code::UnknownRequest)?
            .phase = Phase::Writer(Box::new(Record {
            document: document.clone(),
            scope,
            selection,
            bytes,
            state: State::Ready,
            save_as: Some(SaveAsPlan {
                identity: SaveAsIdentity {
                    target_grant_id: target.clone(),
                    capture_revision,
                    target_absent,
                },
            }),
            new_version,
            document_version,
            document_capture,
            adopted: None,
            verified_selection: None,
            cancel: Arc::new(AtomicBool::new(false)),
            attempt: None,
            artifacts: None,
        }));
        self.targets.remove(target);
        Ok(request)
    }
    pub fn save_as_reserved_version(
        &self,
        caller: &Caller,
        id: &RequestId,
    ) -> Result<Version, Code> {
        let Phase::Writer(r) = &self.entry(caller, id)?.phase else {
            return Err(Code::InvalidInput);
        };
        r.save_as.as_ref().ok_or(Code::InvalidInput)?;
        Ok(r.new_version.clone())
    }
    /// Historical identity allocated at reservation, including ordinary Save.
    pub fn save_reserved_version(&self, caller: &Caller, id: &RequestId) -> Result<Version, Code> {
        let Phase::Writer(r) = &self.entry(caller, id)?.phase else {
            return Err(Code::InvalidInput);
        };
        Ok(r.new_version.clone())
    }
    fn adopt_saved_binding(&mut self, id: &RequestId) -> Result<(), Code> {
        let e = self.operations.get(id).ok_or(Code::UnknownRequest)?;
        let Phase::Writer(r) = &e.phase else {
            return Err(Code::InvalidInput);
        };
        if !matches!(r.state, State::Written) || r.adopted.is_some() {
            return Ok(());
        }
        // A revoked caller may drain Written but can never acquire a new grant.
        if self.authorize(&e.owner).is_err() {
            return Ok(());
        }
        let Some(selection) = r.verified_selection.clone() else {
            return Ok(());
        };
        // Byte equality alone is insufficient: retain the original owner/version
        // and exact draft capture, never acquiring a newer draft's authority.
        if selection.bytes != r.bytes
            || selection.path != r.selection.path
            || selection.sha256 != Some(windows_write::digest_raw(&r.bytes))
            || selection
                .writer_revision
                .as_ref()
                .is_none_or(|v| v.bytes != r.bytes || !v.ordinary())
        {
            return Ok(());
        }
        let Some(grant) = self
            .documents
            .get(&r.document)
            .filter(|d| d.owner == e.owner)
        else {
            return Ok(());
        };
        if grant.version != r.document_version {
            return Ok(());
        }
        let capture_matches = match (&grant.draft_capture, &r.document_capture) {
            (None, None) => true,
            (Some(a), Some(b)) => a.revision == b.revision && a.bytes == b.bytes,
            _ => false,
        };
        if !capture_matches {
            return Ok(());
        }
        if let Some(plan) = &r.save_as {
            if !grant
                .draft_capture
                .as_ref()
                .is_some_and(|c| c.revision == plan.identity.capture_revision && c.bytes == r.bytes)
            {
                return Ok(());
            }
        } else if !grant.selection.as_ref().is_some_and(|s| {
            s.path == r.selection.path
                && s.parent == r.selection.parent
                && s.file == r.selection.file
                && s.bytes == r.selection.bytes
                && s.sha256 == r.selection.sha256
                && s.writer_revision == r.selection.writer_revision
        }) {
            return Ok(());
        }
        let document = r.document.clone();
        let version = r.new_version.clone();
        let grant = self.documents.get_mut(&document).ok_or(Code::Denied)?;
        grant.project = grant
            .project
            .as_ref()
            .and_then(|p| p.saved_source(&selection));
        let saved_capture = if grant.project.is_some() {
            grant
                .draft_capture
                .take()
                .filter(|c| c.bytes == selection.bytes)
        } else {
            None
        };
        grant.selection = Some(selection);
        grant.version = Some(version.clone());
        grant.draft_capture = saved_capture;
        let Phase::Writer(r) = &mut self
            .operations
            .get_mut(id)
            .ok_or(Code::UnknownRequest)?
            .phase
        else {
            return Err(Code::InvalidInput);
        };
        r.adopted = Some(AdoptedBinding {
            document_id: document,
            version,
        });
        Ok(())
    }
}
impl Record {
    fn work(&mut self, confirmed: Option<Revision>) -> WriteJob {
        let attempt = Arc::new(());
        self.attempt = Some(attempt.clone());
        self.state = State::Running;
        WriteJob {
            scope: self.scope.clone(),
            selection: self.selection.clone(),
            bytes: self.bytes.clone(),
            confirmed,
            cancel: self.cancel.clone(),
            attempt,
            save_as: self.save_as.is_some(),
        }
    }
}
impl WriteJob {
    pub fn undispatched(self) -> WriteCompletion {
        WriteCompletion {
            scope: self.scope,
            attempt: self.attempt,
            effect: Effect::NotStarted(Code::Unavailable),
        }
    }
    pub fn run(self, environment: &mut WriterEnvironment) -> WriteCompletion {
        // Keep an owned recovery reference BEFORE any journal/target operation.
        let mut artifacts = None;
        let mut uncertain = false;
        let effect = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            self.execute(environment, &mut artifacts, &mut uncertain)
        }))
        .unwrap_or(Effect::Unknown(artifacts.clone()));
        WriteCompletion {
            scope: self.scope,
            attempt: self.attempt,
            effect,
        }
    }
    fn execute(
        &self,
        environment: &mut WriterEnvironment,
        artifacts: &mut Option<Prepared>,
        uncertain: &mut bool,
    ) -> Effect {
        let result = (|| -> Result<Effect, Code> {
            if self.cancel.load(Ordering::Acquire) {
                return Ok(Effect::NotStarted(Code::Revoked));
            }
            if self.save_as && self.selection.file.is_none() && self.confirmed.is_none() {
                return match crate::create_target::execute_create(
                    &self.scope,
                    &self.selection.path,
                    &self.selection.parent,
                    &self.bytes,
                    &self.cancel,
                    &environment.journal,
                    artifacts,
                    uncertain,
                )? {
                    crate::create_target::CreatedEffect::Existing(r) => Ok(Effect::Conflict(r)),
                    crate::create_target::CreatedEffect::Written(p, s) => Ok(Effect::Written(p, s)),
                };
            }
            let mut target = HeldTarget::open(&self.selection.path)?;
            let external = target.snapshot()?;
            target.check_namespace()?;
            let ordinary = external.ordinary();
            if !ordinary {
                return Err(Code::UnsupportedPath);
            }
            if let Some(confirmed) = &self.confirmed {
                if !external.same_revision(confirmed) {
                    return Err(Code::Conflict);
                }
            } else if self.save_as {
                // Existing targets always need approval of this exact native
                // observation; a target picker is not overwrite confirmation.
                return Ok(Effect::Conflict(external));
            } else {
                let original = self
                    .selection
                    .writer_revision
                    .as_ref()
                    .ok_or(Code::Unavailable)?;
                if !external.same_revision(original) {
                    return Ok(Effect::Conflict(external));
                }
            }
            // Check the conventional local journal and held target namespace.
            environment.journal.check_domain(&target)?;
            target.recheck(&external)?;
            let prepared = environment.journal.prepare(
                &self.scope,
                &self.selection.path,
                &external,
                &self.bytes,
            )?;
            *artifacts = Some(prepared.clone());
            target.recheck(&external)?;
            environment.journal.check_domain(&target)?;
            if self.cancel.load(Ordering::Acquire) {
                return Ok(Effect::NotStarted(Code::Revoked));
            }
            // Uncertainty starts BEFORE durable marker append and BEFORE first
            // target syscall. A failed marker flush cannot be called Untouched.
            *uncertain = true;
            environment.journal.mark_may_write(&self.scope, &prepared)?;
            target.recheck(&external)?;
            target.update(&self.bytes, &self.cancel)?;
            let after = target.snapshot()?;
            target.check_namespace()?;
            if !after.same_object_metadata(&external)
                || after.bytes != self.bytes
                || !after.ordinary()
            {
                return Err(Code::Conflict);
            }
            environment
                .journal
                .record_written(&self.scope, &prepared, &after)?;
            target.recheck(&after)?;
            environment.journal.check_domain(&target)?;
            let selection = target.selection(&after)?;
            environment.journal.finish_verified(&self.scope)?;
            Ok(Effect::Written(prepared, selection))
        })();
        match result {
            Ok(effect) => effect,
            Err(code) if !*uncertain => Effect::NotStarted(code),
            Err(_) => Effect::Unknown(artifacts.clone()),
        }
    }
}

#[cfg(test)]
#[path = "writer_tests.rs"]
mod tests;
