"""
casper.fusion.engine
====================

Fusion engine orchestration:
- selects measurements within a fusion time gate
- filters dropped measurements
- calls the selected fusion strategy
- returns a fused estimate

No UI dependencies. No sensor simulation.
"""

from typing import Deque, List

from casper.config import FusionConfig
from casper.models import SensorMeasurement, FusedEstimate
from casper.fusion.strategies import WeightedFusion, KalmanFusion, FusionStrategy


class FusionEngine:
    """
    Strategy-driven fusion engine with deterministic measurement selection.
    """

    def __init__(self, config: FusionConfig, strategy_name: str = "weighted"):
        self.config = config
        self._strategies = {
            "weighted": WeightedFusion(config),
            "kalman": KalmanFusion(config),
        }
        self.strategy_name = strategy_name if strategy_name in self._strategies else "weighted"
        self.strategy: FusionStrategy = self._strategies[self.strategy_name]

    def set_strategy(self, strategy_name: str) -> None:
        """Switch fusion strategy safely."""
        if strategy_name not in self._strategies:
            strategy_name = "weighted"
        self.strategy_name = strategy_name
        self.strategy = self._strategies[strategy_name]

    def select_measurements(
        self,
        history: Deque[SensorMeasurement],
        current_tick: int
    ) -> List[SensorMeasurement]:
        """
        Select usable measurements within the fusion time gate.

        Gate logic:
        age_ms = |(tick_delta * dt_seconds * 1000) + latency_ms|
        """
        selected: List[SensorMeasurement] = []
        gate_ms = float(self.config.fusion_time_gate_ms)

        # Iterate most-recent-first for efficiency
        for m in reversed(history):
            if m.dropped:
                continue

            tick_delta = current_tick - m.tick
            age_ms = abs((tick_delta * self.config.dt_seconds * 1000.0) + m.latency_ms)

            if age_ms <= gate_ms:
                selected.append(m)
            else:
                # history is chronological; once we're outside gate, older will be worse
                break

        return selected

    def fuse(
        self,
        history: Deque[SensorMeasurement],
        current_tick: int
    ) -> FusedEstimate:
        """
        Run fusion for the current tick.
        """
        selected = self.select_measurements(history, current_tick)
        return self.strategy.fuse(selected)
