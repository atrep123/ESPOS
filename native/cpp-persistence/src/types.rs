use base64::{engine::general_purpose::STANDARD, Engine};
use serde::{Deserialize, Serialize};

pub const MAX_SOURCE_BYTES: usize = 1024 * 1024;
pub const MAX_REQUEST_JSON_BYTES: usize = 1024;
pub const MAX_GRANTS: usize = 32; // documents + provisional targets, registry-wide
pub const MAX_SETTLED_OPS: usize = 128;
pub const MAX_UNRESOLVED_OPS: usize = 32; // reservations + pending reads; never evict
pub const MAX_CALLERS: usize = 8;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Code {
    Denied,
    Busy,
    InvalidInput,
    TooLarge,
    UnsupportedPath,
    IOFailure,
    Conflict,
    UnknownRequest,
    Revoked,
    Unavailable,
}

macro_rules! opaque_id {
    ($name:ident, $prefix:literal) => {
        #[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize)]
        #[serde(transparent)]
        pub struct $name(String);
        impl $name {
            pub(crate) fn mint() -> Result<Self, Code> {
                Ok(Self(format!(
                    "{}{}",
                    $prefix,
                    crate::windows_read::random_hex()?
                )))
            }
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
                let value = String::deserialize(d)?;
                let suffix = value
                    .strip_prefix($prefix)
                    .ok_or_else(|| serde::de::Error::custom("invalid opaque ID"))?;
                if suffix.len() != 32
                    || !suffix
                        .bytes()
                        .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
                {
                    return Err(serde::de::Error::custom("invalid opaque ID"));
                }
                Ok(Self(value))
            }
        }
    };
}
opaque_id!(DocumentId, "doc_");
opaque_id!(TargetId, "target_");
opaque_id!(RequestId, "request_");
opaque_id!(Version, "version_");

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Request {
    pub request_id: RequestId,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct TargetRequest {
    pub request_id: RequestId,
    pub document_id: DocumentId,
}

/// Bounded lifecycle intent only. Neither caller identity, request IDs nor
/// filesystem paths are accepted from a reservation payload.
#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "operation", rename_all = "camelCase", deny_unknown_fields)]
pub enum ReserveRequest {
    // Empty struct variants intentionally enforce unknown-field rejection.
    // Serde internally tagged unit variants can otherwise discard extra keys.
    New {},
    Open {},
    ChooseTarget {
        #[serde(rename = "documentId")]
        document_id: DocumentId,
    },
}

impl From<ReserveRequest> for Operation {
    fn from(value: ReserveRequest) -> Self {
        match value {
            ReserveRequest::New {} => Self::New,
            ReserveRequest::Open {} => Self::Open,
            ReserveRequest::ChooseTarget { document_id } => Self::ChooseTarget(document_id),
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "kind", rename_all = "camelCase", deny_unknown_fields)]
pub enum Release {
    Document {
        #[serde(rename = "documentId")]
        document_id: DocumentId,
    },
    Target {
        #[serde(rename = "targetGrantId")]
        target_grant_id: TargetId,
    },
}

pub fn decode_request<T: serde::de::DeserializeOwned>(input: &[u8]) -> Result<T, Code> {
    if input.len() > MAX_REQUEST_JSON_BYTES {
        return Err(Code::TooLarge);
    }
    serde_json::from_slice(input).map_err(|_| Code::InvalidInput)
}

// Shared validation for the future writer, NOT a save endpoint/receipt.
pub fn decode_source(input: &str) -> Result<Vec<u8>, Code> {
    if input.len() > MAX_SOURCE_BYTES.div_ceil(3) * 4 {
        return Err(Code::TooLarge);
    }
    let bytes = STANDARD.decode(input).map_err(|_| Code::InvalidInput)?;
    if bytes.len() > MAX_SOURCE_BYTES {
        return Err(Code::TooLarge);
    }
    if STANDARD.encode(&bytes) != input {
        return Err(Code::InvalidInput);
    }
    Ok(bytes)
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Operation {
    New,
    Open,
    ChooseTarget(DocumentId),
    Save(DocumentId),
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Binding {
    pub version: Version,
    pub display_name: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Candidate {
    pub document_id: DocumentId,
    pub source_base64: String,
    pub saved_base64: Option<String>,
    pub binding: Option<Binding>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "kind", rename_all = "camelCase")]
pub enum TargetState {
    Absent,
    Existing { version: Version },
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "status", rename_all = "camelCase")]
pub enum Outcome {
    Created {
        document: Candidate,
    },
    Opened {
        document: Candidate,
    },
    Selected {
        #[serde(rename = "targetGrantId")]
        target_grant_id: TargetId,
        #[serde(rename = "documentId")]
        document_id: DocumentId,
        #[serde(rename = "displayName")]
        display_name: String,
        #[serde(rename = "targetState")]
        target_state: TargetState,
    },
    Cancelled {
        commit: &'static str,
    },
    Failed {
        commit: &'static str,
        code: Code,
    },
    // Explicitly invalidates previously returned candidate IDs; never recreate.
    Revoked,
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "status", rename_all = "camelCase")]
pub enum Status {
    Save {
        write: crate::writer::SaveView,
    },
    Reserved,
    Pending {
        #[serde(rename = "cancelRequested")]
        cancel_requested: bool,
    },
    Complete {
        operation: &'static str,
        result: Outcome,
    },
}
