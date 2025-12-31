# Casper_Fusion

**Casper_Fusion** is a deterministic, audit-bound synthetic recon console designed to explore **multi-sensor fusion governance** under uncertainty.  
It emphasizes clarity, epistemic confidence, and human-inspectable decision support over autonomy or actuation.

This project is **recon-only**, **non-kinetic**, and **non-operational** by design.

---

## Core Intent

Casper_Fusion exists to answer a specific question:

> *How should a system reason, present confidence, and degrade authority when sensor truth is uncertain or contradictory?*

Rather than maximizing model capability, Casper_Fusion focuses on:
- deterministic control flow  
- explicit uncertainty modeling  
- sensor health transparency  
- auditability suitable for regulated or safety-critical domains  

It treats autonomy as a **governance problem**, not a model problem.

---

## What This Is (and Is Not)

### ✔️ This IS
- A **synthetic simulation environment**
- A **multi-sensor fusion testbed**
- A **governance-first architecture**
- A **human-in-the-loop decision console**
- A reference implementation for:
  - fusion confidence
  - epistemic surprise
  - authority degradation
  - audit trails

### ❌ This is NOT
- A weapon system
- A fire-control system
- An autonomous decision-maker
- A real ISR pipeline
- A live sensor integration

All sensors, environments, and targets are **synthetic**.

---

## High-Level Architecture

```

app.py (UI only)
↓
StepEngine (single-tick execution)
↓
┌───────────────┐
│ Sensor Sim    │  → noisy, degraded, dropped measurements
└───────────────┘
↓
┌───────────────┐
│ Fusion Engine │  → fused estimate + confidence + surprise
└───────────────┘
↓
┌───────────────┐
│ Governance    │  → clarity, risk, system state
└───────────────┘
↓
┌───────────────┐
│ Audit Chain   │  → deterministic, hashable records
└───────────────┘

```

Each layer is isolated, testable, and replaceable.

---

## Key Concepts

### Deterministic Execution
- Every tick is seeded
- No hidden global state
- Replayable behavior given seed + inputs

### Multi-Sensor Fusion
Synthetic sensors include:
- GNSS (with jamming/spoof risk)
- EO/IR (with comms and degrade effects)
- RADAR (intermittent)
- IMU (drift proxy)
- BARO (altitude)
- LINK (latency + comms loss)

Fusion currently uses a **weighted deterministic strategy**, with:
- inverse covariance weighting
- latency penalties
- quality factors
- sensor-type policy weights

A Kalman-based approach is intentionally stubbed, not implied.

---

### Epistemic Confidence & Surprise
Fusion does not just output a position.

It also outputs:
- **fusion_conf** — how internally consistent sensors are
- **surprise** — how contradictory measurements are

These values directly affect governance outcomes.

---

### Governance (Clarity & Risk)
The system computes:
- envelope pressure (physics)
- epistemic penalties (fusion confidence & surprise)
- threat weighting
- smoothed clarity via EMA

This produces:
- `clarity` (0–100)
- `risk` (0–100)
- `predicted_risk`
- system state:
  - STABLE
  - TENSE
  - HIGH_RISK
  - CRITICAL

Governance is explicit and inspectable.

---

### Audit Trail
Every tick produces an audit record:
- which measurements were used
- summarized covariances
- fused output
- deterministic SHA-256 hash

This enables:
- post-run inspection
- replay validation
- governance accountability

---

## Repository Structure

```

Casper_Fusion/
├── app.py                # Streamlit UI entry point
├── README.md
├── requirements.txt
└── casper/
├── config.py         # FusionConfig
├── models.py         # Core data contracts
├── state.py          # EngineState
├── step_engine.py    # Single-tick execution
├── presets.py        # AO / environments / envelopes
├── fusion/
│   ├── engine.py
│   └── strategies.py
├── sensors/
│   └── simulator.py
├── governance/
│   └── clarity_risk.py
├── audit/
│   └── chain.py
└── visualization/
└── terrain.py

```

UI code lives **outside** the package.  
Core logic is UI-agnostic and testable.

---

## Running the Demo

### Requirements
- Python 3.10+
- Streamlit

```

pip install -r requirements.txt

```

### Launch
```

streamlit run app.py

```

---

## Design Philosophy

Casper_Fusion follows a few non-negotiables:

- **Governance before autonomy**
- **Uncertainty must be visible**
- **Authority must degrade gracefully**
- **Every decision must be auditable**
- **No hidden magic**

This is infrastructure-grade thinking applied to autonomy-adjacent systems.

---

## Intended Audience

- Systems engineers
- Autonomy governance researchers
- Safety & certification professionals
- Defense-adjacent infrastructure teams
- Anyone skeptical of “just trust the model”

---

## Status

- Synthetic demo
- Architecture reference
- Actively evolving

Future directions may include:
- additional fusion strategies
- real sensor adapters (offline)
- scenario playback
- certification-oriented reporting

---

## Disclaimer

This project is:
- non-operational
- non-kinetic
- non-deployable

It is a **governance and reasoning prototype**, not a fielded system.

---

## License

MIT
