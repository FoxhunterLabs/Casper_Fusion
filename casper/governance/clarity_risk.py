"""
casper.governance.clarity_risk
==============================

Clarity + risk computation for Casper_Fusion.

Inputs:
- physical envelope signals (q_kpa, thermal_index)
- threat index
- fusion health signals (fusion_conf, surprise)

Outputs:
- clarity (0..100)
- risk (0..100)
- predicted risk (0..100)
- SystemState label
- envelope pressure (0..~2.0)

This module is deterministic and side-effect free,
except for EMA state stored inside the calculator object.
"""

from typing import Dict, Tuple

import numpy as np

from casper.config import FusionConfig
from casper.models import SystemState, FusedEstimate
from casper.presets import ENVELOPES
from casper.state import EngineState


class ClarityRiskCalculator:
    def __init__(self, config: FusionConfig):
        self.config = config
        self.clarity_ema = 0.9

    def reset(self):
        self.clarity_ema = 0.9

    def compute(
        self,
        state: EngineState,
        physical_state: Dict[str, float],
        fused: FusedEstimate,
    ) -> Tuple[float, float, float, SystemState, float]:
        """
        Compute clarity/risk with fusion epistemics.

        physical_state must include:
        - q_kpa
        - thermal_index
        - threat_index
        """
        envp = ENVELOPES[state.envelope_name]

        q_u = float(np.clip(physical_state["q_kpa"] / envp.max_q_kpa, 0, 1.6))
        t_u = float(np.clip(physical_state["thermal_index"] / envp.max_thermal_index, 0, 1.8))
        threat_u = float(np.clip(physical_state["threat_index"] / 100.0, 0, 1.0))

        pressure = 0.6 * q_u + 0.4 * t_u

        fusion_conf = float(getattr(fused, "fusion_conf", 0.5))
        surprise = float(getattr(fused, "surprise", 0.5))

        # Base clarity (pressure + threat)
        raw = float(np.clip(1.0 - pressure - 0.3 * threat_u, 0.55, 1.0))

        # Epistemic penalties: low confidence + high surprise
        raw *= float(np.clip(0.70 + 0.30 * fusion_conf, 0.0, 1.0))
        raw *= float(np.clip(1.0 - 0.30 * surprise, 0.0, 1.0))

        # EMA smoothing
        self.clarity_ema = 0.15 * raw + 0.85 * self.clarity_ema
        clarity = float(self.clarity_ema * 100.0)

        # Risk
        risk = float(
            np.clip(
                pressure * 60.0
                + (100.0 - clarity) * 0.45
                + (1.0 - fusion_conf) * 18.0
                + surprise * 14.0,
                0.0,
                100.0,
            )
        )

        pred = float(np.clip(risk + 8.0 * (pressure - 0.8), 0.0, 100.0))

        if clarity >= 90 and risk < 30:
            sys_state = SystemState.STABLE
        elif clarity >= 80:
            sys_state = SystemState.TENSE
        elif clarity >= 65:
            sys_state = SystemState.HIGH_RISK
        else:
            sys_state = SystemState.CRITICAL

        return clarity, risk, pred, sys_state, float(pressure)
