"""
casper.config
==============

Central configuration definitions for Casper_Fusion.

This module contains only static configuration logic:
- Timing parameters
- Fusion gates
- Buffer sizes
- Alert thresholds

No runtime state. No Streamlit dependencies.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
import logging

logger = logging.getLogger("CASPER.config")


@dataclass
class FusionConfig:
    """
    Global configuration for fusion, governance, and buffering.

    Intended to be:
    - deterministic
    - serializable
    - safe to load from disk (YAML/JSON)
    """

    # --------------------------------------------------
    # Time / cadence
    # --------------------------------------------------
    dt_seconds: float = 1.0
    fusion_time_gate_ms: float = 350.0
    stale_ticks: int = 6

    # --------------------------------------------------
    # History limits (deque maxlen)
    # --------------------------------------------------
    max_telemetry_history: int = 600
    max_measurement_history: int = 3000
    max_audit_history: int = 1000

    # --------------------------------------------------
    # Fusion weighting (sensor priors)
    # --------------------------------------------------
    position_fusion_weight: Dict[str, float] = field(
        default_factory=lambda: {
            "GNSS": 1.0,
            "EOIR": 0.8,
            "RADAR": 0.9,
            "BARO": 0.3,
        }
    )

    # --------------------------------------------------
    # Governance thresholds
    # --------------------------------------------------
    clarity_warning_threshold: float = 75.0
    clarity_critical_threshold: float = 65.0
    fusion_conf_warning: float = 0.6
    fusion_conf_critical: float = 0.4

    # --------------------------------------------------
    # Serialization helpers
    # --------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return config as a plain dictionary."""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_")
        }

    @classmethod
    def from_yaml(cls, path: str) -> "FusionConfig":
        """
        Optional YAML loader.
        Falls back to defaults if PyYAML is unavailable or load fails.
        """
        try:
            import yaml  # type: ignore
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except ImportError:
            logger.warning("PyYAML not installed; using default FusionConfig.")
            return cls()
        except Exception as exc:
            logger.error(f"Failed to load config from {path}: {exc}")
            return cls()
