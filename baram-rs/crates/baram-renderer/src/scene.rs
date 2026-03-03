// ════════════════════════════════════════════════════════════════
//  Scene Graph — arena‑based hierarchy inspired by Fyrox Engine
//
//  Fyrox Editor → Custom plugins → Hedron geometry → wgpu compute
// ════════════════════════════════════════════════════════════════

use glam::{Mat4, Quat, Vec3};
use std::hash::{Hash, Hasher};
use std::marker::PhantomData;

// ── Handle (generational index) ────────────────────────────────

/// A generational index into an [`Arena`]. Modelled after Fyrox's
/// `Handle<T>` so the scene graph never stores raw pointers.
///
/// Manual trait impls avoid requiring `T: Copy/Eq/Hash` bounds.
pub struct Handle<T> {
    pub(crate) index: u32,
    pub(crate) generation: u32,
    _marker: PhantomData<T>,
}

// Manual impls — no bounds on T ─────────────────────────────────
impl<T> std::fmt::Debug for Handle<T> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Handle")
            .field("index", &self.index)
            .field("generation", &self.generation)
            .finish()
    }
}
impl<T> Clone for Handle<T> {
    fn clone(&self) -> Self { *self }
}
impl<T> Copy for Handle<T> {}
impl<T> PartialEq for Handle<T> {
    fn eq(&self, other: &Self) -> bool {
        self.index == other.index && self.generation == other.generation
    }
}
impl<T> Eq for Handle<T> {}
impl<T> Hash for Handle<T> {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.index.hash(state);
        self.generation.hash(state);
    }
}

impl<T> Handle<T> {
    pub fn index(&self) -> u32 { self.index }
    pub fn generation(&self) -> u32 { self.generation }

    pub const NONE: Self = Self {
        index: u32::MAX,
        generation: 0,
        _marker: PhantomData,
    };
    pub fn is_none(&self) -> bool {
        self.index == u32::MAX
    }
    pub fn is_some(&self) -> bool {
        !self.is_none()
    }
}


impl<T> Default for Handle<T> {
    fn default() -> Self {
        Self::NONE
    }
}

// ── Arena ──────────────────────────────────────────────────────

struct ArenaEntry<T> {
    generation: u32,
    value: Option<T>,
}

/// A simple generational arena (object pool).
pub struct Arena<T> {
    entries: Vec<ArenaEntry<T>>,
    free_list: Vec<u32>,
    len: usize,
}

impl<T> Arena<T> {
    pub fn new() -> Self {
        Self {
            entries: Vec::new(),
            free_list: Vec::new(),
            len: 0,
        }
    }

    pub fn insert(&mut self, value: T) -> Handle<T> {
        self.len += 1;
        if let Some(idx) = self.free_list.pop() {
            let e = &mut self.entries[idx as usize];
            e.generation += 1;
            e.value = Some(value);
            Handle { index: idx, generation: e.generation, _marker: PhantomData }
        } else {
            let index = self.entries.len() as u32;
            self.entries.push(ArenaEntry { generation: 0, value: Some(value) });
            Handle { index, generation: 0, _marker: PhantomData }
        }
    }

    pub fn remove(&mut self, h: Handle<T>) -> Option<T> {
        if h.is_none() { return None; }
        let e = self.entries.get_mut(h.index as usize)?;
        if e.generation != h.generation { return None; }
        self.len -= 1;
        self.free_list.push(h.index);
        e.value.take()
    }

    pub fn get(&self, h: Handle<T>) -> Option<&T> {
        if h.is_none() { return None; }
        let e = self.entries.get(h.index as usize)?;
        if e.generation != h.generation { return None; }
        e.value.as_ref()
    }

    pub fn get_mut(&mut self, h: Handle<T>) -> Option<&mut T> {
        if h.is_none() { return None; }
        let e = self.entries.get_mut(h.index as usize)?;
        if e.generation != h.generation { return None; }
        e.value.as_mut()
    }

    pub fn len(&self) -> usize { self.len }
    pub fn is_empty(&self) -> bool { self.len == 0 }

    /// Iterate over all live entries with their handles.
    pub fn iter(&self) -> impl Iterator<Item = (Handle<T>, &T)> {
        self.entries.iter().enumerate().filter_map(|(i, e)| {
            e.value.as_ref().map(|v| {
                (Handle { index: i as u32, generation: e.generation, _marker: PhantomData }, v)
            })
        })
    }
}

// ── Transform ──────────────────────────────────────────────────

/// Decomposed 3‑D transform (TRS).
#[derive(Debug, Clone)]
pub struct Transform3D {
    pub position: Vec3,
    pub rotation: Quat,
    pub scale: Vec3,
}

impl Default for Transform3D {
    fn default() -> Self {
        Self { position: Vec3::ZERO, rotation: Quat::IDENTITY, scale: Vec3::ONE }
    }
}

impl Transform3D {
    pub fn matrix(&self) -> Mat4 {
        Mat4::from_scale_rotation_translation(self.scale, self.rotation, self.position)
    }
}

// ── Node component ─────────────────────────────────────────────

/// Payload attached to each scene node (Fyrox‑style component).
#[derive(Debug, Clone)]
pub enum NodeComponent {
    Empty,
    /// Reference to a GPU mesh (index into `Scene::meshes`).
    Mesh { mesh_index: usize, visible: bool },
    /// A named boundary surface (for boundary‑condition colouring).
    Boundary { boundary_name: String, color: [f32; 4] },
    /// A named cell zone.
    CellZone { zone_name: String, color: [f32; 4] },
    /// A CSG primitive leaf in the Hedron geometry tree.
    CsgPrimitive(super::hedron::CsgPrimitive),
    /// Directional light.
    Light { direction: Vec3, color: Vec3, intensity: f32 },
}

// ── Scene node ─────────────────────────────────────────────────

/// A single node in the hierarchy.
#[derive(Debug, Clone)]
pub struct SceneNode {
    pub name: String,
    pub transform: Transform3D,
    pub parent: Handle<SceneNode>,
    pub children: Vec<Handle<SceneNode>>,
    pub visible: bool,
    pub component: NodeComponent,
}

impl SceneNode {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            transform: Transform3D::default(),
            parent: Handle::NONE,
            children: Vec::new(),
            visible: true,
            component: NodeComponent::Empty,
        }
    }
}

// ── Scene ──────────────────────────────────────────────────────

/// The complete scene graph.
pub struct Scene {
    pub nodes: Arena<SceneNode>,
    pub root_nodes: Vec<Handle<SceneNode>>,
    pub selected: Handle<SceneNode>,
}

impl Scene {
    pub fn new() -> Self {
        Self {
            nodes: Arena::new(),
            root_nodes: Vec::new(),
            selected: Handle::NONE,
        }
    }

    /// Insert a top‑level node.
    pub fn add_root_node(&mut self, node: SceneNode) -> Handle<SceneNode> {
        let h = self.nodes.insert(node);
        self.root_nodes.push(h);
        h
    }

    /// Insert a child node under `parent`.
    pub fn add_child_node(
        &mut self,
        parent: Handle<SceneNode>,
        mut node: SceneNode,
    ) -> Handle<SceneNode> {
        node.parent = parent;
        let child = self.nodes.insert(node);
        if let Some(p) = self.nodes.get_mut(parent) {
            p.children.push(child);
        }
        child
    }

    /// Compute world‑space transform by walking up the parent chain.
    pub fn world_transform(&self, handle: Handle<SceneNode>) -> Mat4 {
        let mut chain = Vec::new();
        let mut cur = handle;
        while let Some(n) = self.nodes.get(cur) {
            chain.push(n.transform.matrix());
            cur = n.parent;
        }
        chain.iter().rev().fold(Mat4::IDENTITY, |acc, m| acc * *m)
    }

    /// Remove a node (and detach from parent/children).
    pub fn remove_node(&mut self, handle: Handle<SceneNode>) {
        if let Some(node) = self.nodes.get(handle) {
            let parent = node.parent;
            let children: Vec<_> = node.children.clone();
            // Detach from parent
            if let Some(p) = self.nodes.get_mut(parent) {
                p.children.retain(|c| *c != handle);
            }
            self.root_nodes.retain(|r| *r != handle);
            // Orphan children → root
            for child in &children {
                if let Some(c) = self.nodes.get_mut(*child) {
                    c.parent = Handle::NONE;
                }
                self.root_nodes.push(*child);
            }
        }
        self.nodes.remove(handle);
    }
}
