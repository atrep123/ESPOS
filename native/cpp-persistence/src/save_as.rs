//! Rust-only native capture/target contract. Not an installed IPC capability.
use crate::{
    Caller, Code, DocumentId, Outcome, Registry, Request, RequestId, ReserveRequest, Start, Status,
};
use serde::Serialize;

#[derive(Clone)]
pub(crate) struct CapturedDraft {
    pub(crate) revision: u64,
    pub(crate) bytes: Vec<u8>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DraftBinding {
    pub request_id: RequestId,
    pub document_id: DocumentId,
    pub capture_revision: u64,
    pub source_hash: String,
    pub source_bytes: usize,
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn same_registry_capture_is_immutable_native_operation_input() {
        let mut registry = Registry::new().unwrap();
        let caller = registry.attach_caller().unwrap();
        let payload = vec![0xef, 0xbb, 0xbf, 0xff, 0, 13, 10];
        let binding = registry
            .bind_captured_draft(&caller, 73, payload.clone())
            .unwrap();
        let d = registry.document(&caller, &binding.document_id).unwrap();
        assert!(d.selection.is_none());
        assert!(d.version.is_none());
        let captured = d.draft_capture.as_ref().unwrap();
        assert_eq!(captured.revision, 73);
        assert_eq!(captured.bytes, payload);
        assert_eq!(binding.source_hash, crate::windows_write::digest(&payload));
    }
    #[test]
    fn capture_size_limit_precedes_new_grant() {
        let mut registry = Registry::new().unwrap();
        let caller = registry.attach_caller().unwrap();
        assert!(matches!(
            registry.bind_captured_draft(&caller, 0, vec![0; crate::MAX_SOURCE_BYTES + 1]),
            Err(Code::TooLarge)
        ));
        assert_eq!(registry.documents.len(), 0);
    }
    #[test]
    fn other_caller_cannot_use_real_captured_document() {
        let mut registry = Registry::new().unwrap();
        let a = registry.attach_caller().unwrap();
        let b = registry.attach_caller().unwrap();
        let draft = registry.bind_captured_draft(&a, 0, b"x".to_vec()).unwrap();
        assert!(matches!(
            registry.reserve_request(
                &b,
                ReserveRequest::ChooseTarget {
                    document_id: draft.document_id
                }
            ),
            Err(Code::Denied)
        ));
    }
    #[test]
    fn owner_revision_source_and_unissued_target_are_denied_without_consumption() {
        let mut registry = Registry::new().unwrap();
        let caller = registry.attach_caller().unwrap();
        let draft = registry
            .bind_captured_draft(&caller, 3, b"x".to_vec())
            .unwrap();
        // TESTONLY invalid/unissued ID, not a fabricated valid target grant.
        let target: crate::TargetId =
            serde_json::from_str("\"target_00000000000000000000000000000000\"").unwrap();
        assert!(matches!(
            registry.reserve_save_as(&caller, &draft.document_id, &target, 4, b"x".to_vec()),
            Err(Code::Conflict)
        ));
        assert!(matches!(
            registry.reserve_save_as(&caller, &draft.document_id, &target, 3, b"y".to_vec()),
            Err(Code::Conflict)
        ));
        assert!(matches!(
            registry.reserve_save_as(&caller, &draft.document_id, &target, 3, b"x".to_vec()),
            Err(Code::Denied)
        ));
        assert!(registry
            .document(&caller, &draft.document_id)
            .unwrap()
            .draft_capture
            .is_some());
    }
}
impl Registry {
    pub fn validate_draft_target_request(
        &self,
        caller: &Caller,
        id: &RequestId,
        document: &DocumentId,
    ) -> Result<(), Code> {
        let e = self.entry(caller, id)?;
        if e.operation != crate::Operation::ChooseTarget(document.clone()) {
            return Err(Code::InvalidInput);
        }
        Ok(())
    }
    /// Caller already authenticated by the SAME Host. Revision is an owner
    /// correlation value, never sender/window/file authority. Immutable bytes
    /// are a pending operation input, not another editable document owner.
    pub fn bind_captured_draft(
        &mut self,
        caller: &Caller,
        revision: u64,
        bytes: Vec<u8>,
    ) -> Result<DraftBinding, Code> {
        self.authorize(caller)?;
        if bytes.len() > crate::MAX_SOURCE_BYTES {
            return Err(Code::TooLarge);
        }
        let request = self.reserve_request(caller, ReserveRequest::New {})?;
        let result = self.new_document(
            caller,
            Request {
                request_id: request.clone(),
            },
        )?;
        let Start::Ready(Status::Complete {
            result: Outcome::Created { document },
            ..
        }) = result
        else {
            return Err(Code::Unavailable);
        };
        let grant = self
            .documents
            .get_mut(&document.document_id)
            .ok_or(Code::Denied)?;
        if grant.selection.is_some() || grant.version.is_some() {
            return Err(Code::Denied);
        }
        let hash = crate::windows_write::digest(&bytes);
        let len = bytes.len();
        grant.draft_capture = Some(CapturedDraft { revision, bytes });
        Ok(DraftBinding {
            request_id: request,
            document_id: document.document_id,
            capture_revision: revision,
            source_hash: hash,
            source_bytes: len,
        })
    }
}
