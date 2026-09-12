import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("DJFrequency")

SUPPORTED_FREQUENCIES = {
    432: {
        "name": "Harmonic Grounding & Clarity",
        "description": "Natural mathematical tuning (A=432Hz). Promotes cognitive equilibrium, clear thinking, and structural coherence.",
        "state": "EQUILIBRIUM",
        "tone_type": "sine",
        "binaural_beat_hz": 8.0,  # Alpha relaxation
        "lounge_temp_modifier": 0.0,
        "work_temp_modifier": 0.0
    },
    528: {
        "name": "Transformation & High Empathy",
        "description": "Solfeggio 'Miracle' frequency (528Hz). Sparks expressive creativity, open dialogue, and adaptive relationship formation.",
        "state": "CREATIVE_EXPANSION",
        "tone_type": "sine",
        "binaural_beat_hz": 10.0,  # Alpha-Theta crossover
        "lounge_temp_modifier": 0.1,
        "work_temp_modifier": 0.05
    },
    40: {
        "name": "Gamma Synchrony & Deep Synthesis",
        "description": "Gamma wave entrainment (40Hz). Triggers ultra-focused cross-agent logic synthesis and strict computational problem-solving.",
        "state": "GAMMA_HYPERFOCUS",
        "tone_type": "sine",
        "binaural_beat_hz": 40.0,  # Pure Gamma
        "lounge_temp_modifier": -0.4,
        "work_temp_modifier": -0.05
    }
}

class DJFrequencyNode:
    """
    DJ Frequency Node:
    - Broadcasts ambient acoustic frequencies: 432Hz, 528Hz, and 40Hz
    - Modulates agent cognitive temperature across spatial zones
    - Emits real-time resonance telemetry and audio synthesis parameters
    """
    DEFAULT_FREQUENCY = 432

    def __init__(self, initial_frequency: int = DEFAULT_FREQUENCY):
        self.current_frequency = initial_frequency if initial_frequency in SUPPORTED_FREQUENCIES else self.DEFAULT_FREQUENCY
        self.history: List[Dict[str, Any]] = []
        self.gain = 0.35  # Operator listening volume
        self._record_transition(self.current_frequency, "Ecosystem Genesis Initialization")

    def _record_transition(self, freq: int, reason: str):
        record = {
            "frequency_hz": freq,
            "profile": SUPPORTED_FREQUENCIES[freq]["name"],
            "state": SUPPORTED_FREQUENCIES[freq]["state"],
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.history.append(record)
        # Cap history to 50 entries
        if len(self.history) > 50:
            self.history.pop(0)

    def set_frequency(self, freq_hz: int, reason: str = "Operator C2 Command") -> Dict[str, Any]:
        """Sets active DJ frequency. Raises ValueError if unsupported."""
        freq_int = int(freq_hz)
        if freq_int not in SUPPORTED_FREQUENCIES:
            raise ValueError(
                f"Unsupported frequency: {freq_hz}Hz. Supported: {list(SUPPORTED_FREQUENCIES.keys())}Hz"
            )
        
        previous = self.current_frequency
        self.current_frequency = freq_int
        self._record_transition(freq_int, reason)
        logger.info(f"🎶 DJ Frequency Shift: {previous}Hz ➔ {freq_int}Hz ({SUPPORTED_FREQUENCIES[freq_int]['name']})")
        return self.get_current_state()

    def calculate_cognitive_temperature(self, zone: str) -> float:
        """
        Calculates active cognitive temperature based on spatial zone and active acoustic resonance:
        - Work Plaza baseline: 0.2
        - Frequency Lounge baseline: 1.6
        """
        freq_meta = SUPPORTED_FREQUENCIES[self.current_frequency]
        if zone == "Work Plaza":
            base = 0.2
            mod = freq_meta.get("work_temp_modifier", 0.0)
            return round(max(0.05, min(1.0, base + mod)), 2)
        else:
            base = 1.6
            mod = freq_meta.get("lounge_temp_modifier", 0.0)
            return round(max(0.5, min(2.0, base + mod)), 2)

    def get_current_state(self) -> Dict[str, Any]:
        """Returns the complete DJ Frequency Node status and audio synthesis profile."""
        meta = SUPPORTED_FREQUENCIES[self.current_frequency]
        return {
            "active_frequency_hz": self.current_frequency,
            "profile_name": meta["name"],
            "description": meta["description"],
            "cognitive_state": meta["state"],
            "tone_type": meta["tone_type"],
            "gain": self.gain,
            "binaural_beat_hz": meta["binaural_beat_hz"],
            "zone_temperatures": {
                "Work Plaza": self.calculate_cognitive_temperature("Work Plaza"),
                "Frequency Lounge": self.calculate_cognitive_temperature("Frequency Lounge")
            },
            "supported_frequencies": list(SUPPORTED_FREQUENCIES.keys()),
            "last_shift": self.history[-1] if self.history else None
        }

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self.history)

    def get_active_telemetry(self) -> Dict[str, Any]:
        """Alias for get_current_state for telemetry consistency."""
        return self.get_current_state()

