"""
DJ Frequency Node:
Generates 432Hz (Restorative), 528Hz (Miracle/DNA Repair), and 40Hz (Gamma Focus)
harmonic soundscape metadata and logs ambient lounge reflections.
"""

from typing import Any, Dict, Optional
from app.services.vault_manager import VaultManager


class DJFrequencyNode:
    """Manages audio frequency entrainment state and lounge logging."""

    FREQUENCIES = {
        432: {"name": "Restorative Natural Harmonic", "description": "Verdi tuning, soothing cognitive buffers, low stress", "target_temp": 1.6},
        528: {"name": "Solfeggio Transformation", "description": "Transformation and miraculous cognitive expansion", "target_temp": 1.4},
        40: {"name": "Gamma Cognitive Entrainment", "description": "High-focus deep work synchronization", "target_temp": 0.2}
    }

    def __init__(self, vault_manager: Optional[VaultManager] = None):
        self.vault = vault_manager or VaultManager()
        self.current_freq: int = 432
        self.is_playing: bool = True
        self.volume: float = 0.85

    def get_state(self) -> Dict[str, Any]:
        info = self.FREQUENCIES.get(self.current_freq, self.FREQUENCIES[432])
        return {
            "frequency_hz": self.current_freq,
            "name": info["name"],
            "description": info["description"],
            "target_temperature": info["target_temp"],
            "is_playing": self.is_playing,
            "volume": self.volume,
            "supported_frequencies": list(self.FREQUENCIES.keys())
        }

    def set_frequency(self, freq: int) -> Dict[str, Any]:
        if freq not in self.FREQUENCIES:
            return {
                "success": False,
                "error": f"Unsupported frequency {freq}Hz. Supported: {list(self.FREQUENCIES.keys())}",
                "current_state": self.get_state()
            }
        self.current_freq = freq
        info = self.FREQUENCIES[freq]

        self.vault.append_lounge_log(
            speaker="DJ_Frequency",
            message=f"Modulated frequency to {freq}Hz ({info['name']}). State: {info['description']}."
        )
        return {"success": True, **self.get_state()}

    def set_playback(self, playing: bool) -> Dict[str, Any]:
        self.is_playing = playing
        return self.get_state()
