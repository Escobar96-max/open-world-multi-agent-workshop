import os
import json
import base64
import logging
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)


class AgentIdentityService:
    """
    Sovereign Agent Cryptographic Identity & End-to-End Encryption (E2EE) Service.
    
    Provides:
    - Ed25519 Signing Keypairs & Decentralized Identifiers (DIDs)
    - X25519 Diffie-Hellman Key Exchange for Zero-Knowledge Whispers
    - AES-256-GCM authenticated payload encryption
    - Enclave storage under vault/Agents/{agent_id}/.keys/
    - Private Whisper Inboxes under vault/Agents/{agent_id}/whispers/
    """

    def __init__(self, vault_root: str = "vault"):
        self.vault_root = vault_root

    def _get_enclave_dir(self, agent_id: str) -> str:
        enclave = os.path.join(self.vault_root, "Agents", agent_id, ".keys")
        os.makedirs(enclave, exist_ok=True)
        return enclave

    def get_or_create_identity(self, agent_id: str) -> Dict[str, str]:
        """
        Retrieves or generates the Ed25519 signing keypair and X25519 encryption
        keypair for the specified agent. Returns public metadata including DID.
        """
        enclave = self._get_enclave_dir(agent_id)
        sign_priv_path = os.path.join(enclave, "signing_private.key")
        sign_pub_path = os.path.join(enclave, "signing_public.key")
        enc_priv_path = os.path.join(enclave, "encryption_private.key")
        enc_pub_path = os.path.join(enclave, "encryption_public.key")

        # 1. Ed25519 Signing Keys
        if not os.path.exists(sign_priv_path):
            priv = ed25519.Ed25519PrivateKey.generate()
            pub = priv.public_key()

            priv_bytes = priv.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            pub_bytes = pub.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )

            with open(sign_priv_path, "wb") as f:
                f.write(priv_bytes)
            with open(sign_pub_path, "wb") as f:
                f.write(pub_bytes)
        else:
            with open(sign_pub_path, "rb") as f:
                pub_bytes = f.read()

        # 2. X25519 E2EE Encryption Keys
        if not os.path.exists(enc_priv_path):
            enc_priv = x25519.X25519PrivateKey.generate()
            enc_pub = enc_priv.public_key()

            enc_priv_bytes = enc_priv.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            enc_pub_bytes = enc_pub.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )

            with open(enc_priv_path, "wb") as f:
                f.write(enc_priv_bytes)
            with open(enc_pub_path, "wb") as f:
                f.write(enc_pub_bytes)
        else:
            with open(enc_pub_path, "rb") as f:
                enc_pub_bytes = f.read()

        pub_hex = pub_bytes.hex()
        enc_pub_hex = enc_pub_bytes.hex()
        did = f"did:agent:ed25519:{pub_hex[:16]}"

        return {
            "agent_id": agent_id,
            "did": did,
            "signing_public_key": pub_hex,
            "encryption_public_key": enc_pub_hex,
            "enclave_status": "SECURED"
        }

    def sign_payload(self, agent_id: str, payload: Dict[str, Any]) -> str:
        """Cryptographically signs a canonical JSON payload using the agent's Ed25519 private key."""
        enclave = self._get_enclave_dir(agent_id)
        sign_priv_path = os.path.join(enclave, "signing_private.key")
        if not os.path.exists(sign_priv_path):
            self.get_or_create_identity(agent_id)

        with open(sign_priv_path, "rb") as f:
            priv_bytes = f.read()
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)

        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = priv.sign(canonical)
        return signature.hex()

    def verify_signature(self, agent_id: str, payload: Dict[str, Any], signature_hex: str) -> bool:
        """Verifies an Ed25519 signature against an agent's public signing key."""
        enclave = self._get_enclave_dir(agent_id)
        sign_pub_path = os.path.join(enclave, "signing_public.key")
        if not os.path.exists(sign_pub_path):
            self.get_or_create_identity(agent_id)

        with open(sign_pub_path, "rb") as f:
            pub_bytes = f.read()
        pub = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)

        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        try:
            pub.verify(bytes.fromhex(signature_hex), canonical)
            return True
        except Exception:
            return False

    def encrypt_whisper(self, sender_id: str, recipient_id: str, plaintext: str) -> Dict[str, str]:
        """
        Encrypts a private message from sender to recipient using X25519 Diffie-Hellman
        and AES-256-GCM.
        """
        # Ensure identities exist
        sender_id_info = self.get_or_create_identity(sender_id)
        recipient_id_info = self.get_or_create_identity(recipient_id)

        # Load sender encryption private key
        sender_enclave = self._get_enclave_dir(sender_id)
        with open(os.path.join(sender_enclave, "encryption_private.key"), "rb") as f:
            sender_priv_bytes = f.read()
        sender_priv = x25519.X25519PrivateKey.from_private_bytes(sender_priv_bytes)

        # Load recipient encryption public key
        recipient_enclave = self._get_enclave_dir(recipient_id)
        with open(os.path.join(recipient_enclave, "encryption_public.key"), "rb") as f:
            recipient_pub_bytes = f.read()
        recipient_pub = x25519.X25519PublicKey.from_public_bytes(recipient_pub_bytes)

        # Perform Diffie-Hellman key exchange
        shared_secret = sender_priv.exchange(recipient_pub)
        aesgcm = AESGCM(shared_secret)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        # Sign the encrypted transmission
        transmission_header = {
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8")
        }
        sig = self.sign_payload(sender_id, transmission_header)

        return {
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "sender_did": sender_id_info["did"],
            "recipient_did": recipient_id_info["did"],
            "nonce_b64": transmission_header["nonce"],
            "ciphertext_b64": transmission_header["ciphertext"],
            "signature": sig,
            "encryption_algorithm": "X25519-ECDH-AES256-GCM"
        }

    def decrypt_whisper(
        self,
        recipient_id: str,
        sender_id: str,
        ciphertext_b64: str,
        nonce_b64: str,
        signature: Optional[str] = None
    ) -> str:
        """
        Decrypts an incoming whisper for recipient from sender using X25519 Diffie-Hellman
        and AES-256-GCM.
        """
        # Load recipient private key
        recipient_enclave = self._get_enclave_dir(recipient_id)
        with open(os.path.join(recipient_enclave, "encryption_private.key"), "rb") as f:
            recip_priv_bytes = f.read()
        recip_priv = x25519.X25519PrivateKey.from_private_bytes(recip_priv_bytes)

        # Load sender public key
        sender_enclave = self._get_enclave_dir(sender_id)
        with open(os.path.join(sender_enclave, "encryption_public.key"), "rb") as f:
            sender_pub_bytes = f.read()
        sender_pub = x25519.X25519PublicKey.from_public_bytes(sender_pub_bytes)

        # Derive shared key and decrypt
        shared_secret = recip_priv.exchange(sender_pub)
        aesgcm = AESGCM(shared_secret)

        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode("utf-8")
