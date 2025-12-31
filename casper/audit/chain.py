"""
casper.audit.chain
==================

Audit trail utilities for Casper_Fusion.

Provides:
- AuditRecord model
- build_audit_record() helper that emits a deterministic SHA256 hash
"""

import json
import hashlib
from typing import Any, Dict, List

import numpy as np
from pydantic import BaseModel, Field, ConfigDict

from casper.models import SensorMeasurement, FusedEstimate


class AuditRecord(BaseModel):
    """
    One audit entry capturing which measurements were used and the fused output.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tick: int = Field(ge=0)
    utc: str
    used_measurements: List[Dict[str, Any]]
    fused_output: Dict[str, Any]
    sha256: str


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def build_audit_record(
    tick: int,
    utc: str,
    used_measurements: List[SensorMeasurement],
    fused: FusedEstimate,
) -> AuditRecord:
    """
    Build a deterministic audit record + SHA256.

    Notes:
    - We intentionally store compact measurement summaries (not full matrices)
      to keep exports readable.
    - Hash is computed from a stable JSON serialization (sorted keys).
    """
    used_payload: List[Dict[str, Any]] = []
    for m in used_measurements:
        # Measurement summary (3D pos sensors use z[:3]; others still include z[:3] if present)
        z3 = m.z[:3] if hasattr(m.z, "__len__") else []
        z3_list = [ _safe_float(v) for v in (z3.tolist() if isinstance(z3, np.ndarray) else list(z3)) ]

        used_payload.append(
            {
                "sensor_id": m.sensor_id,
                "type": m.sensor_type.value,
                "quality": _safe_float(m.quality),
                "latency_ms": _safe_float(m.latency_ms),
                "tick": int(m.tick),
                "z3": z3_list,
                "R_trace": _safe_float(np.trace(m.R)),
                "dropped": bool(m.dropped),
                "meta": dict(m.meta or {}),
            }
        )

    fused_payload: Dict[str, Any] = {
        "lat": _safe_float(fused.lat),
        "lon": _safe_float(fused.lon),
        "altitude_m": _safe_float(fused.altitude_m),
        "velocity_mps": _safe_float(fused.velocity_mps),
        "heading_deg": _safe_float(fused.heading_deg),
        "fusion_conf": _safe_float(fused.fusion_conf),
        "surprise": _safe_float(fused.surprise),
        "sensor_contrib": {k: _safe_float(v) for k, v in (fused.sensor_contrib or {}).items()},
        "used_meas_count": int(fused.used_meas_count),
    }

    payload = {
        "tick": int(tick),
        "utc": str(utc),
        "used": used_payload,
        "fused": fused_payload,
    }

    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()

    return AuditRecord(
        tick=int(tick),
        utc=str(utc),
        used_measurements=used_payload,
        fused_output=fused_payload,
        sha256=sha,
    )
