use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Boundary Condition Types — complete port of boundary_db.py
// ════════════════════════════════════════════════════════════════

/// Physical boundary condition type (28 types)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum BoundaryType {
    // ── Inlets (10) ──
    VelocityInlet,
    FlowRateInlet,
    PressureInlet,
    IntakeFan,
    AblInlet,
    OpenChannelInlet,
    FreeStream,
    FarFieldRiemann,
    SubsonicInlet,
    SupersonicInflow,
    // ── Outlets (7) ──
    FlowRateOutlet,
    PressureOutlet,
    ExhaustFan,
    OpenChannelOutlet,
    Outflow,
    SubsonicOutflow,
    SupersonicOutflow,
    // ── Walls (4) ──
    Wall,
    ThermoCoupledWall,
    PorousJump,
    Fan,
    // ── Internal / Special (5) ──
    Symmetry,
    Interface,
    Empty,
    Cyclic,
    Wedge,
}

impl BoundaryType {
    /// Category for UI grouping and color coding.
    pub fn category(&self) -> BoundaryCategory {
        match self {
            Self::VelocityInlet
            | Self::FlowRateInlet
            | Self::PressureInlet
            | Self::IntakeFan
            | Self::AblInlet
            | Self::OpenChannelInlet
            | Self::FreeStream
            | Self::FarFieldRiemann
            | Self::SubsonicInlet
            | Self::SupersonicInflow => BoundaryCategory::Inlet,

            Self::FlowRateOutlet
            | Self::PressureOutlet
            | Self::ExhaustFan
            | Self::OpenChannelOutlet
            | Self::Outflow
            | Self::SubsonicOutflow
            | Self::SupersonicOutflow => BoundaryCategory::Outlet,

            Self::Wall | Self::ThermoCoupledWall => BoundaryCategory::Wall,
            Self::PorousJump | Self::Fan => BoundaryCategory::Fan,
            Self::Symmetry => BoundaryCategory::Symmetry,
            Self::Interface => BoundaryCategory::Interface,
            Self::Cyclic | Self::Wedge => BoundaryCategory::Cyclic,
            Self::Empty => BoundaryCategory::Empty,
        }
    }

    /// Whether this BC type requires a coupled boundary partner.
    pub fn needs_coupled_boundary(&self) -> bool {
        matches!(
            self,
            Self::ThermoCoupledWall
                | Self::PorousJump
                | Self::Fan
                | Self::Interface
                | Self::Cyclic
        )
    }

    /// RGB color for FlowEFD-style rendering.
    pub fn color_rgb(&self) -> [f32; 3] {
        match self.category() {
            BoundaryCategory::Inlet     => [0.2, 0.5, 0.9],   // blue
            BoundaryCategory::Outlet    => [0.9, 0.3, 0.2],   // red
            BoundaryCategory::Wall      => [0.7, 0.7, 0.7],   // gray
            BoundaryCategory::Symmetry  => [0.3, 0.8, 0.4],   // green
            BoundaryCategory::Interface => [0.7, 0.4, 0.9],   // purple
            BoundaryCategory::Fan       => [0.9, 0.85, 0.3],  // yellow
            BoundaryCategory::Cyclic    => [0.2, 0.7, 0.7],   // teal
            BoundaryCategory::Empty     => [0.5, 0.5, 0.5],   // dim gray
        }
    }
}

/// High-level boundary category for grouping.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum BoundaryCategory {
    Inlet,
    Outlet,
    Wall,
    Symmetry,
    Interface,
    Fan,
    Cyclic,
    Empty,
}

/// Geometrical type for OpenFOAM polyMesh boundary file.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum GeometricalType {
    Patch,
    Wall,
    MappedWall,
    Cyclic,
    CyclicAmi,
    Symmetry,
    Empty,
    Wedge,
}

impl BoundaryType {
    pub fn geometrical_type(&self) -> GeometricalType {
        match self {
            Self::Wall | Self::ThermoCoupledWall => GeometricalType::Wall,
            Self::Symmetry => GeometricalType::Symmetry,
            Self::Empty => GeometricalType::Empty,
            Self::Wedge => GeometricalType::Wedge,
            Self::Cyclic => GeometricalType::CyclicAmi,
            Self::Interface => GeometricalType::CyclicAmi,
            _ => GeometricalType::Patch,
        }
    }
}

// ─── Velocity specification enums ─────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum VelocitySpecification {
    #[default]
    Component,
    MagnitudeNormal,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum VelocityProfile {
    #[default]
    Constant,
    SpatialDistribution,
    TemporalDistribution,
}

// ─── Flow rate specification ──────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum FlowRateSpecification {
    #[default]
    VolumeFlowRate,
    MassFlowRate,
}

// ─── Free-stream direction ────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DirectionSpecificationMethod {
    #[default]
    Direct,
    /// Angle of Attack / Angle of Sideslip
    AoaAos,
}

// ─── Wall conditions ──────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum WallMotion {
    #[default]
    StationaryWall,
    MovingWall,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum MovingWallMotion {
    #[default]
    TranslationalMotion,
    RotationalMotion,
    MeshMotion,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ShearCondition {
    #[default]
    NoSlip,
    Slip,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum WallTemperature {
    #[default]
    Adiabatic,
    ConstantTemperature,
    ConstantHeatFlux,
    Convection,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ContactAngleModel {
    #[default]
    Disable,
    Constant,
    Dynamic,
}

// ─── Interface conditions ─────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum InterfaceMode {
    #[default]
    InternalInterface,
    RotationalPeriodic,
    TranslationalPeriodic,
    RegionInterface,
}

// ─── Turbulence BC specification ──────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum SpalartAllmarasSpec {
    #[default]
    ModifiedTurbulentViscosity,
    TurbulentViscosityRatio,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum KEpsilonSpec {
    #[default]
    KAndEpsilon,
    IntensityAndViscosityRatio,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum KOmegaSpec {
    #[default]
    KAndOmega,
    IntensityAndViscosityRatio,
}

// ─── Temperature profile ──────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum TemperatureProfile {
    #[default]
    Constant,
    SpatialDistribution,
    TemporalDistribution,
}

// ─── DPM patch interaction ────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum PatchInteractionType {
    #[default]
    Escape,
    Reflect,
    Recycle,
}

// ════════════════════════════════════════════════════════════════
//  Boundary Condition Data Structures
// ════════════════════════════════════════════════════════════════

/// A single boundary condition with all its parameters.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundaryCondition {
    pub id: i64,
    pub name: String,
    pub region: String,
    pub bc_type: BoundaryType,
    pub coupled_boundary: Option<i64>,

    pub velocity: VelocityBc,
    pub pressure: PressureBc,
    pub temperature: TemperatureBc,
    pub turbulence: TurbulenceBc,
    pub wall: WallBc,
    pub interface: InterfaceBc,
    pub porous_jump: PorousJumpBc,
    pub free_stream: FreeStreamBc,
    pub far_field: FarFieldBc,
    pub flow_rate: FlowRateBc,
    pub open_channel: OpenChannelBc,
    pub subsonic: SubsonicBc,
    pub supersonic: SupersonicBc,
    pub dpm: DpmBc,

    /// Per-material volume fraction values (VOF)
    pub volume_fractions: Vec<(i64, f64)>,
    /// Per-species mass fraction values
    pub species: Vec<(i64, f64)>,
    /// Per-UDS values
    pub user_defined_scalars: Vec<(i64, f64)>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct VelocityBc {
    pub specification: VelocitySpecification,
    pub profile: VelocityProfile,
    pub component: [f64; 3],
    pub magnitude: f64,
    /// CSV data reference for spatial/temporal distributions
    pub profile_data_id: Option<i64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PressureBc {
    pub pressure: f64,
    pub non_reflective: bool,
    pub calculated_backflow: bool,
    pub backflow_total_temperature: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemperatureBc {
    pub profile: TemperatureProfile,
    pub value: f64,
    pub profile_data_id: Option<i64>,
}

impl Default for TemperatureBc {
    fn default() -> Self {
        Self {
            profile: TemperatureProfile::Constant,
            value: 300.0,
            profile_data_id: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TurbulenceBc {
    pub spalart_allmaras: SpalartAllmarasSpec,
    pub sa_modified_viscosity: f64,
    pub sa_viscosity_ratio: f64,
    pub k_epsilon: KEpsilonSpec,
    pub k: f64,
    pub epsilon: f64,
    pub k_omega: KOmegaSpec,
    pub omega: f64,
    pub intensity: f64,
    pub viscosity_ratio: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct WallBc {
    pub motion: WallMotion,
    pub moving_motion: MovingWallMotion,
    pub shear_condition: ShearCondition,
    pub translational_velocity: [f64; 3],
    pub rotation_axis_origin: [f64; 3],
    pub rotation_axis_direction: [f64; 3],
    pub rotating_speed: f64,
    pub temperature: WallTemperature,
    pub constant_temperature: f64,
    pub heat_flux: f64,
    pub convection_coefficient: f64,
    pub free_stream_temperature: f64,
    pub roughness_height: f64,
    pub roughness_constant: f64,
    pub contact_angle: ContactAngleModel,
    pub static_contact_angle: f64,
    pub advancing_contact_angle: f64,
    pub receding_contact_angle: f64,
    pub wall_layers: Vec<WallLayer>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WallLayer {
    pub thickness: f64,
    pub conductivity: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct InterfaceBc {
    pub mode: InterfaceMode,
    pub rotation_axis_origin: [f64; 3],
    pub rotation_axis_direction: [f64; 3],
    pub rotation_angle: f64,
    pub translation_vector: [f64; 3],
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PorousJumpBc {
    pub darcy_coefficient: f64,
    pub inertial_coefficient: f64,
    pub porous_media_thickness: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FreeStreamBc {
    pub direction_method: DirectionSpecificationMethod,
    pub flow_direction: [f64; 3],
    pub angle_of_attack: f64,
    pub angle_of_sideslip: f64,
    pub drag_direction: [f64; 3],
    pub lift_direction: [f64; 3],
    pub free_stream_velocity: f64,
    pub pressure: f64,
    pub temperature: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FarFieldBc {
    pub flow_direction: [f64; 3],
    pub mach_number: f64,
    pub static_pressure: f64,
    pub static_temperature: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FlowRateBc {
    pub specification: FlowRateSpecification,
    pub volume_flow_rate: f64,
    pub mass_flow_rate: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct OpenChannelBc {
    pub volume_flow_rate: f64,
    pub mean_velocity: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SubsonicBc {
    pub flow_direction: [f64; 3],
    pub total_pressure: f64,
    pub total_temperature: f64,
    pub static_pressure: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SupersonicBc {
    pub velocity: [f64; 3],
    pub static_pressure: f64,
    pub static_temperature: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DpmBc {
    pub interaction: PatchInteractionType,
}

impl Default for BoundaryCondition {
    fn default() -> Self {
        Self {
            id: 0,
            name: String::new(),
            region: String::new(),
            bc_type: BoundaryType::Wall,
            coupled_boundary: None,
            velocity: VelocityBc::default(),
            pressure: PressureBc::default(),
            temperature: TemperatureBc::default(),
            turbulence: TurbulenceBc::default(),
            wall: WallBc::default(),
            interface: InterfaceBc::default(),
            porous_jump: PorousJumpBc::default(),
            free_stream: FreeStreamBc::default(),
            far_field: FarFieldBc::default(),
            flow_rate: FlowRateBc::default(),
            open_channel: OpenChannelBc::default(),
            subsonic: SubsonicBc::default(),
            supersonic: SupersonicBc::default(),
            dpm: DpmBc::default(),
            volume_fractions: Vec::new(),
            species: Vec::new(),
            user_defined_scalars: Vec::new(),
        }
    }
}
