"""
Calendly MCP Server
--------------------
Exposes your Calendly account (event types, scheduled events, invitees,
cancellations, scheduling links) as MCP tools, using a Personal Access
Token for auth.

Setup:
    1. Get a Personal Access Token from Calendly:
       Account Settings -> Integrations -> API & Webhooks -> Personal Access Tokens
    2. Put it in a .env file (see .env.example) as CALENDLY_API_TOKEN=...
    3. Run with: python server.py   (for direct stdio testing)
       or:       mcp dev server.py (to use the MCP Inspector UI)
"""

import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()


BASE_URL = "https://api.calendly.com"

CALENDLY_TOKEN = os.environ.get("CALENDLY_API_TOKEN")
if not CALENDLY_TOKEN:
    raise RuntimeError(
        """CALENDLY_API_TOKEN is not set. Add it to a .env file or export it 
        in your shell before running this server."""
    )

mcp = FastMCP("calendly")

_user_uri_cache: Optional[str] = None


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {CALENDLY_TOKEN}",
        "Content-Type": "application/json",
    }


async def _get_user_uri(client: httpx.AsyncClient) -> str:
    """Resource URI of the authenticated user, cached after first lookup."""
    global _user_uri_cache
    if _user_uri_cache:
        return _user_uri_cache
    resp = await client.get(f"{BASE_URL}/users/me", headers=_headers())
    resp.raise_for_status()
    _user_uri_cache = resp.json()["resource"]["uri"]
    return _user_uri_cache


@mcp.tool()
async def get_current_user() -> dict:
    """Get the authenticated Calendly user's profile: name, email, timezone,
    and scheduling URL."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/users/me", headers=_headers())
        resp.raise_for_status()
        return resp.json()["resource"]


@mcp.tool()
async def list_event_types(active_only: bool = True) -> list:
    """List the user's Calendly event types (e.g. '30 Minute Meeting',
    'Intro Call'), including their URI, name, duration, and public
    scheduling link. Use the URI with create_scheduling_link or
    get_event_type_available_times."""
    async with httpx.AsyncClient() as client:
        user_uri = await _get_user_uri(client)
        params = {"user": user_uri, "count": 100}
        if active_only:
            params["active"] = "true"
        resp = await client.get(
            f"{BASE_URL}/event_types", headers=_headers(), params=params
        )
        resp.raise_for_status()
        return resp.json()["collection"]


@mcp.tool()
async def list_scheduled_events(
    status: str = "active",
    count: int = 20,
    min_start_time: Optional[str] = None,
    max_start_time: Optional[str] = None,
) -> list:
    """List the user's scheduled Calendly events (bookings on their
    calendar). status is 'active' or 'canceled'. min_start_time /
    max_start_time are optional ISO 8601 timestamps (e.g.
    '2026-06-18T00:00:00Z') to filter the date range."""
    async with httpx.AsyncClient() as client:
        user_uri = await _get_user_uri(client)
        params = {"user": user_uri, "status": status, "count": count}
        if min_start_time:
            params["min_start_time"] = min_start_time
        if max_start_time:
            params["max_start_time"] = max_start_time
        resp = await client.get(
            f"{BASE_URL}/scheduled_events", headers=_headers(), params=params
        )
        resp.raise_for_status()
        return resp.json()["collection"]


@mcp.tool()
async def get_scheduled_event(event_uuid: str) -> dict:
    """Get full details for one scheduled event by its UUID (the last
    segment of the event's 'uri' field from list_scheduled_events)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/scheduled_events/{event_uuid}", headers=_headers()
        )
        resp.raise_for_status()
        return resp.json()["resource"]


@mcp.tool()
async def list_event_invitees(event_uuid: str) -> list:
    """List the invitees for a scheduled event UUID, including their name,
    email, and any answers to custom booking questions."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/scheduled_events/{event_uuid}/invitees",
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()["collection"]


@mcp.tool()
async def cancel_scheduled_event(event_uuid: str, reason: str = "") -> dict:
    """Cancel a scheduled Calendly event by UUID. The optional reason is
    included in the cancellation email sent to invitees."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/scheduled_events/{event_uuid}/cancellation",
            headers=_headers(),
            json={"reason": reason},
        )
        resp.raise_for_status()
        return resp.json()["resource"]


@mcp.tool()
async def get_event_type_available_times(
    event_type_uri: str, start_time: str, end_time: str
) -> list:
    """Get open booking slots for an event type between start_time and
    end_time (ISO 8601 timestamps, max 7-day range). event_type_uri comes
    from list_event_types."""
    async with httpx.AsyncClient() as client:
        params = {
            "event_type": event_type_uri,
            "start_time": start_time,
            "end_time": end_time,
        }
        resp = await client.get(
            f"{BASE_URL}/event_type_available_times",
            headers=_headers(),
            params=params,
        )
        resp.raise_for_status()
        return resp.json()["collection"]


@mcp.tool()
async def create_scheduling_link(event_type_uri: str, max_event_count: int = 1) -> dict:
    """Create a single-use Calendly scheduling link for an event type, so
    you can share it with someone to book a slot. event_type_uri comes
    from list_event_types."""
    async with httpx.AsyncClient() as client:
        body = {
            "max_event_count": max_event_count,
            "owner": event_type_uri,
            "owner_type": "EventType",
        }
        resp = await client.post(
            f"{BASE_URL}/scheduling_links", headers=_headers(), json=body
        )
        resp.raise_for_status()
        return resp.json()["resource"]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)