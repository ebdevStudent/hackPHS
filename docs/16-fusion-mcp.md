# Fusion MCP — shared local connection

Updated 2026-10-07. Fusion MCP uses the existing server already connected to Claude and Codex on this Mac. Keep Fusion running while connecting clients.

## Connection and recorded check

- Endpoint: `http://127.0.0.1:27182/mcp`.
- Transport: Streamable HTTP; the checked existing server required no authentication.
- Codex configuration: the global `fusion` entry in `/Users/devk/.codex/config.toml`.
- Recorded on 2026-10-07: MCP handshake succeeded, four tools were exposed, and Codex called `fusion_mcp_read` with `{"queryType":"document","operation":"open"}` successfully. Fusion reported zero open documents at that moment.
- Cursor and Antigravity prompts below have not been executed or verified in those apps.

Port 27182 is Fusion MCP. The monitoring backend (8080) and illustrative game (8765) are separate services. Successful MCP access is not measured CAD clearance or permission to treat a reference drawing as a manufacturing model; follow the [CAD plan](03-cad.md).

## Prompt for Cursor

[Cursor MCP configuration docs](https://cursor.com/docs/mcp).

```text
Connect Cursor to the existing Fusion MCP server already used by Claude and Codex.

Back up ~/.cursor/mcp.json, then merge this entry into its mcpServers object, preserving existing servers:

"fusion": {
  "url": "http://127.0.0.1:27182/mcp"
}

This is a running Streamable HTTP server inside Fusion; it requires no authentication or installation.

Refresh the MCP connection. Verify that Fusion tools are available, then call fusion_mcp_read with {"queryType":"document","operation":"open"} to test the connection without changing a design.

If a reload or restart is needed, tell me the exact step. Report configuration saved and connection verified separately.
```

## Prompt for Antigravity

[Antigravity MCP configuration docs](https://antigravity.google/docs/mcp?tab=ide).

```text
Connect Antigravity to the existing Fusion MCP server already used by Claude and Codex.

Identify the MCP configuration used by this installed version. Both ~/.gemini/config/mcp_config.json and ~/.gemini/antigravity/mcp_config.json exist on this Mac; use the active configuration, checking “View raw config” if needed.

Back up that file, then merge this entry into its mcpServers object, preserving existing servers:

"fusion": {
  "serverUrl": "http://127.0.0.1:27182/mcp"
}

This is a running Streamable HTTP server inside Fusion; it requires no authentication or installation.

Refresh the MCP connection. Verify that Fusion tools are available, then call fusion_mcp_read with {"queryType":"document","operation":"open"} to test the connection without changing a design.

If a reload or restart is needed, tell me the exact step. Report configuration saved and connection verified separately.
```

## Verification after setup

Use the actual client's MCP tool list, then the read-only open-document query in the prompt. A saved configuration is distinct from a live connection. If the server cannot be reached, check that Fusion is running on this Mac and that its existing MCP server still uses the recorded endpoint.

[Documentation index](README.md) · [CAD](03-cad.md) · [Historical setup record](decisions.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- https://cursor.com/docs/mcp — Cursor MCP configuration and `url` for remote HTTP/SSE servers.
- [Google Antigravity MCP setup](https://antigravity.google/docs/mcp?tab=ide) — Current settings UI, config locations and remote `serverUrl` field.
- [Fusion MCP protocol](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) — Transport background; actual endpoint and handshake are documented from local verification above.
