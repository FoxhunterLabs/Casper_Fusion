"""
casper.fusion.strategies
=======================

Fusion strategies for Casper_Fusion.

Each strategy:
- accepts validated SensorMeasurement objects
- returns a FusedEstimate
- exposes epistemic confidence + surprise

No state mutation. No UI dependencies.
"""

from typing import List, Tuple

import numpy as np

from casper.config import FusionConfig
from casper.models import SensorMeasurement, FusedEstimate, SensorType


# ============================================================
# BASE STRATEGY
# ============================================================

class FusionStrategy:
    """
    Abstract fusion strategy interface.
    """

    def fuse(self, measurements: List[SensorMeasurement]) -> FusedEstimate:
        raise NotImplementedError

    def calculate_confidence(
        self,
        measurements: List[SensorMeasurement],
        weights: np.ndarray,
        fused: np.ndarray
    ) -> Tuple[float, float]:
        raise NotImplementedError


# ============================================================
# WEIGHTED FUSION (DEFAULT)
# ============================================================

class WeightedFusion(FusionStrategy):
    """
    Deterministic weighted-average fusion.

    Weighting factors:
    - inverse covariance trace
    - latency penalty
    - measurement quality
    - sensor-type policy weight
    """

    def __init__(self, config: FusionConfig):
        self.config = config

    # --------------------------------------------------
    # Weight computation
    # --------------------------------------------------
    def _weight(self, m: SensorMeasurement) -> float:
        cov_trace = float(np.trace(m.R))
        cov_term = 1.0 / max(cov_trace, 1e-9)

        latency_term = 1.0 / (1.0 + (m.latency_ms / 200.0))
        quality_term = float(np.clip(m.quality, 0.0, 1.0))

        type_weight = self.config.position_fusion_weight.get(
            m.sensor_type.value,
            0.5
        )

        return max(0.0, cov_term * latency_term * quality_term * type_weight)

    # --------------------------------------------------
    # Fusion
    # --------------------------------------------------
    def fuse(self, measurements: List[SensorMeasurement]) -> FusedEstimate:
        # Only position-capable sensors
        pos_meas = [
            m for m in measurements
            if m.sensor_type in (
                SensorType.GNSS,
                SensorType.EOIR,
                SensorType.RADAR,
            )
            and not m.dropped
        ]

        if not pos_meas:
            return self._fallback()

        weights = np.array([self._weight(m) for m in pos_meas], dtype=float)

        if weights.sum() <= 1e-12:
            weights = np.ones(len(weights)) / len(weights)
        else:
            weights /= weights.sum()

        Z = np.stack([m.z[:3] for m in pos_meas], axis=0)
        fused = (Z * weights[:, None]).sum(axis=0)

        fusion_conf, surprise = self.calculate_confidence(
            pos_meas, weights, fused
        )

        contrib = {
            m.sensor_id: float(w)
            for m, w in zip(pos_meas, weights)
        }

        return FusedEstimate(
            lat=float(fused[0]),
            lon=float(fused[1]),
            altitude_m=float(fused[2]),
            velocity_mps=0.0,
            heading_deg=0.0,
            threat_index=0.0,
            civ_density=0.0,
            fusion_conf=fusion_conf,
            surprise=surprise,
            sensor_contrib=contrib,
            used_meas_count=len(pos_meas),
        )

    # --------------------------------------------------
    # Confidence metrics
    # --------------------------------------------------
    def calculate_confidence(
        self,
        measurements: List[SensorMeasurement],
        weights: np.ndarray,
        fused: np.ndarray
    ) -> Tuple[float, float]:
        if len(measurements) < 2:
            return 0.5, 0.5

        Z = np.stack([m.z[:3] for m in measurements], axis=0)
        diffs = Z - fused[None, :]

        scale = np.array([1e-3, 1e-3, 10.0], dtype=float)
        diffs_scaled = diffs / scale[None, :]

        dispersion = float(
            np.sqrt((weights[:, None] * diffs_scaled ** 2).sum())
        )

        surprise = float(np.clip(dispersion / 2.0, 0.0, 1.0))
        fusion_conf = float(np.clip(1.0 - surprise, 0.0, 1.0))

        return fusion_conf, surprise

    # --------------------------------------------------
    # Fallback
    # --------------------------------------------------
    def _fallback(self) -> FusedEstimate:
        return FusedEstimate(
            lat=0.0,
            lon=0.0,
            altitude_m=0.0,
            velocity_mps=0.0,
            heading_deg=0.0,
            threat_index=0.0,
            civ_density=0.0,
            fusion_conf=0.1,
            surprise=1.0,
            sensor_contrib={},
            used_meas_count=0,
        )


# ============================================================
# KALMAN FUSION (STUB — SAFE)
# ============================================================

class KalmanFusion(FusionStrategy):
    """
    Placeholder for future Kalman-based fusion.

    Explicitly not implemented to avoid
    accidental use without validation.
    """

    def __init__(self, config: FusionConfig):
        self.config = config

    def fuse(self, measurements: List[SensorMeasurement]) -> FusedEstimate:
        raise NotImplementedError(
            "KalmanFusion is a stub and must be explicitly implemented."
        )

    def calculate_confidence(self, *args, **kwargs):
        raise NotImplementedError
