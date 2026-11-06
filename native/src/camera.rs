//! Orbit camera — the same parameterisation and framing constants as
//! the web shell (`web/viewer.js`): azimuth / polar angle / radius
//! around a target, vertical FOV 0.72 rad, near 0.5 cm, far 2000 cm.
//!
//! Canonical frame: x+ = subject right, y+ = up, z+ = anterior.
//! az = 0 puts the eye on +z (anterior): the front view. The eye is
//!   target + radius * (sin(pol)*sin(az), cos(pol), sin(pol)*cos(az))
//! exactly as in the web shell.

use glam::{Mat4, Vec3};

pub const FOV_Y: f32 = 0.72;
pub const NEAR: f32 = 0.5;
pub const FAR: f32 = 2000.0;
pub const HOME_RADIUS: f32 = 300.0;

#[derive(Debug, Clone, Copy)]
pub struct OrbitCamera {
    pub az: f32,
    pub pol: f32,
    pub radius: f32,
    pub target: Vec3,
}

impl OrbitCamera {
    pub fn new(target: Vec3) -> Self {
        OrbitCamera {
            az: 0.0,
            pol: 1.35,
            radius: HOME_RADIUS,
            target,
        }
    }

    pub fn eye(&self) -> Vec3 {
        let (sp, cp) = (self.pol.sin(), self.pol.cos());
        self.target
            + self.radius * Vec3::new(sp * self.az.sin(), cp, sp * self.az.cos())
    }

    pub fn view(&self) -> Mat4 {
        Mat4::look_at_rh(self.eye(), self.target, Vec3::Y)
    }

    /// View with an explicit up vector (the top view: eye on +y makes
    /// the default y-up degenerate).
    pub fn view_with_up(&self, up: Vec3) -> Mat4 {
        Mat4::look_at_rh(self.eye(), self.target, up)
    }

    pub fn proj(&self, aspect: f32) -> Mat4 {
        Mat4::perspective_rh(FOV_Y, aspect, NEAR, FAR)
    }

    pub fn mvp(&self, aspect: f32) -> Mat4 {
        self.proj(aspect) * self.view()
    }

    pub fn mvp_with_up(&self, aspect: f32, up: Vec3) -> Mat4 {
        self.proj(aspect) * self.view_with_up(up)
    }
}

/// Project a canonical-cm point to framebuffer pixel coordinates
/// (origin top-left, y down) under `mvp`. Returns None when the point
/// is on or behind the camera plane (clip w <= 0).
pub fn project(mvp: &Mat4, p: Vec3, width: u32, height: u32) -> Option<(f32, f32)> {
    let clip = mvp * p.extend(1.0);
    if clip.w <= 0.0 {
        return None;
    }
    let ndc = clip.truncate() / clip.w;
    Some((
        (ndc.x * 0.5 + 0.5) * width as f32,
        (1.0 - (ndc.y * 0.5 + 0.5)) * height as f32,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn eye_front_at_az0_equator() {
        let cam = OrbitCamera {
            az: 0.0,
            pol: std::f32::consts::FRAC_PI_2,
            radius: 100.0,
            target: Vec3::new(1.0, 2.0, 3.0),
        };
        let eye = cam.eye();
        assert!((eye - Vec3::new(1.0, 2.0, 103.0)).length() < 1e-4, "eye={eye}");
    }

    #[test]
    fn target_projects_to_frame_centre() {
        let cam = OrbitCamera::new(Vec3::new(0.0, 78.0, 11.0));
        let mvp = cam.mvp(1.0);
        let (x, y) = project(&mvp, cam.target, 1024, 1024).expect("target in front");
        assert!((x - 512.0).abs() < 0.01 && (y - 512.0).abs() < 0.01, "({x},{y})");
    }

    #[test]
    fn point_behind_camera_rejected() {
        let cam = OrbitCamera::new(Vec3::ZERO);
        let mvp = cam.mvp(1.0);
        let behind = cam.eye() + (cam.eye() - cam.target);
        assert!(project(&mvp, behind, 100, 100).is_none());
    }
}
