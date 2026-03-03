use baram_core::types::mesh::Bounds;

// ════════════════════════════════════════════════════════════════
//  Bounds utilities — AABB computation for meshes
// ════════════════════════════════════════════════════════════════

/// Compute AABB from a slice of f64 points.
pub fn bounds_from_points(points: &[[f64; 3]]) -> Bounds {
    let mut b = Bounds::default();
    for p in points {
        b.expand(p);
    }
    b
}

/// Compute AABB from f32 positions (GPU vertex data).
pub fn bounds_from_f32(positions: &[[f32; 3]]) -> Bounds {
    let mut b = Bounds::default();
    for p in positions {
        let p64 = [p[0] as f64, p[1] as f64, p[2] as f64];
        b.expand(&p64);
    }
    b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn aabb_basic() {
        let pts = vec![
            [0.0, 0.0, 0.0],
            [1.0, 2.0, 3.0],
            [-1.0, -2.0, -3.0],
        ];
        let b = bounds_from_points(&pts);
        assert_eq!(b.min, [-1.0, -2.0, -3.0]);
        assert_eq!(b.max, [1.0, 2.0, 3.0]);
        let c = b.center();
        assert!((c[0]).abs() < 1e-12);
    }
}
