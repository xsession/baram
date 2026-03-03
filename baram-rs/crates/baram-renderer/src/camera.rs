use glam::{Mat4, Vec3};
use bytemuck::{Pod, Zeroable};

// ════════════════════════════════════════════════════════════════
//  Orbit Camera — orbit/pan/zoom like Fusion 360 / VTK style
// ════════════════════════════════════════════════════════════════

#[repr(C)]
#[derive(Debug, Clone, Copy, Pod, Zeroable)]
pub struct CameraUniform {
    pub view_proj: [[f32; 4]; 4],
    pub eye:       [f32; 4],
}

pub struct OrbitCamera {
    pub target: Vec3,
    pub distance: f32,
    pub azimuth: f32,   // radians
    pub elevation: f32, // radians
    pub fov_y: f32,     // radians
    pub near: f32,
    pub far: f32,
    pub aspect: f32,
    pub pan_offset: Vec3,
}

impl Default for OrbitCamera {
    fn default() -> Self {
        Self {
            target: Vec3::ZERO,
            distance: 5.0,
            azimuth: std::f32::consts::FRAC_PI_4,
            elevation: std::f32::consts::FRAC_PI_6,
            fov_y: 45.0f32.to_radians(),
            near: 0.01,
            far: 10000.0,
            aspect: 16.0 / 9.0,
            pan_offset: Vec3::ZERO,
        }
    }
}

impl OrbitCamera {
    pub fn eye_position(&self) -> Vec3 {
        let x = self.distance * self.elevation.cos() * self.azimuth.cos();
        let y = self.distance * self.elevation.sin();
        let z = self.distance * self.elevation.cos() * self.azimuth.sin();
        self.target + self.pan_offset + Vec3::new(x, y, z)
    }

    pub fn view_matrix(&self) -> Mat4 {
        let eye = self.eye_position();
        let center = self.target + self.pan_offset;
        Mat4::look_at_rh(eye, center, Vec3::Y)
    }

    pub fn projection_matrix(&self) -> Mat4 {
        Mat4::perspective_rh(self.fov_y, self.aspect, self.near, self.far)
    }

    pub fn view_proj(&self) -> Mat4 {
        self.projection_matrix() * self.view_matrix()
    }

    pub fn uniform(&self) -> CameraUniform {
        let eye = self.eye_position();
        CameraUniform {
            view_proj: self.view_proj().to_cols_array_2d(),
            eye: [eye.x, eye.y, eye.z, 1.0],
        }
    }

    /// Rotate around the target.
    pub fn orbit(&mut self, delta_azimuth: f32, delta_elevation: f32) {
        self.azimuth += delta_azimuth;
        self.elevation = (self.elevation + delta_elevation).clamp(
            -std::f32::consts::FRAC_PI_2 + 0.01,
            std::f32::consts::FRAC_PI_2 - 0.01,
        );
    }

    /// Zoom in/out.
    pub fn zoom(&mut self, factor: f32) {
        self.distance *= factor;
        self.distance = self.distance.max(0.01);
    }

    /// Pan the camera.
    pub fn pan(&mut self, dx: f32, dy: f32) {
        let view = self.view_matrix();
        let right = Vec3::new(view.col(0).x, view.col(1).x, view.col(2).x);
        let up = Vec3::new(view.col(0).y, view.col(1).y, view.col(2).y);
        self.pan_offset += right * dx * self.distance * 0.002;
        self.pan_offset += up * (-dy) * self.distance * 0.002;
    }

    /// Fit the camera to a bounding box.
    pub fn fit_to_bounds(&mut self, center: Vec3, diagonal: f32) {
        self.target = center;
        self.pan_offset = Vec3::ZERO;
        self.distance = diagonal * 1.5;
    }

    /// Set standard views.
    pub fn set_front(&mut self) {
        self.azimuth = 0.0;
        self.elevation = 0.0;
    }
    pub fn set_top(&mut self) {
        self.azimuth = 0.0;
        self.elevation = std::f32::consts::FRAC_PI_2 - 0.01;
    }
    pub fn set_right(&mut self) {
        self.azimuth = std::f32::consts::FRAC_PI_2;
        self.elevation = 0.0;
    }
    pub fn set_isometric(&mut self) {
        self.azimuth = std::f32::consts::FRAC_PI_4;
        self.elevation = std::f32::consts::FRAC_PI_6;
    }
}
