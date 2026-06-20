# Garmin health connector for Claude (MCP)

A local [MCP](https://modelcontextprotocol.io) server that lets **Claude** read your
Garmin data. It wraps the Laravel backend's read API (`/api/garmin/*`) as tools:
`summary`, `daily`, `sleep`, `activities`, `body`.

It's a **local stdio server** — not hosted. The Claude app launches it on demand; it
calls your backend over HTTPS with a read-only token and returns JSON. Read-only; your
token stays on your machine.

## Prerequisites
- `uv` + this backend installed (`uv sync` in `backend/`).
- A **read token**: on the server run `php artisan garmin:token --read` and copy it.

## Add to Claude Code
```bash
claude mcp add garmin-health --scope user \
  --env GARMIN_API_URL=https://backend.gleearl.com \
  --env GARMIN_READ_TOKEN=PASTE_READ_TOKEN \
  -- uv run --directory /ABSOLUTE/PATH/TO/garmin/backend python -m garmin_dash.mcp_server
```
Then ask, e.g.: *"Using garmin-health, how did I sleep last week?"*

## Add to Claude Desktop
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "garmin-health": {
      "command": "uv",
      "args": ["run", "--directory", "/ABSOLUTE/PATH/TO/garmin/backend",
               "python", "-m", "garmin_dash.mcp_server"],
      "env": {
        "GARMIN_API_URL": "https://backend.gleearl.com",
        "GARMIN_READ_TOKEN": "PASTE_READ_TOKEN"
      }
    }
  }
}
```
Restart Claude Desktop; the tools appear under the connector.

## Test it without Claude (MCP Inspector)
```bash
GARMIN_API_URL=https://backend.gleearl.com GARMIN_READ_TOKEN=… \
  npx @modelcontextprotocol/inspector uv run --directory $(pwd) python -m garmin_dash.mcp_server
```

## Notes
- Tools accept optional `from_date` / `to_date` (YYYY-MM-DD); omit for the last ~90 days.
- A missing/invalid token returns a clear "unauthorized (401)" message from each tool.
- This only works in Claude **on the machine where it's configured**. For access from
  claude.ai web / phone, the connector would need to run remotely on the backend (see
  the project plan's "Phase 2").
