"""
casper.sensors.simulator
=======================

Synthetic sensor simulator for Casper_Fusion.

Generates SensorMeasurement records per tick:
- LINK (latency + comms loss)
- IMU (drift proxy)
- BARO (altitude)
- GNSS (position w/ jam & spoof risk)
- EOIR (position-ish proxy w/ degrade)
- RADAR (position-ish proxy intermittent)

This is recon-only synthetic telemetry.
"""

from typing import Dict, List

import numpy as np

from casper.config import FusionConfig
from casper.models import SensorMeasurement, SensorType
from casper.presets import EnvProfile
from casper.state import EngineState


class SensorSimulator:
    def __init__(self, config: FusionConfig):
        self.config = config

    # --------------------------------------------------
    # Individual sensors
    # --------------------------------------------------
    def simulate_link(
        self,
        state: EngineState,
        env: EnvProfile,
        rng: np.random.Generator,
    ) -> SensorMeasurement:
        link_latency = float(
            np.clip(env.latency_base + rng.normal(0, env.latency_jitter), 40, 800)
        )
        comms_loss = 1.0 if rng.random() < (0.02 + 0.08 * (link_latency / 600.0)) else 0.0

        return SensorMeasurement(
            tick=state.tick + 1,
            utc_timestamp=state.utc(),
            sensor_id="LINK_1",
            sensor_type=SensorType.LINK,
            z=np.array([link_latency, comms_loss, 0.0], dtype=float),
            R=np.diag([25.0, 0.05, 1.0]),
            quality=float(np.clip(1.0 - link_latency / 900.0, 0.1, 1.0)),
            latency_ms=link_latency,
            dropped=False,
            meta={"comms_loss": float(comms_loss)},
        )

    def simulate_imu(
        self,
        state: EngineState,
        env: EnvProfile,
        rng: np.random.Generator,
    ) -> SensorMeasurement:
        imu_drift = float(
            np.clip(
                0.02 + env.imu_drift_bias + abs(rng.normal(0, 0.01)),
                0.005,
                0.12,
            )
        )
        return SensorMeasurement(
            tick=state.tick + 1,
            utc_timestamp=state.utc(),
            sensor_id="IMU_1",
            sensor_type=SensorType.IMU,
            z=np.array([imu_drift, 0.0, 0.0], dtype=float),
            R=np.diag([0.0004, 1.0, 1.0]),
            quality=float(np.clip(1.0 - imu_drift / 0.15, 0.2, 1.0)),
            latency_ms=float(np.clip(20 + rng.normal(0, 8), 5, 60)),
            dropped=False,
            meta={"imu_drift_deg_s": float(imu_drift)},
        )

    def simulate_baro(
        self,
        state: EngineState,
        truth: Dict[str, float],
        rng: np.random.Generator,
    ) -> SensorMeasurement:
        baro_noise = float(rng.normal(0, 7.0))
        alt_baro = float(truth["altitude_m"] + baro_noise)
        return SensorMeasurement(
            tick=state.tick + 1,
            utc_timestamp=state.utc(),
            sensor_id="BARO_1",
            sensor_type=SensorType.BARO,
            z=np.array([alt_baro, 0.0, 0.0], dtype=float),
            R=np.diag([49.0, 1.0, 1.0]),
            quality=0.85,
            latency_ms=float(np.clip(30 + rng.normal(0, 10), 5, 80)),
            dropped=False,
            meta={"altitude_m_baro": alt_baro},
        )

    def simulate_gnss(
        self,
        state: EngineState,
        truth: Dict[str, float],
        env: EnvProfile,
        rng: np.random.Generator,
    ) -> SensorMeasurement:
        gnss_drop = rng.random() < (0.02 + env.gnss_jam_factor * 0.25)

        base_std = np.array([0.00025, 0.00025, 3.5], dtype=float)
        jam_std = np.array([0.0012, 0.0012, 15.0], dtype=float) * float(env.gnss_jam_factor)
        std = base_std + jam_std

        z_true = np.array([truth["lat"], truth["lon"], truth["altitude_m"]], dtype=float)

        if gnss_drop:
            return SensorMeasurement(
                tick=state.tick + 1,
                utc_timestamp=state.utc(),
                sensor_id="GNSS_A",
                sensor_type=SensorType.GNSS,
                z=z_true,
                R=np.diag(std**2),
                quality=0.0,
                latency_ms=float(np.clip(120 + rng.normal(0, 35), 60, 300)),
                dropped=True,
                meta={"dropped_reason": "synthetic_jam_drop", "jam_factor": float(env.gnss_jam_factor)},
            )

        noise = rng.normal(0, std)

        spoof_bias = np.array([0.0, 0.0, 0.0], dtype=float)
        if rng.random() < float(env.gnss_jam_factor) * 0.15:
            spoof_bias = rng.normal(0, np.array([0.002, 0.002, 10.0], dtype=float))

        z = z_true + noise + spoof_bias
        R = np.diag(std**2)

        quality = float(np.clip(0.95 - float(env.gnss_jam_factor) * 0.6, 0.15, 0.95))

        return SensorMeasurement(
            tick=state.tick + 1,
            utc_timestamp=state.utc(),
            sensor_id="GNSS_A",
            sensor_type=SensorType.GNSS,
            z=z.astype(float),
            R=R.astype(float),
            quality=quality,
            latency_ms=float(np.clip(90 + rng.normal(0, 25), 40, 220)),
            dropped=False,
            meta={"jam_factor": float(env.gnss_jam_factor)},
        )

    def simulate_eoir(
        self,
        state: EngineState,
        truth: Dict[str, float],
        env: EnvProfile,
        rng: np.random.Generator,
        comms_loss: float,
    ) -> SensorMeasurement:
        eoir_drop = rng.random() < (0.03 + float(env.eoir_degrade) * 0.22 + comms_loss * 0.15)

        base_std = np.array([0.0006, 0.0006, 8.0], dtype=float)
        degrade_std = np.array([0.0013, 0.0013, 20.0], dtype=float) * float(env.eoir_degrade)
        std = base_std + degrade_std

        z_true = np.array([truth["lat"], truth["lon"], truth["altitude_m"]], dtype=float)

        if eoir_drop:
            return SensorMeasurement(
                tick=state.tick + 1,
                utc_timestamp=state.utc(),
                sensor_id="EOIR_1",
                sensor_type=SensorType.EOIR,
                z=z_true,
                R=np.diag(std**2),
                quality=0.0,
                latency_ms=float(np.clip(180 + rng.normal(0, 55), 80, 400)),
                dropped=True,
                meta={"dropped_reason": "synthetic_eoir_drop"},
            )

        noise = rng.normal(0, std)
        z = z_true + noise
        R = np.diag(std**2)

        hot_ratio = float(np.clip(truth.get("vision_hot_ratio", 0.10) + rng.normal(0, 0.03), 0.0, 1.0))
        quality = float(np.clip(0.82 - float(env.eoir_degrade) * 0.55 - comms_loss * 0.2, 0.1, 0.85))

        return SensorMeasurement(
            tick=state.tick + 1,
            utc_timestamp=state.utc(),
            sensor_id="EOIR_1",
            sensor_type=SensorType.EOIR,
            z=z.astype(float),
            R=R.astype(float),
            quality=quality,
            latency_ms=float(np.clip(140 + rng.normal(0, 45), 60, 320)),
            dropped=False,
            meta={"hot_ratio": hot_ratio},
        )

    def simulate_radar(
        self,
        state: EngineState,
        truth: Dict[str, float],
        rng: np.random.Generator,
    ) -> SensorMeasurement:
        radar_std = np.array([0.00045, 0.00045, 6.5], dtype=float)
        noise = rng.normal(0, radar_std)
        z_true = np.array([truth["lat"], truth["lon"], truth["altitude_m"]], dtype=float)
        z = z_true + noise
        R = np.diag(radar_std**2)

        return SensorMeasurement(
            tick=state.tick + 1,
            utc_timestamp=state.utc(),
            sensor_id="RADAR_1",
            sensor_type=SensorType.RADAR,
            z=z.astype(float),
            R=R.astype(float),
            quality=0.75,
            latency_ms=float(np.clip(110 + rng.normal(0, 35), 50, 280)),
            dropped=False,
            meta={},
        )

    # --------------------------------------------------
    # Main entry: simulate all sensors for one tick
    # --------------------------------------------------
    def simulate_all(
        self,
        state: EngineState,
        truth: Dict[str, float],
        env: EnvProfile,
        rng: np.random.Generator,
    ) -> List[SensorMeasurement]:
        measurements: List[SensorMeasurement] = []

        link = self.simulate_link(state, env, rng)
        measurements.append(link)
        comms_loss = float(link.meta.get("comms_loss", 0.0))

        measurements.append(self.simulate_imu(state, env, rng))
        measurements.append(self.simulate_baro(state, truth, rng))
        measurements.append(self.simulate_gnss(state, truth, env, rng))
        measurements.append(self.simulate_eoir(state, truth, env, rng, comms_loss))

        # RADAR intermittently available
        if rng.random() < 0.55:
            measurements.append(self.simulate_radar(state, truth, rng))

        return measurements
