"""
VLONE Headless Semantic Browser Driver:
Playwright Chromium async runtime with aggressive bloat stripping (CSS/Images/SVGs),
dynamic data-vlone-id element numbering for selector-less execution,
session state cookie persistence in ./vlone_sessions/, and background API sniffing.
Includes in-process BeautifulSoup fallback for environments without Playwright browser binaries.
"""

import asyncio
import ipaddress
import json
import logging
import os
import re
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Comment
import httpcore
from httpcore._backends.auto import AutoBackend
import httpx

from app.config import settings

logger = logging.getLogger("vlone.driver")

STRIP_TAGS = {
    "script", "style", "svg", "noscript", "iframe", "canvas",
    "video", "audio", "track", "source", "map", "object", "embed",
    "applet", "frame", "frameset", "head", "meta", "link"
}

INTERACTIVE_TAGS = {"a", "button", "input", "select", "textarea"}


class PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Network backend that connects directly to the pre-validated IP address."""

    def __init__(self, pinned_map: Dict[str, str]):
        self.pinned_map = pinned_map
        self.backend = AutoBackend()

    async def connect_tcp(self, host: str, port: int, **kwargs):
        target = self.pinned_map.get(host, host)
        return await self.backend.connect_tcp(target, port, **kwargs)

    async def connect_unix_socket(self, *args, **kwargs):
        return await self.backend.connect_unix_socket(*args, **kwargs)

    async def sleep(self, seconds: float):
        return await self.backend.sleep(seconds)


class PinnedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """Async transport pinning TCP connections to verified safe IP addresses."""

    def __init__(self, pinned_map: Dict[str, str], **kwargs):
        super().__init__(**kwargs)
        self.pinned_map = pinned_map
        self._pool = httpcore.AsyncConnectionPool(network_backend=PinnedNetworkBackend(pinned_map))


def validate_url(url: str) -> str:
    """
    Hardens URL against SSRF, internal network scanning, and unsafe schemes.
    Resolves hostname and verifies that all addresses are public and non-privileged.
    Returns the resolved public IP string.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials (username:password) are prohibited.")
    if not parsed.hostname:
        raise ValueError("URL must include a valid hostname.")

    hostname = parsed.hostname.lower()
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}
    if hostname in blocked_hosts or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise ValueError(f"Access to private/local address '{hostname}' is prohibited.")

    parsed_ip = None
    try:
        parsed_ip = ipaddress.ip_address(hostname)
    except ValueError:
        pass

    if parsed_ip is not None:
        if parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_link_local or parsed_ip.is_reserved or parsed_ip.is_multicast:
            raise ValueError(f"Access to private IP '{hostname}' is prohibited.")
        return str(parsed_ip)

    try:
        addr_info = socket.getaddrinfo(hostname, None)
        if not addr_info:
            raise ValueError(f"Unable to resolve address for host '{hostname}'.")
        validated_ip = None
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise ValueError(f"Resolved address '{ip_str}' is private and prohibited.")
            if not validated_ip:
                validated_ip = ip_str
        if not validated_ip:
            raise ValueError(f"No valid public address resolved for '{hostname}'.")
        return validated_ip
    except socket.gaierror as err:
        raise ValueError(f"DNS resolution failed for '{hostname}': {err}")


class VloneDriver:
    """
    Headless semantic browser automation engine.
    Extracts clean token-reduced markdown and numbered actionable elements.
    """

    def __init__(self, sessions_dir: Optional[Path] = None, transport_factory: Optional[Any] = None):
        self.sessions_dir = Path(sessions_dir or settings.sessions_path)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._sniffed_apis: Dict[str, List[Dict[str, Any]]] = {}
        self._live_pages: Dict[str, Dict[str, Any]] = {}
        self._playwright: Any = None
        self._transport_factory = transport_factory
        self.engine_status: str = "nominal"

    def _get_session_cookie_path(self, session_id: str) -> Path:
        if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", session_id):
            raise ValueError(f"Invalid session_id '{session_id}'. Must contain only alphanumeric, dash, or underscore characters.")
        return self.sessions_dir / f"{session_id}_cookies.json"

    def save_session_cookies(self, session_id: str, cookies: List[Dict[str, Any]]) -> None:
        p = self._get_session_cookie_path(session_id)
        p.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
        try:
            os.chmod(p, 0o600)
        except (OSError, NotImplementedError):
            pass

    def load_session_cookies(self, session_id: str) -> List[Dict[str, Any]]:
        p = self._get_session_cookie_path(session_id)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    async def open_page(self, url: str, session_id: str = "default", use_playwright: bool = True) -> Dict[str, Any]:
        """
        Navigates to URL, strips visual bloat, stamps data-vlone-id on interactive nodes,
        and produces semantic token-reduced markdown.
        """
        dns_cache: Dict[str, str] = {}

        async def validate_url_async(u: str) -> str:
            parsed = urlparse(u)
            host = (parsed.hostname or "").lower()
            if host in dns_cache:
                return dns_cache[host]
            ip = await asyncio.to_thread(validate_url, u)
            dns_cache[host] = ip
            return ip

        # Validate caller-controlled target URL asynchronously and resolve verified safe IP
        validated_ip = await validate_url_async(url)
        parsed_target = urlparse(url)
        target_hostname = parsed_target.hostname or ""

        logger.info(f"🌐 [Vlone] Navigating to {url} [pinned: {validated_ip}] (session: {session_id})")

        raw_html = ""
        playwright_success = False

        browser = None
        context = None
        page = None

        # 1. Attempt Playwright Chromium navigation if requested and available
        if use_playwright:
            try:
                from playwright.async_api import async_playwright
                if self._playwright is None:
                    self._playwright = await async_playwright().start()

                # Clean up previous session resources if present
                old_live = self._live_pages.pop(session_id, None)
                if old_live:
                    try:
                        await old_live["page"].close()
                        await old_live["context"].close()
                        await old_live["browser"].close()
                    except Exception:
                        pass

                # Pin DNS resolution for target host to the validated IP via Chromium network flags
                playwright_args = [f"--host-resolver-rules=MAP {target_hostname} {validated_ip}"]
                browser = await self._playwright.chromium.launch(headless=True, args=playwright_args)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) VLONE-Headless/3.0"
                )

                saved_cookies = self.load_session_cookies(session_id)
                if saved_cookies:
                    await context.add_cookies(saved_cookies)

                page = await context.new_page()

                # Sniff background APIs
                captured_requests: List[Dict[str, Any]] = []

                def on_request(req):
                    if req.resource_type in ["fetch", "xhr"]:
                        captured_requests.append({
                            "method": req.method,
                            "url": req.url,
                            "headers": req.headers
                        })

                page.on("request", on_request)

                # Harden all outgoing routes against SSRF asynchronously and filter heavy media bloat
                async def handle_route(route):
                    req_url = route.request.url
                    try:
                        await validate_url_async(req_url)
                    except Exception:
                        await route.abort()
                        return
                    if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                        await route.abort()
                    else:
                        await route.continue_()

                await page.route("**/*", handle_route)

                # Navigate to validated URL
                await page.goto(url, timeout=12000, wait_until="domcontentloaded")

                # Apply data-vlone-id attributes to the live DOM
                await page.evaluate("""() => {
                    let id = 0;
                    const actionable = document.querySelectorAll('a, button, input, select, textarea, [role="button"], [role="link"]');
                    actionable.forEach(el => {
                        id++;
                        el.setAttribute('data-vlone-id', String(id));
                    });
                }""")

                raw_html = await page.content()

                # Persist updated cookies
                cookies = await context.cookies()
                self.save_session_cookies(session_id, cookies)

                self._live_pages[session_id] = {
                    "browser": browser,
                    "context": context,
                    "page": page
                }
                playwright_success = True
                self.engine_status = "nominal"
                self._sniffed_apis[session_id] = captured_requests
            except Exception as e:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass
                logger.info(f"[Vlone] Playwright unavailable or failed ({e}). Executing fast HTTP/BeautifulSoup perception engine.")

        # 2. Fallback to direct HTTP fetch if Playwright did not run
        if not raw_html:
            try:
                curr_url = url
                # Validate URL before initial request and revalidate each redirect hop
                for _ in range(5):
                    curr_ip = await validate_url_async(curr_url)
                    curr_host = urlparse(curr_url).hostname or ""

                    pinned_transport = (
                        self._transport_factory({curr_host: curr_ip})
                        if self._transport_factory
                        else PinnedAsyncHTTPTransport({curr_host: curr_ip})
                    )
                    async with httpx.AsyncClient(
                        transport=pinned_transport,
                        timeout=10.0,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VLONE-Semantic/3.0"}
                    ) as client:
                        resp = await client.get(curr_url, follow_redirects=False)

                    if resp.is_redirect and "location" in resp.headers:
                        from urllib.parse import urljoin
                        curr_url = urljoin(curr_url, resp.headers["location"])
                    else:
                        raw_html = resp.text
                        break
                else:
                    raise ValueError(f"Exceeded maximum redirect limit (5) for '{url}'.")
            except Exception as ex:
                if isinstance(ex, ValueError) and "redirect limit" in str(ex):
                    raise
                logger.warning(f"[Vlone] Network fetch error on {url}: {ex}. Using synthetic fallback.")
                raw_html = f"<html><head><title>Offline: {url}</title></head><body><h1>Target: {url}</h1><p>Offline perception active.</p></body></html>"

            # Fallback path: real interception not available via static fetch
            self._sniffed_apis[session_id] = []
            self.engine_status = "degraded"

        # 3. Clean DOM and catalog interactive elements
        parsed = self._clean_and_catalog_dom(raw_html, url)

        session_state = {
            "session_id": session_id,
            "url": url,
            "title": parsed["title"],
            "markdown": parsed["markdown"],
            "elements": parsed["elements"],
            "elements_count": len(parsed["elements"]),
            "token_estimate": parsed["token_estimate"],
            "raw_tokens_estimate": parsed["raw_tokens_estimate"],
            "reduction_pct": parsed["reduction_pct"],
            "engine": "playwright" if playwright_success else "in-process-soup"
        }
        self._active_sessions[session_id] = session_state
        return session_state

    def _clean_and_catalog_dom(self, raw_html: str, url: str) -> Dict[str, Any]:
        """BeautifulSoup DOM token reducer and numbered element cataloger."""
        soup = BeautifulSoup(raw_html, "html.parser")
        page_title = soup.title.get_text().strip() if soup.title else f"VLONE Semantic: {url}"

        # Strip comment nodes
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Decompose non-content bloat tags
        for tag in soup.find_all(STRIP_TAGS):
            tag.decompose()

        catalog: List[Dict[str, Any]] = []
        actionable = soup.find_all(lambda el: el.name in INTERACTIVE_TAGS or el.get("role") in {"button", "link"})

        # Preserve valid existing data-vlone-id values and advance counter past maximum reused ID
        max_existing_id = 0
        for el in actionable:
            existing_id = el.get("data-vlone-id")
            if existing_id and existing_id.isdigit():
                max_existing_id = max(max_existing_id, int(existing_id))

        counter = max_existing_id
        for el in actionable:
            existing_id = el.get("data-vlone-id")
            if existing_id and existing_id.isdigit():
                vid = int(existing_id)
            else:
                counter += 1
                vid = counter
                el["data-vlone-id"] = str(vid)

            tag_name = el.name.lower()
            text = el.get_text(separator=" ", strip=True)
            name = el.get("name", "")
            placeholder = el.get("placeholder", "")
            elem_type = el.get("type", "")
            href = el.get("href", "")
            val = el.get("value", "")
            role = el.get("role", "link" if tag_name == "a" else ("button" if tag_name == "button" else tag_name))

            catalog.append({
                "vlone_id": vid,
                "tag": tag_name,
                "element_type": elem_type,
                "text": text,
                "name": name,
                "placeholder": placeholder,
                "href": href,
                "value": val,
                "role": role
            })

        markdown_lines = [f"# {page_title}\n", f"**Source URL**: {url}\n\n## Actionable Elements Catalog\n"]
        for item in catalog:
            label = item["text"] or item["placeholder"] or item["name"] or item["tag"]
            markdown_lines.append(f"- `[#{item['vlone_id']}: {item['tag'].upper()} \"{label}\"]` (type={item['element_type']}, name=\"{item['name']}\")")

        markdown_lines.append("\n## Page Content\n")

        for content_tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            txt = content_tag.get_text(strip=True)
            if not txt:
                continue
            if content_tag.name.startswith("h"):
                level = int(content_tag.name[1])
                markdown_lines.append(f"\n{'#' * level} {txt}\n")
            elif content_tag.name == "li":
                markdown_lines.append(f"- {txt}")
            else:
                markdown_lines.append(f"{txt}\n")

        clean_md = "\n".join(markdown_lines).strip()
        raw_tokens = max(1, len(raw_html) // 4)
        opt_tokens = max(1, len(clean_md) // 4)
        reduction = round(max(0.0, 1.0 - (opt_tokens / raw_tokens)) * 100, 2)

        return {
            "title": page_title,
            "elements": catalog,
            "markdown": clean_md,
            "raw_tokens_estimate": raw_tokens,
            "token_estimate": opt_tokens,
            "reduction_pct": reduction
        }

    async def interact(
        self,
        action: str,
        vlone_id: int,
        value: str = "",
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Executes click or fill action on element identified by vlone_id."""
        session = self._active_sessions.get(session_id, {})

        # Return explicit unsupported status when running on fallback engine
        if session.get("engine") != "playwright" or session_id not in self._live_pages:
            return {
                "status": "unsupported",
                "error": "Interactive execution requires Playwright browser engine. Fallback engine is read-only.",
                "action": action,
                "vlone_id": int(vlone_id),
                "session_id": session_id
            }

        action_lower = action.lower()
        if action_lower not in ["click", "fill", "type", "hover", "select"]:
            return {
                "status": "error",
                "error": f"Unsupported action '{action}'. Allowed: click, fill, type, hover, select",
                "action": action,
                "vlone_id": int(vlone_id)
            }

        elements = session.get("elements", [])
        matched = next((e for e in elements if e.get("vlone_id") == int(vlone_id)), None)

        if not matched:
            return {
                "status": "not_found",
                "error": f"Element with data-vlone-id='{vlone_id}' not found in active session catalog.",
                "action": action,
                "vlone_id": int(vlone_id)
            }

        live_entry = self._live_pages[session_id]
        live_page = live_entry["page"]
        try:
            locator = live_page.locator(f'[data-vlone-id="{vlone_id}"]')
            if action_lower == "click":
                await locator.click(timeout=5000)
            elif action_lower in ["fill", "type"]:
                await locator.fill(value, timeout=5000)
            elif action_lower == "hover":
                await locator.hover(timeout=5000)
            elif action_lower == "select":
                await locator.select_option(value, timeout=5000)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Playwright action failed: {e}",
                "action": action,
                "vlone_id": int(vlone_id)
            }

        if action_lower in ["fill", "type"]:
            matched["value"] = value

        # Re-run live-page ID stamping so newly created elements receive sequential IDs
        try:
            await live_page.evaluate("""() => {
                let maxId = 0;
                const stamped = document.querySelectorAll('[data-vlone-id]');
                stamped.forEach(el => {
                    const n = parseInt(el.getAttribute('data-vlone-id') || '0', 10);
                    if (!isNaN(n) && n > maxId) maxId = n;
                });
                const actionable = document.querySelectorAll('a, button, input, select, textarea, [role="button"], [role="link"]');
                actionable.forEach(el => {
                    const cur = el.getAttribute('data-vlone-id');
                    if (!cur || isNaN(parseInt(cur, 10))) {
                        maxId++;
                        el.setAttribute('data-vlone-id', String(maxId));
                    }
                });
            }""")
            raw_html = await live_page.content()
            parsed = self._clean_and_catalog_dom(raw_html, session.get("url", ""))
            session["markdown"] = parsed["markdown"]
            session["elements"] = parsed["elements"]
            session["elements_count"] = len(parsed["elements"])
        except Exception:
            pass

        result_msg = f"Executed '{action}' on element #{vlone_id} ({matched.get('tag')}: '{matched.get('text') or matched.get('name')}') with value='{value}'"

        return {
            "status": "success",
            "action": action,
            "vlone_id": int(vlone_id),
            "value": value,
            "url": session.get("url", "about:blank"),
            "result": result_msg,
            "markdown": session.get("markdown", "")
        }

    async def get_sniffed_apis(self, session_id: str = "default") -> List[Dict[str, Any]]:
        """Returns captured network APIs for the session."""
        return self._sniffed_apis.get(session_id, [])

    async def close(self):
        """Closes active Playwright instances and live browser resources."""
        for sess_id, live in list(self._live_pages.items()):
            try:
                await live["page"].close()
                await live["context"].close()
                await live["browser"].close()
            except Exception:
                pass
        self._live_pages.clear()

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

