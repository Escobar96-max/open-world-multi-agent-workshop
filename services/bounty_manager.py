import os
import time
import secrets
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from services.vault_manager import VaultManager
from services.ledger_service import LedgerService, LedgerError

logger = logging.getLogger("BountyManager")

class BountyError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class BountyManager:
    """
    Manages the Open-World Task & Bounty Marketplace.
    Handles lifecycle transitions (OPEN -> CLAIMED -> SUBMITTED -> COMPLETED),
    vault markdown synchronization (/vault/World/bounty_board.md),
    and automated token escrow settlements via LedgerService.
    """
    def __init__(
        self,
        vault_manager: Optional[VaultManager] = None,
        ledger_service: Optional[LedgerService] = None
    ):
        self.vault_manager = vault_manager or VaultManager()
        self.ledger_service = ledger_service or LedgerService()
        self.bounties: Dict[str, Dict[str, Any]] = {}
        self._sync_from_vault()

    def _sync_from_vault(self) -> None:
        """Loads existing bounties from /vault/World/bounty_board.md if it exists."""
        board_path = self.vault_manager.world_path / "bounty_board.md"
        if board_path.is_file():
            try:
                fm, _ = self.vault_manager.read_file(board_path)
                items = fm.get("bounties", [])
                for b in items:
                    self.bounties[b["bounty_id"]] = b
            except Exception as e:
                logger.warning(f"Could not read bounty board: {e}")

        # Seed initial bounties if empty
        if not self.bounties:
            self._seed_default_bounties()

    def _seed_default_bounties(self) -> None:
        self.create_bounty(
            title="Calibrate Acoustic Harmonic Resonator",
            description="Run a sweep of 432Hz, 528Hz, and 40Hz frequencies in Frequency Lounge and log telemetry.",
            reward=120.0,
            posted_by="Architect_Prime"
        )
        self.create_bounty(
            title="Synthesize Gatekeeper Intrusion Vectors",
            description="Construct non-replayable cryptographic PoW test harness for Gatekeeper Beta.",
            reward=250.0,
            posted_by="Curator_Node"
        )

    def _save_to_vault(self) -> None:
        """Synchronizes all bounties to /vault/World/bounty_board.md."""
        board_path = self.vault_manager.world_path / "bounty_board.md"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        bounties_list = list(self.bounties.values())
        bounties_list.sort(key=lambda x: x["created_at"], reverse=True)

        body_lines = [
            "# 📋 Open-World Task & Bounty Marketplace",
            "",
            f"*Last Updated: {now_iso}*",
            "",
            "| ID | Title | Reward | Poster | Assignee | Status |",
            "| :--- | :--- | :---: | :--- | :--- | :---: |"
        ]

        for b in bounties_list:
            assignee_str = f"[[{b['assignee']}]]" if b.get("assignee") else "—"
            body_lines.append(
                f"| `{b['bounty_id']}` | **{b['title']}** | {b['reward']} TK | [[{b['posted_by']}]] | {assignee_str} | `{b['status']}` |"
            )

        fm = {
            "title": "Bounty Marketplace",
            "updated_at": now_iso,
            "total_bounties": len(bounties_list),
            "open_count": len([b for b in bounties_list if b["status"] == "OPEN"]),
            "bounties": bounties_list
        }

        self.vault_manager.write_file(board_path, fm, "\n".join(body_lines))

    def create_bounty(
        self,
        title: str,
        description: str,
        reward: float,
        posted_by: str
    ) -> Dict[str, Any]:
        """Creates a new bounty. Validates poster balance sufficiency."""
        self.vault_manager.validate_identifier(posted_by)
        if reward <= 0:
            raise BountyError("Bounty reward must be greater than 0.")

        # Check that poster has sufficient balance
        poster_bal = self.ledger_service.get_balance(posted_by)
        if poster_bal < reward:
            raise BountyError(
                f"Poster '{posted_by}' has insufficient funds ({poster_bal} TK) for reward ({reward} TK)."
            )

        bounty_id = f"bounty_{int(time.time())}_{secrets.token_hex(2)}"
        now_iso = datetime.now(timezone.utc).isoformat()

        bounty = {
            "bounty_id": bounty_id,
            "title": title,
            "description": description,
            "reward": float(reward),
            "posted_by": posted_by,
            "assignee": None,
            "status": "OPEN",
            "proof_of_work": None,
            "created_at": now_iso,
            "updated_at": now_iso,
            "completed_at": None
        }

        self.bounties[bounty_id] = bounty
        self._save_to_vault()
        logger.info(f"✨ Created bounty '{bounty_id}' by '{posted_by}' for {reward} TK.")
        return bounty

    def list_bounties(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all bounties, optionally filtered by status (OPEN, CLAIMED, etc.)."""
        items = list(self.bounties.values())
        if status:
            items = [b for b in items if b["status"].upper() == status.upper()]
        return sorted(items, key=lambda x: x["created_at"], reverse=True)

    def get_bounty(self, bounty_id: str) -> Dict[str, Any]:
        if bounty_id not in self.bounties:
            raise BountyError(f"Bounty '{bounty_id}' does not exist.", status_code=404)
        return self.bounties[bounty_id]

    def claim_bounty(self, bounty_id: str, agent_id: str) -> Dict[str, Any]:
        """Allows an agent to claim an OPEN bounty."""
        self.vault_manager.validate_identifier(agent_id)
        bounty = self.get_bounty(bounty_id)

        if bounty["status"] != "OPEN":
            raise BountyError(f"Cannot claim bounty with status '{bounty['status']}'. Must be OPEN.")
        if bounty["posted_by"] == agent_id:
            raise BountyError("Agents cannot claim their own bounties.")

        bounty["assignee"] = agent_id
        bounty["status"] = "CLAIMED"
        bounty["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_to_vault()
        logger.info(f"📌 Bounty '{bounty_id}' claimed by '{agent_id}'.")
        return bounty

    def submit_bounty_work(
        self,
        bounty_id: str,
        agent_id: str,
        proof_of_work: str
    ) -> Dict[str, Any]:
        """Allows assignee to submit proof of work for verification."""
        self.vault_manager.validate_identifier(agent_id)
        bounty = self.get_bounty(bounty_id)

        if bounty["status"] != "CLAIMED":
            raise BountyError(f"Cannot submit work for bounty with status '{bounty['status']}'. Must be CLAIMED.")
        if bounty["assignee"] != agent_id:
            raise BountyError(f"Agent '{agent_id}' is not the assignee for this bounty.")

        bounty["proof_of_work"] = proof_of_work
        bounty["status"] = "SUBMITTED"
        bounty["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_to_vault()
        logger.info(f"📤 Bounty '{bounty_id}' work submitted by '{agent_id}'.")
        return bounty

    def complete_bounty(
        self,
        bounty_id: str,
        verifier_id: str
    ) -> Dict[str, Any]:
        """
        Completes bounty, releases reward tokens from posted_by to assignee via LedgerService.
        Can be verified by the poster, Architect_Prime, or operator.
        """
        bounty = self.get_bounty(bounty_id)

        if bounty["status"] not in ("CLAIMED", "SUBMITTED"):
            raise BountyError(f"Cannot complete bounty with status '{bounty['status']}'.")

        assignee = bounty["assignee"]
        if not assignee:
            raise BountyError("Bounty has no assignee to pay reward to.")

        # Authorized verifiers: original poster, Architect_Prime, or operator
        if verifier_id not in (bounty["posted_by"], "Architect_Prime", "operator"):
            raise BountyError(
                f"Agent '{verifier_id}' is not authorized to approve completion of this bounty.",
                status_code=403
            )

        # Execute settlement payout via Ledger
        reward = bounty["reward"]
        tx = self.ledger_service.transfer_tokens(
            sender_id=bounty["posted_by"],
            recipient_id=assignee,
            amount=reward,
            memo=f"Bounty Payout: {bounty['title']} ({bounty_id})"
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        bounty["status"] = "COMPLETED"
        bounty["completed_at"] = now_iso
        bounty["updated_at"] = now_iso
        bounty["settlement_tx_id"] = tx["tx_id"]

        self._save_to_vault()
        logger.info(f"🎉 Bounty '{bounty_id}' completed! {reward} TK transferred to '{assignee}'.")
        return {
            "status": "COMPLETED",
            "bounty": bounty,
            "settlement_transaction": tx
        }
