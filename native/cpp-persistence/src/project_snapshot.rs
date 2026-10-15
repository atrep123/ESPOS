//! Private fixed-role NTFS provenance. No source-ancestor or journal adoption.
use crate::{
    fresh_project::{exact_layout, member, Files, ROLES},
    windows_read::Selection,
    windows_write::{HeldTarget, Pins, Revision},
    *,
};
use std::path::{Path, PathBuf};

/// Opaque native revision of all four member baselines. No DTO representation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProjectRevision(String);

pub(crate) struct Namespace {
    root: PathBuf,
    pins: Vec<Pins>,
}
impl Namespace {
    fn open(root: &Path) -> Result<Self, Code> {
        windows_read::validate_path(&member(root, ROLES[0]))?;
        let pins = ["", "app", "app/src", "docs"]
            .into_iter()
            .map(|role| {
                Pins::open(&if role.is_empty() {
                    root.to_path_buf()
                } else {
                    member(root, role)
                })
            })
            .collect::<Result<Vec<_>, _>>()?;
        let value = Self {
            root: root.to_path_buf(),
            pins,
        };
        value.check()?;
        Ok(value)
    }
    fn check(&self) -> Result<(), Code> {
        for pins in &self.pins {
            pins.check()?;
        }
        exact_layout(&self.root)
    }
}

#[derive(Clone)]
pub(crate) struct Provenance {
    namespace: Arc<Namespace>,
    pub(crate) members: [Revision; 4],
    pub(crate) revision: ProjectRevision,
}
impl Provenance {
    // A verified same-object Save advances just the admitted source baseline.
    // Save As outside the native-captured root invalidates the association.
    pub(crate) fn saved_source(&self, selection: &Selection) -> Option<Self> {
        let source = selection.writer_revision.as_ref()?;
        if selection.path != member(&self.namespace.root, ROLES[0])
            || !source.ordinary()
            || !source.same_object_metadata(&self.members[0])
        {
            return None;
        }
        let mut value = self.clone();
        value.members[0] = source.clone();
        value.revision = ProjectRevision(windows_read::random_hex().ok()?);
        Some(value)
    }
}

pub(crate) struct HeldApp {
    namespace: Arc<Namespace>,
    // Real READ-only SHARE_READ handles prevent writes/deletes until Drop.
    handles: [HeldTarget; 4],
    pub(crate) members: [Revision; 4],
}
fn cap(index: usize) -> usize {
    if index == 0 {
        MAX_SOURCE_BYTES
    } else {
        65_536
    }
}
impl HeldApp {
    pub(crate) fn open(root: &Path) -> Result<Self, Code> {
        Self::capture(Arc::new(Namespace::open(root)?))
    }
    fn capture(namespace: Arc<Namespace>) -> Result<Self, Code> {
        namespace.check()?;
        let mut handles = (0..ROLES.len())
            .map(|role| HeldTarget::read_project_member(&namespace.root, role))
            .collect::<Result<Vec<_>, _>>()?;
        let mut revisions = Vec::new();
        for (index, held) in handles.iter_mut().enumerate() {
            let revision = held.project_snapshot_bounded(cap(index))?;
            if !revision.ordinary() {
                return Err(Code::UnsupportedPath);
            }
            held.check_namespace()?;
            revisions.push(revision);
        }
        let members: [Revision; 4] = revisions.try_into().map_err(|_| Code::Unavailable)?;
        Files::new(std::array::from_fn(|i| members[i].bytes.clone()))?;
        namespace.check()?;
        Ok(Self {
            namespace,
            handles: handles.try_into().map_err(|_| Code::Unavailable)?,
            members,
        })
    }
    pub(crate) fn from_provenance(provenance: &Provenance) -> Result<Self, Code> {
        let mut held = Self::capture(provenance.namespace.clone())?;
        held.check(&provenance.members)?;
        Ok(held)
    }
    pub(crate) fn provenance(&self) -> Result<Provenance, Code> {
        Ok(Provenance {
            namespace: self.namespace.clone(),
            members: self.members.clone(),
            revision: ProjectRevision(windows_read::random_hex()?),
        })
    }
    pub(crate) fn source(&self) -> Result<Selection, Code> {
        self.handles[0].selection(&self.members[0])
    }
    pub(crate) fn check(&mut self, expected: &[Revision; 4]) -> Result<(), Code> {
        self.namespace.check()?;
        for (i, held) in self.handles.iter_mut().enumerate() {
            let fresh = held.project_snapshot_bounded(cap(i))?;
            if !fresh.ordinary() || !fresh.same_revision(&expected[i]) {
                return Err(Code::Conflict);
            }
            held.check_namespace()?;
        }
        self.namespace.check()
    }
}

impl Registry {
    pub(crate) fn has_saved_app_work(&self, caller: &Caller) -> bool {
        self.documents
            .values()
            .any(|d| d.owner == *caller && d.project_lease.is_some())
    }
}
