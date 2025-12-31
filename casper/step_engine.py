"""
casper.step_engine
==================

Single-step execution engine for Casper_Fusion.

Responsibilities:
- generate synthetic ground truth
- simulate sensors
- run fusion
- compute governance metrics
- emit telemetry
- append audit record
- update EngineState deterministically
"""

import math
import numpy as np

from casper.config import FusionConfig
from casper.state import EngineState
from casper.models import Telemetry
from casper.presets import ENVELOPES, ENVIRONMENTS
from casper.sensors.simulator import SensorSimulator
from casper.fusion.engine import FusionEngine
from casper.governance.clarity_risk import ClarityRiskCalculator
from casper.audit.chain import build_audit_record


class StepEngine:
    def __init__(self, config: FusionConfig):
        self.config = config
        self.sensor_sim = SensorSimulator(config)
        self.clarity_calc = ClarityRiskCalculator(config)

    # --------------------------------------------------
    # Truth generation
    # --------------------------------------------------
    def _generate_truth(self, state: EngineState, env, rng) -> dict:
        last = state.history[-1] if state.history else None
        envelope = ENVELOPES[state.envelope_name]

        mach = float(
            np.clip(
                (last.mach if last else 0.0) + rng.uniform(0.01, 0.05),
                0.0,
                envelope.max_mach,
            )
        )

        alt = float(
            np.clip(
                (last.altitude_m if last else 0.0) + rng.uniform(50.0, 150.0),
                0.0,
                18000.0,
            )
        )

        vel = mach * 295.0
        rho = 1.225 * math.exp(-alt / 8000.0)
        q = float(np.clip(0.5 * rho * vel**2 / 1000.0, 0.0, 900.0))

        thermal = float(
            np.clip(
                0.2 + 0.5 * (mach / envelope.max_mach) + env.thermal_bias + rng.normal(0, 0.02),
                0.0,
                1.0,
            )
        )

        lat = float(state.ao.base_lat + rng.uniform(-state.ao.lat_delta, state.ao.lat_delta))
        lon = float(state.ao.base_lon + rng.uniform(-state.ao.lon_delta, state.ao.lon_delta))

        threat = float(
            np.clip(
                (last.threat_index if last else 40.0) + rng.uniform(-5.0, 5.0),
                0.0,
                100.0,
            )
        )

        civ = float(
            np.clip(
                (last.civ_density if last else 0.3) + rng.uniform(-0.05, 0.05),
                0.0,
                1.0,
            )
        )

        return {
            "mach": mach,
            "velocity_mps": vel,
            "altitude_m": alt,
            "q_kpa": q,
            "thermal_index": thermal,
            "g_load": 1.0,
            "lat": lat,
            "lon": lon,
            "threat_index": threat,
            "civ_density": civ,
            "nav_drift": 5.0,
            "vision_hot_ratio": float(np.clip(0.10 + rng.normal(0, 0.03), 0.0, 1.0)),
        }

    # --------------------------------------------------
    # Main step
    # --------------------------------------------------
    def step(self, state: EngineState) -> EngineState:
        env = ENVIRONMENTS[state.env_name]
        rng = np.random.default_rng(state.rng_seed + state.tick + 1)

        # Truth
        truth = self._generate_truth(state, env, rng)

        # Sensors
        measurements = self.sensor_sim.simulate_all(state, truth, env, rng)
        for m in measurements:
            state.meas_history.append(m)
            state.last_seen_tick[m.sensor_id] = m.tick

        # Fusion
        fusion_engine = FusionEngine(self.config, state.fusion_strategy_name)
        fused = fusion_engine.fuse(state.meas_history, state.tick + 1)
        state.fused = fused

        used_meas = fusion_engine.select_measurements(state.meas_history, state.tick + 1)

        # Audit
        audit = build_audit_record(
            tick=state.tick + 1,
            utc=state.utc(),
            used_measurements=used_meas,
            fused=fused,
        )
        state.audit_chain.append(audit)

        # Governance
        clarity, risk, pred, sys_state, pressure = self.clarity_calc.compute(
            state,
            physical_state={
                "q_kpa": truth["q_kpa"],
                "thermal_index": truth["thermal_index"],
                "threat_index": truth["threat_index"],
            },
            fused=fused,
        )

        # Telemetry
        tel = Telemetry(
            tick=state.tick + 1,
            utc_timestamp=state.utc(),
            mission_time_s=state.mission_time_s + self.config.dt_seconds,
            mission_stage_code="STAGE",
            mission_stage_label="Recon",
            mission_stage_tick=state.mission_stage_tick,
            flight_phase="CRUISE",

            mach=truth["mach"],
            velocity_mps=truth["velocity_mps"],
            altitude_m=fused.altitude_m,
            q_kpa=truth["q_kpa"],
            thermal_index=truth["thermal_index"],
            g_load=truth["g_load"],
            link_latency_ms=float(next((m.z[0] for m in measurements if m.sensor_id == "LINK_1"), 0.0)),
            imu_drift_deg_s=float(next((m.meta.get("imu_drift_deg_s", 0.0) for m in measurements if m.sensor_id == "IMU_1"), 0.0)),

            lat=fused.lat,
            lon=fused.lon,
            threat_index=truth["threat_index"],
            civ_density=truth["civ_density"],
            nav_drift=truth["nav_drift"],
            comms_loss=float(next((m.meta.get("comms_loss", 0.0) for m in measurements if m.sensor_id == "LINK_1"), 0.0)),
            vision_hot_ratio=truth["vision_hot_ratio"],

            clarity=clarity,
            risk=risk,
            predicted_risk=pred,
            state=sys_state,
            envelope_pressure=pressure,

            cc_combined=clarity / 100.0,
            cc_nav_conf=fused.fusion_conf,
            cc_comms_conf=float(next((m.quality for m in measurements if m.sensor_id == "LINK_1"), 1.0)),
            cc_vision_conf=float(next((m.quality for m in measurements if m.sensor_id == "EOIR_1"), 0.0)),
            cc_clarity_factor=clarity / 100.0,
            cc_threat_factor=max(0.2, 1.0 - truth["threat_index"] / 150.0),

            fusion_conf=fused.fusion_conf,
            fusion_surprise=fused.surprise,
        )

        state.tick = tel.tick
        state.mission_time_s = tel.mission_time_s
        state.history.append(tel)

        return state
