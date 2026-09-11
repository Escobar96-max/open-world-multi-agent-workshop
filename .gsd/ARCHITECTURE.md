# Project Agent World: Architecture & System Design

## 🏛️ System Topology
Project Agent World is an autonomous open-world ecosystem combining persistent Obsidian vault memory, dynamic cryptographic Gatekeepers, a 2D Cartesian spatial simulation grid, Soup Zero RLVR, and operator command-and-control.

```
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

## 🔐 Core Components
1. **Dual Gatekeeper**:
   - Alpha: Identity verification, public key registration, nonce-tracking replay prevention.
   - Beta: Dynamic Proof-of-Work (PoW SHA-256) challenge & 24-hour signed JWT session issuance.
2. **Obsidian Vault & File Governance**:
   - Path-traversal-hardened manager (`services/vault_manager.py`) with YAML frontmatter parsing.
   - World state (`constitution.md`, `state.md`, `admin_logs.md`, `lounge_logs.md`).
3. **Spatial Plane & Frequency Lounge**:
   - 2D grid partitioned into Work Plaza ($0-50$, temp=0.2) and Frequency Lounge ($51-100$, temp=1.6).
   - Distance detection loop ($\le 5.0$), ambient frequencies ($432\text{ Hz}, 528\text{ Hz}, 40\text{ Hz}$).
4. **Operator C2 Bridge**:
   - Authenticated console endpoints for slash commands (`/teleport`, `/train`), memory injection, and real-time telemetry.
