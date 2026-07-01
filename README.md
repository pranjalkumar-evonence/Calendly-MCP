# Calendly MCP Server

A minimal MCP server that exposes your personal Calendly account to Claude
(or any MCP client) as a set of tools, using a Personal Access Token.

## Tools included

- `get_current_user` — your profile info
- `list_event_types` — your bookable event types (e.g. "30 Minute Meeting")
- `list_scheduled_events` — bookings on your calendar
- `get_scheduled_event` — full details of one booking
- `list_event_invitees` — who booked, and their answers to your questions
- `cancel_scheduled_event` — cancel a booking
- `get_event_type_available_times` — open slots for an event type
- `create_scheduling_link` — generate a single-use booking link to share

## 1. Get a Calendly Personal Access Token

1. Log into Calendly in your browser.
2. Go to **Account Settings → Integrations → API & Webhooks**.
3. Under **Personal Access Tokens**, click **Generate New Token**, name it
   (e.g. "MCP Server"), and copy the value — Calendly only shows it once.

## 2. Install dependencies

```bash
cd calendly-mcp
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure your token

```bash
cp .env.example .env
```

Open `.env` and paste your token in place of the placeholder:

```
CALENDLY_API_TOKEN=your_actual_token_here
```

## 4. Test it locally with the MCP Inspector

```bash
mcp dev server.py
```

This opens a local web UI where you can call each tool directly and see the
raw Calendly API responses — the fastest way to catch bugs before wiring it
into a client.

## 5. Connect it to Claude Desktop

Local (stdio) MCP servers like this one run through **Claude Desktop** or
**Claude Code**, not the claude.ai web/mobile app (which only connects to
remote/hosted MCP servers via its connector picker).

Open Claude Desktop's config file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add an entry (use the **absolute path** to your venv's python and server.py):

```json
{
  "mcpServers": {
    "calendly": {
      "command": "/absolute/path/to/calendly-mcp/venv/bin/python",
      "args": ["/absolute/path/to/calendly-mcp/server.py"],
      "env": {
        "CALENDLY_API_TOKEN": "your_actual_token_here"
      }
    }
  }
}
```

Restart Claude Desktop. You should see "calendly" listed under available
tools (hammer icon), and you can ask things like "What meetings do I have
this week?" or "Cancel my 3pm tomorrow."

## 6. Where to go from here

- Add a `reschedule_event` tool (Calendly doesn't have a direct reschedule
  endpoint — typically you cancel + share a new scheduling link).
- Add organization-level tools if you're on a Teams/Enterprise plan
  (`/organizations/{uuid}/memberships`, `/organizations/{uuid}/invitations`).
- Add webhook support (`/webhook_subscriptions`) if you want push
  notifications instead of polling.
- Wrap errors from `resp.raise_for_status()` into friendlier messages — right
  now a bad UUID or expired token will surface as a raw HTTP error.