# Vibe Coding Workshop

A hands-on workshop for healthcare provider teams. Participants vibe-code a **Care Gap Outreach** Databricks App using either the Visual Builder App or their own coding agent (Claude Code / Cursor) wired up with [ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit).

The app is built on the **same governed synthetic dataset** as the companion [Metric Views workshop](https://github.com/philsalm/mvp-metric-views-workshop) (`mvp_quality_workshop`) — one source of truth feeding both a metric view (analytics) and this operational app. That workshop's `00_setup_quality_data` notebook generates the data; this workshop layers an app on top.

## Repo layout

| Path | Purpose |
|------|---------|
| `PARTICIPANT_GUIDE.md` | The hands-on guide participants follow during the workshop. Three paths (Builder App / own agent / choose your own), Module 1 + Module 2 prompts, troubleshooting, take-it-further extensions. Mirrored from the shared Google Doc. |
| `setup_workshop.py` | Databricks notebook the workshop admin runs once before the workshop. Verifies the shared `mvp_quality_workshop` dataset, (re)creates the operational `patients` + `care_gaps` views, opens read access to participants, grants permissions, and guides the Builder App deploy. |
| `VBuilder_patch.md` | Laptop-side instructions for patching and deploying the shared Visual Builder App before the workshop. Tools list + Terraform workaround + patch + deploy steps. |
| `patches/fix-async-mcp-tool-execution.patch` | The actual patch file referenced by `VBuilder_patch.md`. Tracking PR: [ai-dev-kit#526](https://github.com/databricks-solutions/ai-dev-kit/pull/526). Drop once merged. |
| `skills/workshop-app-recipe/SKILL.md` | The Claude Code skill the Builder App loads to carry the plumbing patterns (OBO, scopes, resource binding, deployment). Copied into `ai-dev-kit/databricks-skills/workshop-app-recipe/` before deploying the Builder App. |

## Admin setup

1. **Generate the shared dataset first** (or confirm it's already loaded): run the [Metric Views workshop's](https://github.com/philsalm/mvp-metric-views-workshop) `00_setup_quality_data` notebook against your target catalog. It creates the `mvp_quality_workshop` star schema and the `patients` / `care_gaps` views.
2. Import `setup_workshop.py` into your Databricks workspace.
3. Set the widgets at the top: `catalog`, `schema` (default `mvp_quality_workshop`), `sql_warehouse_name`, `participants_group`.
4. Run Section 1 to verify the shared dataset, (re)create the operational views, and grant participant access.
5. Follow `VBuilder_patch.md` + Section 2 to deploy the Builder App and bind a warehouse to it.
6. Run Section 3 to grant the Builder App's service principal access to your data.
7. Run Section 4 to smoke-test the Builder App end-to-end.

## Participant flow

Participants pick one of three paths on workshop day:

- **Path A — Visual Builder App.** Open the URL the admin shared, paste the prompts from the workshop content doc.
- **Path B — Their own agent.** Install Claude Code (or another agent) + ai-dev-kit on their laptop, follow the prompts.
- **Path C — Choose your own.** Take the synthetic data and personal write schema and vibe-code something else.
