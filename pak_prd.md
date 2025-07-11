# Pixell Agent Kit (PAK) – Product Requirements Document

**Version 0.1 – July 2025**  
Authors: Pixell Core Team

---

## 1. Purpose & Scope
PAK is a lightweight developer **Kit** that turns any AI agent (written with OpenAI Agent SDK, AWS Strands, LangGraph, etc.) into a portable, versioned **Agent Package (APKG)**. PAK’s responsibilities end at packaging, validation, and local dev‑loop; execution is delegated to **PAF‑Runtime**, and user experience to the **PAF** web UI.

> **Goal:** Standardize how agents (and their sub‑agents) are shared, versioned, and hot‑loaded across the Pixell ecosystem – without prescribing a specific reasoning engine.

### In Scope
- Command‑line tooling & minimal library for **building, validating, signing, and inspecting APKG files**.
- Reference manifest schema (`agent.yaml`) and JSON Schema.
- Local dev runner that spins up agents via `uvicorn` for smoke‑testing.
- Docs & sample templates for Python (v1) and TypeScript (v1.1).

### Out of Scope (v1)
- Long‑running orchestration logic (handled by agent engines).  
- Central registry UI (bootstrap with S3 + JSON index via PAF‑Runtime).  
- Complex dependency resolution (defer to v2).

---

## 2. Glossary
| Acronym | Meaning |
|---------|---------|
| **PAF** | *Pixell Agent Framework* – React + Tailwind web console / UI layer |
| **PAF‑Core** | Headless orchestration logic that PAF UI calls via REST/WS |
| **PAF‑Runtime** | FastAPI host that **mounts APKGs** and exposes `/agents/*` endpoints |
| **PAK** | *Pixell Agent Kit* – CLI + library that creates APKGs |
| **APKG** | *Agent Package* – zip/OCI artifact produced by PAK |

---

## 3. Architectural Relationship
```mermaid
flowchart TD
  subgraph DevLaptop
    A[Agent source (any SDK)] -->|`pak build`| B(APKG file)
  end
  B -->|upload| S3Registry[(APKG Registry – S3)]
  S3Registry -->|lazy pull| R[paf-runtime]
  R -->|REST /agents/{id}| PAF-UI[PAF Web UI]
  R -->|Webhooks| PAF-Core
  PAF-UI -->|UX & metrics| User[(Brand/Dev)]
```
**Narrative**
1. Developer authors agent logic with their favourite engine.  
2. `pak build` produces `my_agent-0.3.1.apkg` (zip + manifest).  
3. CI uploads APKG to S3 (acts as dumb registry).  
4. `paf-runtime` periodically (or via webhook) pulls new packages and mounts exported sub‑agents.  
5. PAF UI lets end‑users invoke agents; PAF‑Core orchestrates multi‑agent workflows.

---

## 4. Detailed Requirements for **PAK**

### 4.1 CLI Commands
| Command | Description | Priority |
|---------|-------------|----------|
| `pak init <name>` | Scaffold new agent with sample `agent.yaml`, entrypoint, test | Must‑have |
| `pak build` | Validate schema → create `.apkg` (zip) with SHA‑256 hash | Must‑have |
| `pak run-dev` | Start local FastAPI dev server w/ hot‑reload | Must‑have |
| `pak inspect <file.apkg>` | Print manifest, exports, deps | Should |
| `pak sign --key …` / `pak verify` | Optional GPG signing | Nice‑to‑have |

### 4.2 Manifest (`agent.yaml`)
```yaml
id: pixell.revenue_autopilot
version: 0.1.3
entrypoint: main:app            # ASGI router
exports:
  - id: classify
    path: subagents.classify:agent
    schema: schemas/classify.json
private:
  - id: ingest_amz
    path: subagents.ingest_amz:agent
metadata:
  authors: ["@alice", "@bob"]
  license: Apache‑2.0
  runtime: python3.11
```
**Rules**
- **Semantic versioning**; runtime rejects downgrades by default.  
- Multiple export IDs must be unique across all mounted APKGs.

### 4.3 Packaging Format
- Zip file with deterministic ordering; extension `.apkg`.  
- Embed `agent.yaml` at root; rest under `/src` or `/dist` directory.  
- Size limit configurable (default 50 MB).

### 4.4 Loader API (used by PAF‑Runtime)
```python
from pak.loader import load_apkg
router = load_apkg("my_agent-0.1.3.apkg")
app.include_router(router, prefix="/agents/classify")
```
Must return:
- FastAPI `APIRouter` for each export.  
- Python callable for in‑process calls (`router.call("classify", **kwargs)`).

### 4.5 Local Dev Runner
- Uses `watchdog` for file‑change reload.  
- Environment injection (`.env`) to mimic production secrets.  
- Lint warning if package exceeds size limit.

### 4.6 Registry Compatibility
- Default backend: S3 signed URLs + JSON index.  
- Pluggable interface for future Artifactory / GCS.  
- Support `pak push` (v1.1).

### 4.7 Security & Integrity
| Concern | Mitigation |
|---------|-----------|
| Tampered package | Optional GPG signature + SHA in index |
| Dependency CVEs | `pak build` runs `pip-audit` (Python) |
| Secrets leakage | `.apkgignore` for `.env`, `*.pem` |

---

## 5. Non‑Functional Requirements
| Area | Metric |
|------|--------|
| **Performance** | `pak build` < 2 s for 100‑file repo |
| **DX** | `pak init → run-dev` completes < 60 s cold start |
| **Portability** | APKG can run on any POSIX OS with Python 3.10+ |
| **Reliability** | Loader handles version conflicts gracefully |

---

## 6. Milestones & Timeline
| Date | Milestone |
|------|-----------|
| **Aug 09 ’25** | PAK v0.1 CLI & schema, local dev runner |
| **Aug 30 ’25** | PAF‑Runtime mounts APKGs in staging |
| **Sep 20 ’25** | Signed package support + sample registry |
| **Oct 15 ’25** | TypeScript template, `pak push`, public beta |

---

## 7. Success Metrics
- **<5 min** from `pak init` to running agent in PAF UI.  
- **<2 hrs** to port an existing Strands demo into an APKG.  
- **>10 external APKGs** published within 60 days of beta launch.

---

## 8. Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Competing spec gains traction (OpenAI, Hugging Face) | Med | High | Publish spec early, encourage adapters |
| Format churn breaks PAF‑Runtime | Low | Med | Versioned loader, e2e tests |
| Security supply‑chain attack | Low | High | Mandatory hash, optional signature, SBOM audit |

---

## 9. Open Questions
1. Should we embed **OCI image** support in v1 or defer?  
2. How do we handle **language runtimes** beyond Python (Node, Rust) – wrapper or multi‑lang spec?  
3. Do we need **fine‑grained dependency pinning** (lockfile) now, or rely on containerised builds?

---

_© 2025 Pixell Global Inc._

