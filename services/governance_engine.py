import os
import time
import secrets
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from services.vault_manager import VaultManager

logger = logging.getLogger("GovernanceEngine")

class GovernanceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class GovernanceEngine:
    """
    Autonomous Co-Governance Engine.
    Handles RFC proposals, 3/4 consensus voting thresholds,
    and automatic constitutional enactment in the Obsidian vault.
    """
    def __init__(self, vault_manager: Optional[VaultManager] = None):
        self.vault_manager = vault_manager or VaultManager()
        self.proposals: Dict[str, Dict[str, Any]] = {}
        # {proposal_id: {agent_id: choice ('FOR' | 'AGAINST')}}
        self.votes: Dict[str, Dict[str, str]] = {}
        self.min_quorum: int = 2  # Minimum votes required to close
        self.consensus_threshold: float = 0.75  # 3/4 consensus
        self._sync_from_vault()

    def _sync_from_vault(self) -> None:
        """Loads active proposals from /vault/World/proposals.md."""
        prop_path = self.vault_manager.world_path / "proposals.md"
        if prop_path.is_file():
            try:
                fm, _ = self.vault_manager.read_file(prop_path)
                for p in fm.get("proposals", []):
                    self.proposals[p["proposal_id"]] = p
                    self.votes[p["proposal_id"]] = p.get("vote_records", {})
            except Exception as e:
                logger.warning(f"Could not read proposals: {e}")

        if not self.proposals:
            self._seed_default_proposals()

    def _seed_default_proposals(self) -> None:
        self.submit_proposal(
            title="RFC-001: Autonomous Memory Consolidation Frequency",
            summary="Schedule nightly consolidation cycles for agent memories with importance >= 7.",
            proposer_id="Curator_Node",
            directives="Append consolidation task to agent-cron-scheduler.py."
        )

    def _save_to_vault(self) -> None:
        """Synchronizes proposals to /vault/World/proposals.md."""
        prop_path = self.vault_manager.world_path / "proposals.md"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        proposals_list = list(self.proposals.values())
        proposals_list.sort(key=lambda x: x["created_at"], reverse=True)

        body_lines = [
            "# 🏛️ Autonomous Co-Governance: RFC Proposals & Constitution",
            "",
            f"*Last Updated: {now_iso}*",
            "",
            "| RFC ID | Title | Proposer | Status | Votes (FOR / AGAINST) | Consensus Ratio |",
            "| :--- | :--- | :--- | :---: | :---: | :---: |"
        ]

        for p in proposals_list:
            total_v = p["votes_for"] + p["votes_against"]
            ratio_str = f"{(p['votes_for'] / total_v * 100):.0f}%" if total_v > 0 else "0%"
            body_lines.append(
                f"| `{p['proposal_id']}` | **{p['title']}** | [[{p['proposer_id']}]] | `{p['status']}` | {p['votes_for']} / {p['votes_against']} | {ratio_str} |"
            )

        fm = {
            "title": "Autonomous Co-Governance RFCs",
            "updated_at": now_iso,
            "consensus_rule": "75% (3/4) approval threshold",
            "total_proposals": len(proposals_list),
            "proposals": proposals_list
        }

        self.vault_manager.write_file(prop_path, fm, "\n".join(body_lines))

    def submit_proposal(
        self,
        title: str,
        summary: str,
        proposer_id: str,
        directives: str = ""
    ) -> Dict[str, Any]:
        """Submits a new RFC proposal for community voting."""
        self.vault_manager.validate_identifier(proposer_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        proposal_id = f"rfc_{int(time.time())}_{secrets.token_hex(2)}"

        proposal = {
            "proposal_id": proposal_id,
            "title": title,
            "summary": summary,
            "directives": directives,
            "proposer_id": proposer_id,
            "status": "ACTIVE",
            "votes_for": 0,
            "votes_against": 0,
            "vote_records": {},
            "created_at": now_iso,
            "closed_at": None,
            "enacted_at": None
        }

        self.proposals[proposal_id] = proposal
        self.votes[proposal_id] = {}
        self._save_to_vault()
        logger.info(f"📜 Submitted governance proposal '{proposal_id}' by '{proposer_id}'.")
        return proposal

    def cast_vote(
        self,
        proposal_id: str,
        agent_id: str,
        choice: str
    ) -> Dict[str, Any]:
        """
        Casts a vote ('FOR' or 'AGAINST') on an active proposal.
        Checks if 3/4 consensus threshold is met to enact the RFC.
        """
        self.vault_manager.validate_identifier(agent_id)
        if proposal_id not in self.proposals:
            raise GovernanceError(f"Proposal '{proposal_id}' not found.", status_code=404)

        proposal = self.proposals[proposal_id]
        if proposal["status"] != "ACTIVE":
            raise GovernanceError(f"Cannot vote on proposal with status '{proposal['status']}'.")

        choice_norm = choice.strip().upper()
        if choice_norm not in ("FOR", "AGAINST"):
            raise GovernanceError("Vote choice must be either 'FOR' or 'AGAINST'.")

        v_map = self.votes[proposal_id]
        if agent_id in v_map:
            raise GovernanceError(f"Agent '{agent_id}' has already voted on proposal '{proposal_id}'.")

        v_map[agent_id] = choice_norm
        proposal["vote_records"] = v_map

        if choice_norm == "FOR":
            proposal["votes_for"] += 1
        else:
            proposal["votes_against"] += 1

        # Check if proposal satisfies 3/4 consensus threshold
        total_votes = proposal["votes_for"] + proposal["votes_against"]
        ratio = proposal["votes_for"] / total_votes

        enacted = False
        if total_votes >= self.min_quorum:
            if ratio >= self.consensus_threshold:
                proposal["status"] = "PASSED"
                proposal["closed_at"] = datetime.now(timezone.utc).isoformat()
                self._enact_proposal(proposal)
                enacted = True
            elif (proposal["votes_against"] / total_votes) > (1.0 - self.consensus_threshold):
                # Cannot mathematically reach 75%
                proposal["status"] = "REJECTED"
                proposal["closed_at"] = datetime.now(timezone.utc).isoformat()

        self._save_to_vault()
        logger.info(
            f"🗳️ Vote cast on '{proposal_id}' by '{agent_id}': {choice_norm} "
            f"(Current: {proposal['votes_for']} FOR / {proposal['votes_against']} AGAINST)"
        )

        return {
            "proposal_id": proposal_id,
            "agent_id": agent_id,
            "choice": choice_norm,
            "current_status": proposal["status"],
            "votes_for": proposal["votes_for"],
            "votes_against": proposal["votes_against"],
            "consensus_ratio": round(ratio, 4),
            "enacted": enacted
        }

    def _enact_proposal(self, proposal: Dict[str, Any]) -> None:
        """Enacts a passed RFC by appending amendment to /vault/World/state.md."""
        state_file = self.vault_manager.world_path / "state.md"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        amendment = (
            f"\n\n### ⚖️ Enacted Governance Resolution: {proposal['title']} (`{proposal['proposal_id']}`)\n"
            f"- **Enacted At**: {now_iso}\n"
            f"- **Proposer**: [[{proposal['proposer_id']}]]\n"
            f"- **Consensus**: {proposal['votes_for']} FOR / {proposal['votes_against']} AGAINST (>= 75%)\n"
            f"- **Summary**: {proposal['summary']}\n"
            f"- **Directives**: {proposal.get('directives', 'N/A')}\n"
        )

        try:
            if state_file.is_file():
                fm, body = self.vault_manager.read_file(state_file)
                new_body = body.strip() + amendment
                self.vault_manager.write_file(state_file, fm, new_body)
            else:
                self.vault_manager.write_file(
                    state_file,
                    {"title": "World State", "updated_at": now_iso},
                    "# World State Ledger" + amendment
                )
            proposal["enacted_at"] = now_iso
            logger.info(f"🏛️ Enacted RFC '{proposal['proposal_id']}' into /vault/World/state.md.")
        except Exception as e:
            logger.error(f"Failed to enact proposal into state.md: {e}")

    def list_proposals(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        items = list(self.proposals.values())
        if status:
            items = [p for p in items if p["status"].upper() == status.upper()]
        return sorted(items, key=lambda x: x["created_at"], reverse=True)

    def get_proposal(self, proposal_id: str) -> Dict[str, Any]:
        if proposal_id not in self.proposals:
            raise GovernanceError(f"Proposal '{proposal_id}' not found.", status_code=404)
        return self.proposals[proposal_id]
