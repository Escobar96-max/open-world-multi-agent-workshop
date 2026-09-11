import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from services.dev_loop import DevLoopEngine, DevLoopSafetyError
from services.vault_manager import VaultManager

logger = logging.getLogger("DevLoopRouter")

router = APIRouter(prefix="/api/v1/devloop", tags=["Autonomous Self-Healing Dev Loop"])

vault_mgr = VaultManager()
dev_loop = DevLoopEngine(vault_manager=vault_mgr)

# Schemas
class TestRunRequest(BaseModel):
    target: Optional[str] = Field(None, description="Specific test file or directory (default: 'tests/')")
    timeout_seconds: int = Field(60, ge=5, le=300, description="Max execution duration")

class PatchRequest(BaseModel):
    file_path: str = Field(..., description="Relative file path within project")
    target_content: str = Field(..., description="Exact character string to be replaced")
    replacement_content: str = Field(..., description="Replacement character string")
    verify_regression: bool = Field(True, description="Whether to run full tests and revert on regression")

@router.get("/health", summary="Get Self-Healing Dev Loop Health Metrics")
async def get_health():
    """Returns the operational status, patch history, and safety boundaries of the dev loop."""
    return dev_loop.get_health_metrics()

@router.post("/run-tests", summary="Trigger On-Demand Test Suite Execution")
async def run_tests_endpoint(req: TestRunRequest):
    """Executes test suite and returns parsed results, durations, and diagnostics."""
    res = dev_loop.run_tests(test_target=req.target, timeout_seconds=req.timeout_seconds)
    return res

@router.post("/auto-heal", summary="Trigger Autonomous Diagnostic & Self-Healing Cycle")
async def auto_heal_endpoint():
    """
    Executes Architect_Prime autonomous test cycle.
    If failures exist, prepares failure diagnosis and candidate patch parameters.
    """
    return dev_loop.execute_self_healing_cycle()

@router.post("/apply-patch", summary="Apply Candidate Patch with Rollback Protection")
async def apply_patch_endpoint(req: PatchRequest):
    """
    Applies a targeted code patch, verifies that tests remain green,
    and automatically reverts if a regression occurs.
    """
    try:
        res = dev_loop.apply_patch(
            relative_file_path=req.file_path,
            target_content=req.target_content,
            replacement_content=req.replacement_content,
            verify_regression=req.verify_regression
        )
        return res
    except DevLoopSafetyError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error applying patch: {e}")
        raise HTTPException(status_code=500, detail=str(e))
