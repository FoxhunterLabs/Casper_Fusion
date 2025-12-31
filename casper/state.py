"""
casper.state
============

Runtime state container for Casper_Fusion.

This module defines EngineState:
- simulation clock
- scenario selection
- history buffers
- fusion outputs
- audit chain

No business logic. No UI dependencies.
"""

import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Deque

import numpy as np
from collections import deque

from casper.config import FusionConfig
from casper.presets import AOConfig
from casper.audit.chain import AuditRecord
from casper.fusion.engine import FusedEstimate
from casper.models import Telemetry, SensorMeasurement


@dataclass
class EngineState:
    """
    Central runtime state for CASPER.

    Designed to be:
    - deterministic (seeded)
    - inspectable
    - resettable
    """

    # --------------------------------------------------
    # Configuration
    # --------------------------------------------------
    config: FusionConfig = field(default_factory=FusionConfig)

    # --------------------------------------------------
    # Simulation clock
    # --------------------------------------------------
    tick: int = 0
    mission_time_s: float = 0.0
    mission_stage_index: int = 0
    mission_stage_tick: int = 0

    # --------------------------------------------------
    # Identity / determinism
    # --------------------------------------------------
    run_id: int = 0
    rng_seed: int = 0

    # --------------------------------------------------
    # Scenario selection
    # --------------------------------------------------
    ao: Optional[AOConfig] = None
    env_name: str = "Clear Skies / Clean Link"
    envelope_name: str = "Nominal Demo Flight"
    threshold_name: str = "Balanced"

    # --------------------------------------------------
    # Governance memory
    # --------------------------------------------------
    clarity_ema: float = 0.9

    # --------------------------------------------------
    # History buffers (deque)
    # --------------------------------------------------
    history: Deque[Telemetry] = field(default_factory=deque)
    meas_history: Deque[SensorMeasurement] = field(default_factory=deque)
    audit_chain: Deque[AuditRecord] = field(default_factory=deque)

    # --------------------------------------------------
    # Fusion outputs
    # --------------------------------------------------
    fused: Optional[FusedEstimate] = None
    last_seen_tick: Dict[str, int] = field(default_factory=dict)

    # --------------------------------------------------
    # Visualization cache
    # --------------------------------------------------
    terrain: Optional[np.ndarray] = None

    # --------------------------------------------------
    # Fusion strategy selection
    # --------------------------------------------------
    fusion_strategy_name: str = "weighted"

    def __post_init__(self):
        """Initialize bounded deques after creation."""
        self.history = deque(self.history, maxlen=self.config.max_telemetry_history)
        self.meas_history = deque(self.meas_history, maxlen=self.config.max_measurement_history)
        self.audit_chain = deque(self.audit_chain, maxlen=self.config.max_audit_history)

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------
    def utc(self) -> str:
        """Current UTC timestamp (ISO8601)."""
        return datetime.utcnow().isoformat() + "Z"

    def reset(self, new_seed: Optional[int] = None):
        """
        Reset state for a new run.
        Keeps configuration, clears runtime buffers.
        """
        self.tick = 0
        self.mission_time_s = 0.0
        self.mission_stage_index = 0
        self.mission_stage_tick = 0
        self.clarity_ema = 0.9

        self.history.clear()
        self.meas_history.clear()
        self.audit_chain.clear()
        self.last_seen_tick.clear()

        self.fused = None
        self.terrain = None

        if new_seed is not None:
            self.rng_seed = int(new_seed)

        self.run_id = int(time.time() * 1000)
