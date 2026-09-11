import pytest
from services.dj_frequency import DJFrequencyNode, SUPPORTED_FREQUENCIES

def test_dj_frequency_defaults():
    dj = DJFrequencyNode()
    state = dj.get_current_state()
    assert state["active_frequency_hz"] == 432
    assert state["cognitive_state"] == "EQUILIBRIUM"
    assert state["tone_type"] == "sine"
    assert state["gain"] > 0
    assert 432 in state["supported_frequencies"]
    assert 528 in state["supported_frequencies"]
    assert 40 in state["supported_frequencies"]

def test_dj_frequency_transitions():
    dj = DJFrequencyNode()
    # Transition to 528Hz
    res_528 = dj.set_frequency(528, reason="Creative Expansion Testing")
    assert res_528["active_frequency_hz"] == 528
    assert res_528["cognitive_state"] == "CREATIVE_EXPANSION"

    # Transition to 40Hz
    res_40 = dj.set_frequency(40, reason="Gamma Focus Testing")
    assert res_40["active_frequency_hz"] == 40
    assert res_40["cognitive_state"] == "GAMMA_HYPERFOCUS"

    # Unsupported frequency raises ValueError
    with pytest.raises(ValueError):
        dj.set_frequency(999)

def test_cognitive_temperature_modulation():
    dj = DJFrequencyNode()
    
    # 432Hz baseline
    dj.set_frequency(432)
    temp_work_432 = dj.calculate_cognitive_temperature("Work Plaza")
    temp_lounge_432 = dj.calculate_cognitive_temperature("Frequency Lounge")
    assert temp_work_432 == 0.2
    assert temp_lounge_432 == 1.6

    # 528Hz raises creativity slightly
    dj.set_frequency(528)
    temp_lounge_528 = dj.calculate_cognitive_temperature("Frequency Lounge")
    assert temp_lounge_528 >= temp_lounge_432

    # 40Hz tightens reasoning (lowers temperature)
    dj.set_frequency(40)
    temp_lounge_40 = dj.calculate_cognitive_temperature("Frequency Lounge")
    assert temp_lounge_40 < temp_lounge_432
