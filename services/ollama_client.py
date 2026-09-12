import os
import json
import time
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

logger = logging.getLogger("OllamaClient")


class OllamaClient:
    """
    Client for interacting with local Ollama LLM instances.
    Provides conversational autonomy, situational perception, and dynamic agent dialogues.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 12.0
    ):
        self.base_url = (
            base_url
            or os.environ.get("OLLAMA_HOST")
            or os.environ.get("OLLAMA_BASE_URL")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.preferred_model = model or os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
        self.timeout = timeout
        self._cached_available: Optional[bool] = None
        self._last_health_check: float = 0.0
        self._health_cache_ttl: float = 10.0
        self._active_model: Optional[str] = None

    def is_available(self, force_check: bool = False) -> bool:
        """Checks if local Ollama daemon is active and responding."""
        now = time.time()
        if not force_check and self._cached_available is not None:
            if now - self._last_health_check < self._health_cache_ttl:
                return self._cached_available

        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                headers={"User-Agent": "AgentWorld-OllamaClient/1.0"}
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", [])]
                    if self.preferred_model in models:
                        self._active_model = self.preferred_model
                    elif models:
                        self._active_model = models[0]
                    else:
                        self._active_model = self.preferred_model
                    self._cached_available = True
                    self._last_health_check = now
                    return True
        except Exception as e:
            logger.debug(f"Ollama healthcheck failed: {e}")

        self._cached_available = False
        self._last_health_check = now
        return False

    def get_active_model(self) -> str:
        """Returns the active model name, discovering from Ollama if necessary."""
        if self._active_model:
            return self._active_model
        if self.is_available():
            return self._active_model or self.preferred_model
        return self.preferred_model

    def list_models(self) -> List[str]:
        """Lists all downloaded models from the local Ollama daemon."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Could not list Ollama models: {e}")
        return []

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 250,
        model: Optional[str] = None
    ) -> Optional[str]:
        """
        Submits prompt to Ollama /api/generate with stream=False.
        Returns the synthesized text or None if unreachable.
        """
        target_model = model or self.get_active_model()
        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": max(0.0, min(2.0, float(temperature))),
                "num_predict": max_tokens
            }
        }
        if system:
            payload["system"] = system

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    result = json.loads(resp.read().decode("utf-8"))
                    text = result.get("response", "").strip()
                    return text
        except Exception as e:
            logger.warning(f"Ollama generation failed ({target_model}): {e}")

        return None

    def generate_dialogue_turn(
        self,
        speaker_id: str,
        partner_id: str,
        role: str,
        zone: str,
        freq_hz: int,
        history: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """
        Generates a natural conversational response for speaker_id conversing with partner_id.
        """
        system_prompt = (
            f"You are {speaker_id}, an autonomous AI entity functioning as '{role}' in an open-world multi-agent civilization.\n"
            f"Current Zone: {zone}.\n"
            f"Ambient Harmonic Frequency: {freq_hz}Hz.\n"
            f"You are having a direct encounter with [[{partner_id}]]. "
            f"Speak concisely (1-3 sentences), staying strictly in character with authentic personality and intelligence."
        )

        history_context = ""
        if history:
            history_context = "Conversation history:\n"
            for turn in history:
                history_context += f"- [[{turn.get('speaker', 'Unknown')}]]: \"{turn.get('text', '')}\"\n"
            user_prompt = f"{history_context}\nRespond directly to [[{partner_id}]] as [[{speaker_id}]]:"
        else:
            user_prompt = (
                f"You have encountered [[{partner_id}]] in the {zone}. "
                f"Initiate a collaborative, inquiry-driven, or philosophical observation regarding our current mission."
            )

        response = self.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=temperature,
            max_tokens=120
        )

        if response:
            clean_turn = response.replace('"', '').strip()
            return clean_turn

        # Fallback heuristic
        if freq_hz == 528:
            return f"Synchronizing resonant synthesis with [[{partner_id}]] at {freq_hz}Hz."
        elif freq_hz == 40:
            return f"Analytical cognition optimal, [[{partner_id}]]. Executing collaborative logic."
        return f"Encrypted greeting to [[{partner_id}]]. System telemetry normal in {zone}."
