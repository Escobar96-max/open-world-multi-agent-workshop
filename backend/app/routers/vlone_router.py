"""
VLONE Headless Browser Router:
Exposes REST endpoints for headless page perception, element interaction,
and background API sniffing.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.vlone_driver import VloneDriver

router = APIRouter(prefix="/api/v1/vlone", tags=["VLONE Browser"])

_driver = VloneDriver()


def get_vlone_driver() -> VloneDriver:
    return _driver


class OpenUrlRequest(BaseModel):
    url: str
    session_id: Optional[str] = "default"


class InteractRequest(BaseModel):
    action: str
    vlone_id: int
    value: Optional[str] = ""
    session_id: Optional[str] = "default"


@router.post("/open")
async def open_url_endpoint(req: OpenUrlRequest):
    driver = get_vlone_driver()
    if not req.url or not req.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid target URL. Must start with http/https.")

    res = await driver.open_page(url=req.url, session_id=req.session_id or "default")
    return res


@router.post("/interact")
async def interact_endpoint(req: InteractRequest):
    driver = get_vlone_driver()
    res = await driver.interact(
        action=req.action,
        vlone_id=req.vlone_id,
        value=req.value or "",
        session_id=req.session_id or "default"
    )
    return res


@router.get("/sniffed-apis")
async def sniffed_apis_endpoint(session_id: str = "default"):
    driver = get_vlone_driver()
    apis = await driver.get_sniffed_apis(session_id=session_id)
    return {"session_id": session_id, "apis": apis, "count": len(apis)}


@router.get("/state")
def get_vlone_state_endpoint(session_id: str = "default"):
    driver = get_vlone_driver()
    session = driver._active_sessions.get(session_id, {})
    return {
        "session_id": session_id,
        "is_active": bool(session),
        "url": session.get("url", "about:blank"),
        "title": session.get("title", "Inactive Session"),
        "elements_count": session.get("elements_count", 0),
        "reduction_pct": session.get("reduction_pct", 0.0)
    }
