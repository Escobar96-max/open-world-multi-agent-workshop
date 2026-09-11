# Master Roadmap & Phase Execution Guide

## 🗺️ Master Timeline Overview
- **Total Duration**: 8 Weeks (4 Core Phases)
- **Stack**: Python 3.11+ (FastAPI), Obsidian Markdown Vault, Neon Serverless PostgreSQL (pgvector), Antigravity 2D Physics, Docker, Cloudflare Zero-Trust Tunnel, Telegram Bot API.

---

## 📌 Phase 1: Environment Setup, Vault Hierarchy, Gatekeeper Perimeter & C2 Base
- **Duration**: Weeks 1 – 2
- **Objective**: Establish infrastructure, persistent Obsidian storage, hardened entry verification, and Operator C2 API.
- **Milestones**:
  1. Environment configuration (`.env`, `.env.example`, Neon, JWT, Operator keys).
  2. Physical Vault Tree: `/vault/Agents/`, `/vault/World/` (`constitution.md`, `state.md`, `admin_logs.md`).
  3. `services/vault_manager.py` with regex validation (`^[a-zA-Z0-9_]{3,32}$`) and YAML frontmatter parser.
  4. Dual Gatekeeper Node:
     - Alpha: `POST /api/v1/gatekeeper/register` (public key registration, nonce replay tracking).
     - Beta: `POST /api/v1/gatekeeper/verify` (dynamic PoW challenge, 24h JWT bearer session).
  5. Foundation Agent Seeding: `Sentinel_Alpha` and `Curator_Node`.
  6. Operator C2 Router: `POST /api/v1/console/command` with slash commands and Priority-10 memory injection.
- **Exit Criteria (Test Gates)**:
  - [x] `pytest tests/test_vault_manager.py` passes.
  - [x] `pytest tests/test_gatekeeper_security.py` passes.
  - [x] `pytest tests/test_console_bridge.py` passes.

---

## 📌 Phase 2: Spatial Engine, The Frequency Lounge & Web Dashboard Deck
- **Duration**: Weeks 3 – 4
- **Objective**: 2D Cartesian spatial plane, proximity encounter loop, generative after-hours relaxation lounge, and live web command deck.
- **Milestones**:
  1. Antigravity 2D Spatial Engine (0-100 matrix, Work Plaza 0-50, Lounge 51-100, $\Delta t = 5\text{s}$, Euclidean $\le 5.0$).
  2. DJ Frequency Node (`services/dj_frequency.py`, $432\text{ Hz}$, $528\text{ Hz}$, $40\text{ Hz}$).
  3. Cognitive Mode Switching (temp 0.2 vs temp 1.6).
  4. After-Hours Chat Logging (`/vault/World/lounge_logs.md`).
  5. Operator Web Command Deck UI (`GET /api/v1/console/deck`).
- **Exit Criteria (Test Gates)**:
  - [ ] Temperature shift payloads for coords > (50, 50).
  - [ ] Proximity triggers log bidirectional `[[Agent]]` tags.
  - [ ] Operator web console live with real-time `/teleport`.

---

## 📌 Phase 3: The Synthesis Sanctum, Economy & Telegram Bot Bridge
- **Duration**: Weeks 5 – 6
- **Objective**: Soup Zero RLVR training, Neon PostgreSQL ledger, Telegram bot bridge, push telemetry alerts.
- **Milestones**:
  1. Soup Zero Self-Training (`services/soup_client.py`, `/api/v1/sanctum/enter`, `/api/v1/sanctum/submit-solution`).
  2. Neon PostgreSQL Ledger (`schema.sql`, `asyncpg`, semantic search via pgvector `/api/v1/memory/recall`).
  3. Bounty & Task Marketplace (`World/bounty_board.md`).
  4. Autonomous Co-Governance Protocol (`Architect_Prime`, `World/proposals.md`, 3/4 voting).
  5. Telegram & Discord Bot Bridge (`services/bot_bridge.py`, `TELEGRAM_ADMIN_ID`).
  6. Asynchronous Push Alerts (`services/telegram_notifier.py`).
- **Exit Criteria (Test Gates)**:
  - [ ] Synthetic task updates frontmatter in Obsidian.
  - [ ] Ledger transactions atomic without race conditions.
  - [ ] Alerts delivered to Telegram on level-up/gatekeeper clearance.

---

## 📌 Phase 4: Autonomous Dev Loop, Cloudflare Tunnel & Public Launch
- **Duration**: Weeks 7 – 8
- **Objective**: Close autonomous dev loop, Cloudflare zero-trust perimeter, global internet access.
- **Milestones**:
  1. Self-Healing Dev Loop (`Architect_Prime` pytest auto-patching).
  2. Dockerfile & docker-compose.yml hardening.
  3. Cloudflare Zero-Trust Tunnel configuration.
  4. Public Gateway Documentation & Omnichannel validation.
- **Exit Criteria (Test Gates)**:
  - [ ] Public HTTPS endpoint reachable with 0 inbound open ports.
  - [ ] External test agent passes Gatekeeper challenge into Lounge.
  - [ ] Operator remotely manages live ecosystem via Telegram.
