# Fusion MCP connection prompts

These prompts connect Cursor and Antigravity to the existing Fusion MCP server used by Claude and Codex on this Mac. Keep Fusion running on the same Mac while connecting either app.

**Endpoint:** `http://127.0.0.1:27182/mcp` (Streamable HTTP).

**Checked on 2026-10-07:** Codex registered the existing server and successfully called `fusion_mcp_read` with `{"queryType":"document","operation":"open"}`. Fusion reported zero open documents. The Cursor and Antigravity prompts below have not been executed or verified in those apps.

## Prompt for Cursor

[Cursor configuration docs](https://prod.cursor.com/help/customization/mcp).

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

[Antigravity configuration docs](https://www.antigravity.google/docs/mcp).

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


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../16-fusion-mcp.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
