"""
casper.models
=============

Shared domain models for Casper_Fusion.

These models define the system's data contracts:
- sensor measurements
- fused estimates
- telemetry records
- enums for sensor and system state

No runtime logic. No Streamlit dependencies.
"""

from enum import Enum
from typing import Dict, Any

import numpy as np
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================
# ENUMS
# ============================================================

class SensorType(str, Enum):
    IMU = "IMU"
    GNSS = "GNSS"
    BARO = "BARO"
    RADAR = "RADAR"
    EOIR = "EOIR"
    RF = "RF"
    LINK = "LINK"


class SystemState(str, Enum):
    STABLE = "STABLE"
    TENSE = "TENSE"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


# ============================================================
# SENSOR MEASUREMENT
# ============================================================

class SensorMeasurement(BaseModel):
    """
    Single sensor measurement with uncertainty and metadata.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tick: int = Field(ge=0)
    utc_timestamp: str
    sensor_id: str
    sensor_type: SensorType

    # Measurement vector (z) and covariance (R)
    z: np.ndarray
    R: np.ndarray

    quality: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    dropped: bool = False
    meta: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("z", "R")
    @classmethod
    def _validate_numpy_array(cls, v):
        if not isinstance(v, np.ndarray):
            raise ValueError("Must be a numpy.ndarray")
        return v

    @field_validator("R")
    @classmethod
    def _validate_covariance(cls, v):
        if v.ndim != 2 or v.shape[0] != v.shape[1]:
            raise ValueError("Covariance matrix must be square (2D)")
        return v


# ============================================================
# FUSED ESTIMATE
# ============================================================

class FusedEstimate(BaseModel):
    """
    Output of the fusion engine.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    altitude_m: float = Field(ge=-1000.0, le=50000.0)
    velocity_mps: float = Field(ge=0.0, le=2000.0)
    heading_deg: float = Field(ge=0.0, le=360.0)

    threat_index: float = Field(ge=0.0, le=100.0)
    civ_density: float = Field(ge=0.0, le=1.0)

    fusion_conf: float = Field(ge=0.0, le=1.0)
    surprise: float = Field(ge=0.0, le=1.0)

    sensor_contrib: Dict[str, float] = Field(default_factory=dict)
    used_meas_count: int = Field(ge=0)


# ============================================================
# TELEMETRY
# ============================================================

class Telemetry(BaseModel):
    """
    Complete per-tick telemetry record.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Timing
    tick: int = Field(ge=0)
    utc_timestamp: str
    mission_time_s: float = Field(ge=0.0)
    mission_stage_code: str
    mission_stage_label: str
    mission_stage_tick: int = Field(ge=0)
    flight_phase: str

    # Physical state
    mach: float = Field(ge=0.0, le=5.0)
    velocity_mps: float = Field(ge=0.0, le=2000.0)
    altitude_m: float = Field(ge=-1000.0, le=50000.0)
    q_kpa: float = Field(ge=0.0, le=1000.0)
    thermal_index: float = Field(ge=0.0, le=1.0)
    g_load: float = Field(ge=0.0, le=10.0)
    link_latency_ms: float = Field(ge=0.0, le=2000.0)
    imu_drift_deg_s: float = Field(ge=0.0, le=2.0)

    # Navigation (fused)
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)

    # Environment
    threat_index: float = Field(ge=0.0, le=100.0)
    civ_density: float = Field(ge=0.0, le=1.0)
    nav_drift: float = Field(ge=0.0, le=100.0)
    comms_loss: float = Field(ge=0.0, le=1.0)
    vision_hot_ratio: float = Field(ge=0.0, le=1.0)

    # Governance
    clarity: float = Field(ge=0.0, le=100.0)
    risk: float = Field(ge=0.0, le=100.0)
    predicted_risk: float = Field(ge=0.0, le=100.0)
    state: SystemState
    envelope_pressure: float = Field(ge=0.0, le=2.0)

    # Console contracts
    cc_combined: float = Field(ge=0.0, le=1.0)
    cc_nav_conf: float = Field(ge=0.0, le=1.0)
    cc_comms_conf: float = Field(ge=0.0, le=1.0)
    cc_vision_conf: float = Field(ge=0.0, le=1.0)
    cc_clarity_factor: float = Field(ge=0.0, le=1.0)
    cc_threat_factor: float = Field(ge=0.0, le=1.0)

    # Fusion health
    fusion_conf: float = Field(ge=0.0, le=1.0)
    fusion_surprise: float = Field(ge=0.0, le=1.0)
