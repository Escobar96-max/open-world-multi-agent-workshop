import os
import time
import secrets
import hashlib
import jwt
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from .vault_manager import IDENTIFIER_PATTERN, VaultSecurityError

class GatekeeperError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class ReplayAttackError(GatekeeperError):
    def __init__(self, message: str = "Replay attack detected: Nonce has already been consumed."):
        super().__init__(message, status_code=403)

class ChallengeExpiredError(GatekeeperError):
    def __init__(self, message: str = "Proof-of-Work challenge has expired or does not exist."):
        super().__init__(message, status_code=400)

class InvalidProofError(GatekeeperError):
    def __init__(self, message: str = "Invalid Proof-of-Work solution."):
        super().__init__(message, status_code=400)

class GatekeeperService:
    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        difficulty: Optional[int] = None,
        jwt_expiry_hours: int = 24
    ):
        self.jwt_secret = jwt_secret or os.getenv("JWT_SECRET_KEY", "openworld_default_jwt_secret_key_99")
        self.difficulty = difficulty or int(os.getenv("GATEKEEPER_POW_DIFFICULTY", "4"))
        self.jwt_expiry_hours = jwt_expiry_hours
        
        # In-memory stores (can be backed by DB/Redis in production)
        # {agent_id: set(consumed_nonces)}
        self.consumed_nonces: Dict[str, set] = {}
        # Registered agents: {agent_id: {public_key, registered_at}}
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        # Active challenges: {challenge_id: {agent_id, salt, difficulty, created_at, expires_at}}
        self.active_challenges: Dict[str, Dict[str, Any]] = {}

    def validate_agent_id(self, agent_id: str) -> None:
        if not agent_id or not isinstance(agent_id, str):
            raise GatekeeperError("agent_id must be a non-empty string.", status_code=400)
        if ".." in agent_id or "/" in agent_id or "\\" in agent_id:
            raise GatekeeperError(f"Path traversal characters detected in agent_id: {agent_id}", status_code=400)
        if not IDENTIFIER_PATTERN.match(agent_id):
            raise GatekeeperError(
                f"Invalid agent_id format: '{agent_id}'. Must match ^[a-zA-Z0-9_]{{3,32}}$.",
                status_code=400
            )

    def register_agent(self, agent_id: str, public_key: str, nonce: str) -> Dict[str, Any]:
        """
        Gatekeeper Alpha: Validates public key, registers agent, and checks nonce replay protection.
        Generates and returns a Proof-of-Work challenge for Gatekeeper Beta.
        """
        self.validate_agent_id(agent_id)
        
        if not public_key or not isinstance(public_key, str) or len(public_key.strip()) < 16:
            raise GatekeeperError("Invalid public_key provided. Must be at least 16 characters.", status_code=400)
        
        if not nonce or not isinstance(nonce, str) or len(nonce.strip()) < 8:
            raise GatekeeperError("Invalid nonce. Must be at least 8 characters.", status_code=400)

        # Replay Attack Check
        if agent_id not in self.consumed_nonces:
            self.consumed_nonces[agent_id] = set()

        if nonce in self.consumed_nonces[agent_id]:
            raise ReplayAttackError(f"Replay attack detected: Duplicate nonce detected for agent '{agent_id}'. Request rejected.")

        # Record consumed nonce
        self.consumed_nonces[agent_id].add(nonce)

        # Store agent registration
        self.registered_agents[agent_id] = {
            "agent_id": agent_id,
            "public_key": public_key,
            "registered_at": datetime.now(timezone.utc).isoformat()
        }

        # Issue dynamic PoW Challenge for Gatekeeper Beta
        challenge = self._generate_challenge(agent_id)
        
        return {
            "status": "REGISTERED",
            "message": "Public key registered. Proceed to Gatekeeper Beta Proof-of-Work challenge.",
            "agent_id": agent_id,
            "challenge": challenge
        }

    def _generate_challenge(self, agent_id: str) -> Dict[str, Any]:
        challenge_id = f"pow_{secrets.token_hex(8)}"
        salt = secrets.token_hex(16)
        now = time.time()
        timeout = int(os.getenv("GATEKEEPER_CHALLENGE_TIMEOUT", "300"))
        expires_at = now + timeout

        challenge_data = {
            "challenge_id": challenge_id,
            "agent_id": agent_id,
            "salt": salt,
            "difficulty": self.difficulty,
            "target_prefix": "0" * self.difficulty,
            "algorithm": "SHA-256",
            "expires_at": expires_at
        }
        self.active_challenges[challenge_id] = challenge_data
        return challenge_data

    def request_challenge(self, agent_id: str) -> Dict[str, Any]:
        """Allows an already registered agent to request a fresh challenge."""
        self.validate_agent_id(agent_id)
        return self._generate_challenge(agent_id)

    def verify_pow_and_issue_token(
        self,
        agent_id: str,
        challenge_id: str,
        solution: str
    ) -> Dict[str, Any]:
        """
        Gatekeeper Beta: Verifies Proof-of-Work solution and returns 24h JWT bearer session token.
        Verification formula: SHA-256(salt:solution).hexdigest() must start with '0' * difficulty
        """
        self.validate_agent_id(agent_id)
        
        if challenge_id not in self.active_challenges:
            raise ChallengeExpiredError("Challenge ID not found or already consumed.")

        challenge = self.active_challenges[challenge_id]

        # Verify challenge belongs to agent
        if challenge["agent_id"] != agent_id:
            raise GatekeeperError("Challenge does not belong to specified agent_id.", status_code=403)

        # Check expiration
        if time.time() > challenge["expires_at"]:
            del self.active_challenges[challenge_id]
            raise ChallengeExpiredError("Proof-of-Work challenge has expired.")

        # Compute hash
        salt = challenge["salt"]
        hash_input = f"{salt}:{solution}".encode("utf-8")
        computed_hash = hashlib.sha256(hash_input).hexdigest()
        target_prefix = "0" * challenge["difficulty"]

        if not computed_hash.startswith(target_prefix):
            raise InvalidProofError(
                f"Invalid Proof-of-Work solution: Computed hash '{computed_hash}' does not satisfy target difficulty {challenge['difficulty']} (prefix '{target_prefix}')."
            )

        # Challenge passed: Consume challenge to prevent replay
        del self.active_challenges[challenge_id]

        # Issue 24h JWT session token
        now_dt = datetime.now(timezone.utc)
        exp_dt = now_dt + timedelta(hours=self.jwt_expiry_hours)
        
        payload = {
            "sub": agent_id,
            "role": "authenticated_agent",
            "iat": int(now_dt.timestamp()),
            "exp": int(exp_dt.timestamp()),
            "iss": "openworld_gatekeeper_beta"
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")

        return {
            "status": "VERIFIED",
            "agent_id": agent_id,
            "token_type": "Bearer",
            "access_token": token,
            "expires_in_hours": self.jwt_expiry_hours,
            "hash": computed_hash
        }

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Validates and decodes JWT session token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise GatekeeperError("Session token has expired.", status_code=401)
        except jwt.InvalidTokenError as e:
            raise GatekeeperError(f"Invalid session token: {str(e)}", status_code=401)
