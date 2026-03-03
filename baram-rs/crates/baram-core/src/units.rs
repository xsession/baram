use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Unit System — physical quantity units used throughout BARAM
// ════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum QuantityKind {
    #[default]
    Dimensionless,
    Length,
    Area,
    Volume,
    Velocity,
    Acceleration,
    Pressure,
    Temperature,
    Density,
    DynamicViscosity,
    KinematicViscosity,
    ThermalConductivity,
    SpecificHeat,
    MassFlowRate,
    VolumeFlowRate,
    Force,
    Moment,
    Power,
    Energy,
    Frequency,
    AngularVelocity,
    MolecularWeight,
    TurbulentKineticEnergy,
    TurbulentDissipationRate,
    SpecificDissipationRate,
    Time,
}

/// Conversion factor to/from SI base
#[derive(Debug, Clone)]
pub struct UnitDef {
    pub kind: QuantityKind,
    pub symbol: &'static str,
    pub to_si: f64,   // multiply by this to get SI
    pub offset: f64,   // for temperature: T_si = (value + offset) * to_si
}

/// Convert a value from the given unit symbol to SI.
pub fn to_si(value: f64, unit: &UnitDef) -> f64 {
    (value + unit.offset) * unit.to_si
}

/// Convert a value from SI to the given unit symbol.
pub fn from_si(value: f64, unit: &UnitDef) -> f64 {
    value / unit.to_si - unit.offset
}

// ─── Common unit constants ────────────────────────────────────
pub const METER: UnitDef = UnitDef { kind: QuantityKind::Length, symbol: "m",  to_si: 1.0, offset: 0.0 };
pub const MM:    UnitDef = UnitDef { kind: QuantityKind::Length, symbol: "mm", to_si: 1e-3, offset: 0.0 };
pub const CM:    UnitDef = UnitDef { kind: QuantityKind::Length, symbol: "cm", to_si: 1e-2, offset: 0.0 };
pub const INCH:  UnitDef = UnitDef { kind: QuantityKind::Length, symbol: "in", to_si: 0.0254, offset: 0.0 };

pub const KELVIN:     UnitDef = UnitDef { kind: QuantityKind::Temperature, symbol: "K",  to_si: 1.0,       offset: 0.0 };
pub const CELSIUS:    UnitDef = UnitDef { kind: QuantityKind::Temperature, symbol: "°C", to_si: 1.0,       offset: 273.15 };
pub const FAHRENHEIT: UnitDef = UnitDef { kind: QuantityKind::Temperature, symbol: "°F", to_si: 5.0/9.0,   offset: 459.67 };

pub const PASCAL: UnitDef = UnitDef { kind: QuantityKind::Pressure, symbol: "Pa",  to_si: 1.0, offset: 0.0 };
pub const KPA:    UnitDef = UnitDef { kind: QuantityKind::Pressure, symbol: "kPa", to_si: 1e3, offset: 0.0 };
pub const ATM:    UnitDef = UnitDef { kind: QuantityKind::Pressure, symbol: "atm", to_si: 101325.0, offset: 0.0 };

pub const MPS:   UnitDef = UnitDef { kind: QuantityKind::Velocity, symbol: "m/s",   to_si: 1.0, offset: 0.0 };
pub const KMPH:  UnitDef = UnitDef { kind: QuantityKind::Velocity, symbol: "km/h",  to_si: 1.0/3.6, offset: 0.0 };

pub const KG_M3: UnitDef = UnitDef { kind: QuantityKind::Density, symbol: "kg/m³", to_si: 1.0, offset: 0.0 };
pub const PA_S:  UnitDef = UnitDef { kind: QuantityKind::DynamicViscosity, symbol: "Pa·s", to_si: 1.0, offset: 0.0 };
pub const M2_S:  UnitDef = UnitDef { kind: QuantityKind::KinematicViscosity, symbol: "m²/s", to_si: 1.0, offset: 0.0 };

pub const SECOND: UnitDef = UnitDef { kind: QuantityKind::Time, symbol: "s", to_si: 1.0, offset: 0.0 };
pub const RPM:    UnitDef = UnitDef { kind: QuantityKind::AngularVelocity, symbol: "RPM", to_si: std::f64::consts::TAU / 60.0, offset: 0.0 };
pub const RADS:   UnitDef = UnitDef { kind: QuantityKind::AngularVelocity, symbol: "rad/s", to_si: 1.0, offset: 0.0 };
