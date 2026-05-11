# Vibe Coding Workshop

A 90-minute hands-on workshop for healthcare provider teams. Participants vibe-code a **Care Gap Outreach** Databricks App using either the Visual Builder App or their own coding agent (Claude Code / Cursor) wired up with [ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit).

## Repo layout

| Path | Purpose |
|------|---------|
| `setup_workshop.py` | Databricks notebook the workshop admin runs once before the workshop. Generates synthetic data, opens read access to participants, deploys the shared Builder App, grants permissions. |
| `patches/fix-async-mcp-tool-execution.patch` | Pre-deploy patch for `databricks-solutions/ai-dev-kit` that fixes an async MCP-tool execution bug. Tracking PR: [ai-dev-kit#526](https://github.com/databricks-solutions/ai-dev-kit/pull/526). Drop once merged. |

## Admin setup

1. Import `setup_workshop.py` into your Databricks workspace.
2. Set the widgets at the top: `catalog`, `schema`, `num_patients`, `sql_warehouse_name`, `participants_group`.
3. Follow Section 0 to install the local prerequisites (Databricks CLI, Node, uv, terraform) and apply the Builder App patch.
4. Run Section 1 to create the synthetic data and grant access.
5. Follow Section 2 to deploy the Builder App and bind a warehouse to it.
6. Run Section 3 to grant the Builder App's service principal access to your data.
7. Run Section 4 to smoke-test the Builder App end-to-end.

## Participant flow

Participants pick one of three paths on workshop day:

- **Path A — Visual Builder App.** Open the URL the admin shared, paste the prompts from the workshop content doc.
- **Path B — Their own agent.** Install Claude Code (or another agent) + ai-dev-kit on their laptop, follow the prompts.
- **Path C — Choose your own.** Take the synthetic data and personal write schema and vibe-code something else.
