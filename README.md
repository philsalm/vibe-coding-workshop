# Vibe Coding Workshop

A hands-on workshop for healthcare provider teams. Participants vibe-code a **Care Gap Outreach** Databricks App using either the Visual Builder App or **their own coding agent launched with [`ucode`](https://github.com/databricks/ucode)** — Databricks' coding-agent CLI that routes any supported agent (Codex, Claude Code, Gemini CLI, OpenCode, Copilot CLI, Pi) through **Unity AI Gateway**. The agent path is **agent-agnostic**: OAuth with the workspace, no API keys, and usage tracked centrally in the gateway dashboard. App scaffolding still uses [ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit).

## Repo layout

| Path | Purpose |
|------|---------|
| `PARTICIPANT_GUIDE.md` | The hands-on guide participants follow during the workshop. Three paths (Builder App / own agent via `ucode` / choose your own), Module 1 + Module 2 prompts, a usage/governance wrap-up, troubleshooting, take-it-further extensions. Mirrored from the shared Google Doc. |
| `setup_workshop.py` | Databricks notebook the workshop admin runs once before the workshop. Generates synthetic data, opens read access to participants, grants permissions. |
| `VBuilder_patch.md` | Laptop-side instructions for patching and deploying the shared Visual Builder App before the workshop. Tools list + Terraform workaround + patch + deploy steps. |
| `patches/fix-async-mcp-tool-execution.patch` | The actual patch file referenced by `VBuilder_patch.md`. Tracking PR: [ai-dev-kit#526](https://github.com/databricks-solutions/ai-dev-kit/pull/526). Drop once merged. |
| `skills/workshop-app-recipe/SKILL.md` | The app recipe carrying the plumbing patterns (OBO, scopes, resource binding, deployment). Loads as a Claude skill in the Builder App and `ucode claude`; for other agents, participants attach this file as context. Copied into `ai-dev-kit/databricks-skills/workshop-app-recipe/` before deploying the Builder App. |

## Prerequisite — Unity AI Gateway (for the `ucode` path)

The Path B (`ucode`) experience requires **Unity AI Gateway**, which is in **Beta**. Before the workshop, an **account admin** must:

1. Enable the **Unity AI Gateway** preview from the account console **Previews** page.
2. Confirm the workshop workspace is **Unity Catalog–enabled** and in a [supported region](https://learn.microsoft.com/en-us/azure/databricks/resources/feature-region-support#model-serving-features-availability).
3. Confirm participants (the `participants_group`) have access to the gateway endpoint(s) the agents will use.
4. (Optional) Create the OpenTelemetry UC tables so agent telemetry lands in Unity Catalog for the dashboard.

If the gateway isn't enabled, `ucode` agents will fail to authenticate — verify this ahead of time. (All of Phil's accounts are Azure; the links above are Azure-specific.)

## Admin setup

1. Import `setup_workshop.py` into your Databricks workspace.
2. Set the widgets at the top: `catalog`, `schema`, `num_patients`, `sql_warehouse_name`, `participants_group`.
3. **Confirm the Unity AI Gateway prerequisite above** (account admin) so the `ucode` path works.
4. Follow Section 0 to install the local prerequisites (Databricks CLI, Node, uv, terraform) and apply the Builder App patch.
5. Run Section 1 to create the synthetic data and grant access.
6. Follow Section 2 to deploy the Builder App and bind a warehouse to it.
7. Run Section 3 to grant the Builder App's service principal access to your data.
8. Run Section 4 to smoke-test the Builder App end-to-end.

## Participant flow

Participants pick one of three paths on workshop day:

- **Path A — Visual Builder App.** Open the URL the admin shared, paste the prompts from the workshop content doc.
- **Path B — Their own agent via `ucode`.** Install `ucode` (`uv tool install git+https://github.com/databricks/ucode`), scaffold with ai-dev-kit (`apx init`), then `ucode <agent>` (Claude / Codex / Gemini / OpenCode / Copilot / Pi) — governed through Unity AI Gateway, no API keys. Follow the prompts (identical to Path A).
- **Path C — Choose your own.** Take the synthetic data and personal write schema and vibe-code something else.
