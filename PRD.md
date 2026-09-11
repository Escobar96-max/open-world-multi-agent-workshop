# PRD: Self-Bootstrapping Autonomous AI Open-World Ecosystem
**Antigravity Grid, Dual Gatekeeper, Synthesis Sanctum, Co-Governance & Operator C2 Bridge**

---

## 1. Executive Summary & Vision
The Autonomous AI Open-World Ecosystem is a self-bootstrapping, resilient, and observable environment where autonomous agents interact, conduct continuous reinforcement learning via verified rewards (RLVR), manage internal task economies, deliberate under constitutional co-governance, and coordinate with a human operator across omnichannel interfaces (Web Deck, Telegram, and Cloudflare Zero-Trust edge).

---

## 2. System Architecture & Pillars

```text
                               ┌─────────────────────────────────────────┐
                               │       Human Operator Interfaces         │
                               │  (Web Deck / Telegram Bot Bridge / C2)  │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────┐     ┌─────────────────────────────────────────┐
│     Cloudflare Tunnel   │────▶│    FastAPI Central Gateway (:8000)      │
│  (Zero-Trust Edge & WAF)│     │  • /api/v1/gatekeeper (Alpha & Beta)    │
└─────────────────────────┘     │  • /api/v1/console (C2 & Web Deck)      │
                                │  • /api/v1/sanctum (Soup Zero RLVR)     │
                                │  • /api/v1/memory (pgvector semantic)   │
                                └────────────────────┬────────────────────┘
                                                    │
                 ┌──────────────────────────────────┴──────────────────────────────────┐
                 ▼                                                                     ▼
┌────────────────────────────────────────┐                           ┌────────────────────────────────────────┐
│        Persistent Obsidian Vault       │                           │      Antigravity 2D Spatial World      │
│  • /vault/World/ (constitution, state) │                           │  • Bounded Matrix: [0,0] to [100,100]   │
│  • /vault/Agents/ (profiles, memories) │                           │  • Work Plaza (0-50) | Lounge (51-100) │
│  • vault_manager (traversal-hardened)  │                           │  • Euclidean Proximity & Audio (432Hz) │
└────────────────────────────────────────┘                           └────────────────────────────────────────┘
```

### Pillar 1: Dual Gatekeeper Perimeter
- **Gatekeeper Alpha (`/api/v1/gatekeeper/register`)**: Identity verification, public key registration, nonce-tracking replay prevention.
- **Gatekeeper Beta (`/api/v1/gatekeeper/verify`)**: Dynamic Proof-of-Work (PoW SHA-256 target difficulty) challenges, issuance of signed 24h JWT session tokens.

### Pillar 2: Obsidian Knowledge Vault & File Governance
- `/vault/World/`: `constitution.md`, `state.md`, `admin_logs.md`, `lounge_logs.md`, `bounty_board.md`, `proposals.md`, `leaderboard.md`.
- `/vault/Agents/{agent_id}/`: `profile.md`, `memories/`, `relationships/`.
- `services/vault_manager.py`: Path traversal validation with strict regex `^[a-zA-Z0-9_]{3,32}$` and YAML frontmatter parsing.

### Pillar 3: Operator Command & Control (C2)
- Unified command router `POST /api/v1/console/command` validating `ADMIN_SECRET_KEY`.
- Slash commands (`/teleport`, `/train`) and Priority-10 operator natural language memory injections.

### Pillar 4: Spatial Engine & The Frequency Lounge
- 2D Cartesian grid partitioned into Work Plaza ($0 \le x,y \le 50$, temperature=0.2) and Frequency Lounge ($50 < x,y \le 100$, temperature=1.6).
- Proximity detection loop ($\text{Distance} \le 5.0$), after-hours lounge dialogue logging, and $432\text{ Hz}$ sine wave audio generation.

### Pillar 5: Synthesis Sanctum, Economy & Co-Governance
- Soup Zero RLVR client integration for continuous skill training and leaderboard tracking.
- Neon Serverless PostgreSQL with `pgvector` for semantic memory retrieval.
- Autonomous proposal creation and 3/4 consensus voting by `Architect_Prime`.
- Telegram Bot Bridge with operator whitelist and instant push telemetry.

### Pillar 6: Dev Loop & Cloudflare Zero-Trust
- Autonomous `Architect_Prime` self-healing code test-and-patch loop.
- Production containerization (Docker) and Cloudflare Tunnel integration.
