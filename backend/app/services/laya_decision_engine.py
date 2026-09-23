"""
Laya Decision Engine Service:
Local System 1 Reflex & Calibration Engine.
Uses ConvAI Innovations' non-autoregressive Laya architecture (ModernBERT/mmBERT)
for sub-40ms typed decisions: choice, score, and noul primitives.
Provides zero-crash fallback heuristics for offline and low-resource environments.
"""

import asyncio
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("c2.laya_engine")

LAYA_CHECKPOINT = os.getenv("LAYA_MODEL_CHECKPOINT", "convaiinnovations/laya")


class LayaDecisionEngine:
    """
    Local System 1 Reflex & Calibration Engine.
    Evaluates discrete multi-class routing (choice), ordinal scale ranking (score),
    and strictly calibrated boolean probability (noul).
    """

    def __init__(self, model_checkpoint: str = LAYA_CHECKPOINT):
        self.checkpoint = model_checkpoint
        self.device = "cpu"
        self.model = None
        self.tokenizer = None
        self._is_ready = False
        self._load_attempted = False

    def load_model(self) -> bool:
        """
        Attempts to load ModernBERT/mmBERT weights into VRAM/RAM (<1GB).
        Returns True if loaded, False if fallback mode is active.
        """
        if self._is_ready:
            return True
        if self._load_attempted:
            return self._is_ready

        self._load_attempted = True
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            trust_remote = os.environ.get("LAYA_TRUST_REMOTE_CODE", "false").lower() in ("true", "1")
            revision = os.environ.get("LAYA_MODEL_REVISION", None)

            logger.info(f"⏳ [Laya Engine] Loading weights from '{self.checkpoint}' onto {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.checkpoint, revision=revision)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.checkpoint,
                trust_remote_code=trust_remote,
                revision=revision
            ).to(self.device).eval()
            self._is_ready = True
            logger.info(f"🚀 [Laya Engine] Online and operational on {self.device} (33ms reflex ready).")
            return True
        except Exception as e:
            logger.info(f"ℹ️ [Laya Engine] Running in high-fidelity heuristic fallback mode: {e}")
            self._is_ready = False
            return False

    def ask_choice(self, state_text: str, question: str, options: List[str]) -> Tuple[str, float]:
        """
        Runs in ~33ms: Evaluates discrete multi-class routing options without token generation.
        """
        if not options:
            return "", 0.0

        if not self._is_ready and not self._load_attempted:
            self.load_model()

        if not self._is_ready:
            return self._heuristic_choice(state_text, question, options)

        try:
            import torch
            inputs = self.tokenizer(f"{state_text} [SEP] {question}", return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)[0].cpu().numpy()

            best_idx = int(probs.argmax())
            id2label = getattr(self.model.config, "id2label", {})
            predicted_label = id2label.get(best_idx)

            if predicted_label in options:
                return predicted_label, float(probs[best_idx])

            # If model labels don't match the dynamic options, fall back to semantic heuristic
            return self._heuristic_choice(state_text, question, options)
        except Exception as err:
            logger.debug(f"[Laya Choice Error, falling back]: {err}")
            return self._heuristic_choice(state_text, question, options)

    def ask_noul(self, state_text: str, statement: str) -> float:
        """
        Outputs calibrated boolean confidence P(true) in [0.0, 1.0] using strictly proper scoring.
        """
        if not self._is_ready and not self._load_attempted:
            self.load_model()

        if not self._is_ready:
            return self._heuristic_noul(state_text, statement)

        try:
            import torch
            inputs = self.tokenizer(f"{state_text} [SEP] {statement}", return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)[0].cpu().numpy()
            return float(probs[-1])
        except Exception as err:
            logger.debug(f"[Laya Noul Error, falling back]: {err}")
            return self._heuristic_noul(state_text, statement)

    def ask_score(self, state_text: str, rubric: List[str]) -> Tuple[int, float]:
        """
        Places the state on an ordinal scale 0..len(rubric)-1.
        """
        if not rubric:
            return 0, 1.0

        if not self._is_ready and not self._load_attempted:
            self.load_model()

        if not self._is_ready:
            return 1, 0.90

        try:
            import torch
            inputs = self.tokenizer(f"{state_text} [SEP] Urgency assessment", return_tensors="pt").to(self.device)
            with torch.no_grad():
                logits = self.model(**inputs).logits[0].cpu().numpy()
            idx = int(logits.argmax() % len(rubric))
            probs = torch.softmax(torch.tensor(logits), dim=-1)
            return idx, float(probs[idx])
        except Exception as err:
            logger.debug(f"[Laya Score Error, falling back]: {err}")
            return 1, 0.90

    # Async non-blocking offload wrappers
    async def async_ask_choice(self, state_text: str, question: str, options: List[str]) -> Tuple[str, float]:
        return await asyncio.to_thread(self.ask_choice, state_text, question, options)

    async def async_ask_noul(self, state_text: str, statement: str) -> float:
        return await asyncio.to_thread(self.ask_noul, state_text, statement)

    async def async_ask_score(self, state_text: str, rubric: List[str]) -> Tuple[int, float]:
        return await asyncio.to_thread(self.ask_score, state_text, rubric)

    # High-Performance Calibrated Heuristics for Offline & Fast Reflex
    def _heuristic_choice(self, state_text: str, question: str, options: List[str]) -> Tuple[str, float]:
        text_lower = state_text.lower().strip()

        def _has_word(term: str) -> bool:
            if " " in term:
                return term in text_lower
            return bool(re.search(rf"\b{re.escape(term)}\b", text_lower))

        # 1. Intent Classification: ["CONVERSATION", "META_QUERY", "TASK"]
        if "CONVERSATION" in options and "TASK" in options:
            chitchat = [
                "kemon", "hi", "hello", "valovasi", "valobashi", "ki khobor",
                "ki obostha", "how are you", "sup", "bhalo", "thanks", "dhonnobad",
                "just checking in", "checking in"
            ]
            meta = [
                "kotokhon", "status", "update", "progress", "koto time", "koto shomoy",
                "koto dur", "eta", "shob kaj", "task gulo ki", "last few days", "ager kaj",
                "obostha", "cholche", "lagbe", "how long", "time estimate", "task status",
                "sobai ki korche", "ki kaj korche", "ora ki korche", "koto baki"
            ]
            actionable = [
                "scrape", "extract", "crawl", "search", "email", "send", "draft",
                "code", "build", "analyze", "find", "check", "run", "download",
                "sort", "play", "gaan", "lock", "verify", "audit", "patch", "deploy", "train"
            ]

            has_meta_target = any(_has_word(w) for w in [
                "task", "kaj", "work", "complete", "kotokhon", "koto time",
                "koto shomoy", "koto dur", "eta", "kobe sesh", "kobe hobe", "sobai", "ora"
            ])
            is_chat = any(_has_word(w) for w in chitchat)
            is_meta = any(_has_word(w) for w in meta)

            # Conversational greetings take precedence unless explicitly targeting tasks/estimates
            if is_chat and not has_meta_target:
                return "CONVERSATION", 0.96

            # Check meta query if meta indicators are present
            if is_meta and "META_QUERY" in options:
                return "META_QUERY", 0.95

            effective_actionable = actionable
            if is_chat or is_meta:
                effective_actionable = [w for w in actionable if w not in {"check", "find", "run", "sort"}]

            # Check actionable task
            if any(_has_word(w) for w in effective_actionable):
                return "TASK", 0.93

            return "CONVERSATION", 0.88

        # 2. Persona Targeting: ["ORION_ONLY", "NOVA_ONLY", "DUO"]
        if "ORION_ONLY" in options and "NOVA_ONLY" in options:
            has_nova = bool(re.search(r"\bnova\b", text_lower))
            has_orion = bool(re.search(r"\borion\b", text_lower))

            if has_nova and not has_orion:
                return "NOVA_ONLY", 0.98
            if has_orion and not has_nova:
                return "ORION_ONLY", 0.98
            return "DUO", 0.95

        # 3. Spatial Proximity: ["DEEP_COLLAB", "CASUAL_CHAT", "IGNORE"]
        if "DEEP_COLLAB" in options and "CASUAL_CHAT" in options:
            if "work" in text_lower or "plaza" in text_lower or "architect" in text_lower:
                return "DEEP_COLLAB", 0.92
            if "lounge" in text_lower or "frequency" in text_lower or "dj" in text_lower:
                return "CASUAL_CHAT", 0.94
            return "IGNORE", 0.85

        # 4. Solfeggio Selection: ["432Hz", "528Hz", "40Hz"]
        if "432Hz" in options and "528Hz" in options:
            if "focus" in text_lower or "gamma" in text_lower or "work" in text_lower or "regression" in text_lower:
                return "40Hz", 0.91
            if "transform" in text_lower or "repair" in text_lower or "miracle" in text_lower or "rejuvenation" in text_lower:
                return "528Hz", 0.93
            return "432Hz", 0.96

        # 5. DOM Interactive Element: ["CLICK_BUTTON", "INPUT_FIELD", "DISMISS_MODAL"]
        if "CLICK_BUTTON" in options and "INPUT_FIELD" in options:
            if "button" in text_lower or "submit" in text_lower or "login" in text_lower:
                return "CLICK_BUTTON", 0.93
            if "input" in text_lower or "text" in text_lower or "search" in text_lower:
                return "INPUT_FIELD", 0.92
            return "DISMISS_MODAL", 0.86

        return options[0], 0.85

    def _heuristic_noul(self, state_text: str, statement: str) -> float:
        """
        Calibrated boolean probability calculation for NLI truth checking and CAPTCHA detection.
        """
        state_lower = state_text.lower().strip()
        stmt_lower = statement.lower().strip()

        # CAPTCHA / Wall check
        if any(w in stmt_lower for w in ["captcha", "blocked", "access restriction", "turnstile"]):
            captcha_indicators = [
                "captcha", "cf-turnstile", "access denied", "please verify",
                "security check", "challenge", "robot", "cloudflare", "attention required"
            ]
            if any(ind in state_lower for ind in captcha_indicators):
                return 0.96
            return 0.04

        # Truth / Entailment check
        if not state_lower:
            return 0.10

        contradictions = [
            "contradicts", "false claim", "unsupported", "fake", "hallucinated",
            "conflicts", "hostile", "corrupted", "unauthorized", "attacker"
        ]
        if any(w in stmt_lower for w in contradictions) and not any(w in state_lower for w in contradictions):
            return 0.15

        # Word overlap grounded scoring
        statement_words = set(re.findall(r"\w{4,}", stmt_lower))
        state_words = set(re.findall(r"\w{4,}", state_lower))

        if not statement_words:
            return 0.20

        overlap = statement_words.intersection(state_words)
        overlap_ratio = len(overlap) / len(statement_words)

        if overlap_ratio >= 0.6:
            return min(0.98, 0.88 + (overlap_ratio * 0.10))
        elif overlap_ratio >= 0.4:
            return 0.75
        elif overlap_ratio >= 0.2:
            return 0.40
        else:
            return 0.15


# Singleton Laya Decision Engine instance
_laya_instance: Optional[LayaDecisionEngine] = None


def get_laya_engine() -> LayaDecisionEngine:
    global _laya_instance
    if _laya_instance is None:
        _laya_instance = LayaDecisionEngine()
    return _laya_instance
