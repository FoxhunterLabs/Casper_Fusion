"""
casper.presets
==============

Static presets for Casper_Fusion.

This module defines:
- Areas of Operation (AO)
- Environmental degradation profiles
- Flight envelopes
- Governance thresholds
- Mission stages

All values are immutable and safe to import anywhere.
"""

from typing import Dict, List
from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# CORE PRESET MODELS
# ============================================================

class AOConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    base_lat: float = Field(ge=-90.0, le=90.0)
    base_lon: float = Field(ge=-180.0, le=180.0)
    lat_delta: float = Field(ge=0.0, le=10.0)
    lon_delta: float = Field(ge=0.0, le=10.0)


class EnvProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    latency_base: float = Field(ge=0.0)
    latency_jitter: float = Field(ge=0.0)
    thermal_bias: float = Field(ge=0.0, le=1.0)
    imu_drift_bias: float = Field(ge=0.0, le=0.5)
    gnss_jam_factor: float = Field(ge=0.0, le=1.0)
    eoir_degrade: float = Field(ge=0.0, le=1.0)


class EnvelopePreset(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    max_mach: float = Field(ge=0.0, le=5.0)
    max_q_kpa: float = Field(ge=0.0, le=1000.0)
    max_g: float = Field(ge=0.0, le=10.0)
    max_thermal_index: float = Field(ge=0.0, le=1.0)
    max_latency_ms: float = Field(ge=0.0, le=2000.0)
    description: str


class ThresholdPreset(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    clarity_threshold: float = Field(ge=0.0, le=100.0)
    threat_threshold: float = Field(ge=0.0, le=100.0)
    description: str


class MissionStage(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    label: str
    duration: int = Field(ge=0)
    description: str


# ============================================================
# PRESET DEFINITIONS
# ============================================================

AO_PRESETS: Dict[str, AOConfig] = {
    "Kharkiv (synthetic)": AOConfig(
        label="Kharkiv Region",
        base_lat=49.9935,
        base_lon=36.2304,
        lat_delta=0.08,
        lon_delta=0.12,
    ),
    "Black Sea (synthetic)": AOConfig(
        label="Black Sea",
        base_lat=44.5,
        base_lon=34.0,
        lat_delta=0.2,
        lon_delta=0.3,
    ),
    "Test Range (synthetic)": AOConfig(
        label="Test Range",
        base_lat=35.0,
        base_lon=-117.0,
        lat_delta=0.1,
        lon_delta=0.1,
    ),
}


ENVIRONMENTS: Dict[str, EnvProfile] = {
    "Clear Skies / Clean Link": EnvProfile(
        name="Clear",
        latency_base=120,
        latency_jitter=40,
        thermal_bias=0.0,
        imu_drift_bias=0.0,
        gnss_jam_factor=0.0,
        eoir_degrade=0.0,
    ),
    "High Latency Link": EnvProfile(
        name="High Lat",
        latency_base=260,
        latency_jitter=80,
        thermal_bias=0.05,
        imu_drift_bias=0.02,
        gnss_jam_factor=0.05,
        eoir_degrade=0.10,
    ),
    "GNSS Degraded / Spoof Risk": EnvProfile(
        name="GNSS Degraded",
        latency_base=180,
        latency_jitter=70,
        thermal_bias=0.03,
        imu_drift_bias=0.03,
        gnss_jam_factor=0.55,
        eoir_degrade=0.15,
    ),
    "EO/IR Degraded": EnvProfile(
        name="EOIR Degraded",
        latency_base=140,
        latency_jitter=60,
        thermal_bias=0.02,
        imu_drift_bias=0.02,
        gnss_jam_factor=0.05,
        eoir_degrade=0.55,
    ),
}


ENVELOPES: Dict[str, EnvelopePreset] = {
    "Nominal Demo Flight": EnvelopePreset(
        name="Nominal Demo Flight",
        max_mach=1.8,
        max_q_kpa=650,
        max_g=4.5,
        max_thermal_index=0.78,
        max_latency_ms=300,
        description="Balanced flight envelope",
    ),
    "Conservative Test Profile": EnvelopePreset(
        name="Conservative Test Profile",
        max_mach=1.2,
        max_q_kpa=450,
        max_g=3.5,
        max_thermal_index=0.65,
        max_latency_ms=250,
        description="Tight, conservative envelope",
    ),
    "Aggressive Envelope Probe": EnvelopePreset(
        name="Aggressive Envelope Probe",
        max_mach=2.3,
        max_q_kpa=800,
        max_g=5.5,
        max_thermal_index=0.90,
        max_latency_ms=350,
        description="Aggressive test envelope",
    ),
}


THRESHOLDS: Dict[str, ThresholdPreset] = {
    "Balanced": ThresholdPreset(
        name="Balanced",
        clarity_threshold=75,
        threat_threshold=65,
        description="Standard operational thresholds",
    ),
    "Conservative": ThresholdPreset(
        name="Conservative",
        clarity_threshold=85,
        threat_threshold=55,
        description="Higher safety margins",
    ),
    "Aggressive": ThresholdPreset(
        name="Aggressive",
        clarity_threshold=65,
        threat_threshold=75,
        description="Accept higher risk for mission",
    ),
}


MISSION_STAGES: List[MissionStage] = [
    MissionStage(
        code="STAGE_1_BOOST",
        label="Boost",
        duration=40,
        description="Initial acceleration phase",
    ),
    MissionStage(
        code="STAGE_2_GRID",
        label="Grid",
        duration=70,
        description="Grid search pattern",
    ),
    MissionStage(
        code="STAGE_3_RELAY",
        label="Relay",
        duration=70,
        description="Data relay and communication",
    ),
    MissionStage(
        code="STAGE_4_COLLAPSE",
        label="Collapse",
        duration=50,
        description="Orbit collapse and descent",
    ),
    MissionStage(
        code="STAGE_5_RTB",
        label="RTB",
        duration=9999,
        description="Return to base",
    ),
]
