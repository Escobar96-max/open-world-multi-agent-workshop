import pytest
import shutil
import tempfile
from pathlib import Path
from services.vault_manager import VaultManager, VaultSecurityError

@pytest.fixture
def temp_vault():
    temp_dir = tempfile.mkdtemp()
    vm = VaultManager(vault_path=temp_dir)
    vm.ensure_vault_hierarchy()
    yield vm
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_directory_creation_and_hierarchy(temp_vault):
    """Test that physical vault hierarchy is created."""
    assert temp_vault.agents_path.is_dir()
    assert temp_vault.world_path.is_dir()

def test_frontmatter_read_write(temp_vault):
    """Test reading and writing markdown with YAML frontmatter."""
    agent_id = "Test_Agent"
    fm_in = {
        "agent_id": agent_id,
        "name": "Test Agent",
        "level": 1,
        "tags": ["unit_test", "validator"]
    }
    body_in = "# Test Agent Profile\n\nThis is a test agent body."
    
    temp_vault.write_agent_profile(agent_id, fm_in, body_in)
    
    # Read back
    fm_out, body_out = temp_vault.get_agent_profile(agent_id)
    assert fm_out["agent_id"] == "Test_Agent"
    assert fm_out["level"] == 1
    assert "unit_test" in fm_out["tags"]
    assert "This is a test agent body." in body_out

def test_add_agent_memory(temp_vault):
    """Test adding episodic memory with importance and metadata."""
    agent_id = "Sentinel_Alpha"
    mem_file = temp_vault.add_agent_memory(
        agent_id=agent_id,
        memory_id="mem_test_100",
        content="Detected perimeter anomaly at coordinates [45, 50].",
        importance=10,
        source="Operator_Root",
        tags=["alert", "perimeter"]
    )
    
    assert mem_file.is_file()
    fm, body = temp_vault.read_file(mem_file)
    assert fm["importance"] == 10
    assert fm["source"] == "Operator_Root"
    assert "alert" in fm["tags"]
    assert "Detected perimeter anomaly" in body

def test_bidirectional_relationship(temp_vault):
    """Test that recording a relationship creates bidirectional [[Agent]] files."""
    temp_vault.record_relationship(
        source_agent="Sentinel_Alpha",
        target_agent="Curator_Node",
        affinity=0.85,
        notes="Collaboration on vault indexing."
    )
    
    # Check Sentinel_Alpha side
    sentinel_rel = temp_vault.agents_path / "Sentinel_Alpha" / "relationships" / "Curator_Node.md"
    assert sentinel_rel.is_file()
    fm1, body1 = temp_vault.read_file(sentinel_rel)
    assert fm1["affinity"] == 0.85
    assert "[[Curator_Node]]" in body1

    # Check Curator_Node side (bidirectional)
    curator_rel = temp_vault.agents_path / "Curator_Node" / "relationships" / "Sentinel_Alpha.md"
    assert curator_rel.is_file()
    fm2, body2 = temp_vault.read_file(curator_rel)
    assert fm2["affinity"] == 0.85
    assert "[[Sentinel_Alpha]]" in body2

def test_path_traversal_rejection(temp_vault):
    """Test that path traversal attempts are strictly rejected."""
    traversal_attacks = [
        "../../etc/passwd",
        "../secret_file",
        "/etc/shadow",
        "agent..name",
        "agent/subfolder",
        "agent\\subfolder",
        "a" * 33,  # exceeds 32 chars
        "ab",      # less than 3 chars
        "invalid!agent",
        "agent;rm -rf",
    ]
    
    for attack in traversal_attacks:
        with pytest.raises(VaultSecurityError):
            temp_vault.validate_identifier(attack)
            
        with pytest.raises(VaultSecurityError):
            temp_vault.get_agent_dir(attack)
