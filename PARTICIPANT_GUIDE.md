<!-- toc -->

# Healthcare Vibe Coding Workshop — Hands-On Content

A 50-minute hands-on session in which you build a **Care Gap Outreach** Databricks App. You can follow the scripted prompts below using either the shared Visual Builder App or **your own coding agent — launched through `ucode`** so it runs against **Unity AI Gateway** (no API keys, governed and observable) — or go off-script and build something of your own using the synthetic data we've prepared.

> **`ucode`** is Databricks' coding-agent launcher. One command (`ucode <agent>`) runs Codex, Claude Code, Gemini CLI, OpenCode, Copilot CLI, or Pi through your workspace's Unity AI Gateway: OAuth with your workspace credentials, **no API keys or tokens to manage**, and every request tracked in the gateway usage dashboard. Pick whichever agent you like — this workshop is agent-agnostic.

## What you'll build

**Care Gap Outreach** — an internal tool for a care coordination team to work through open HEDIS-style care gaps and log their outreach attempts. By the end of the workshop the app will:

- Render a filterable list of open care gaps with patient context, backed by shared synthetic Unity Catalog tables
- Use **on-behalf-of-user** authorization so each user's Unity Catalog permissions apply to their queries
- Persist outreach attempts and saved worklists in **Delta tables** in your personal workshop schema
- (Optional take-home) Ship via a Databricks Asset Bundle + GitHub Actions

## Three paths — pick one

| Path | Tool | Setup time | Good for |
|------|------|------------|----------|
| **A — Visual Builder App** | The shared app at the URL the admin sent | 0 min | First-timers, zero local setup, focus on prompting |
| **B — Your own agent via `ucode`** | `uv tool install … ucode` → `ucode <agent>` (Codex / Claude / Gemini / OpenCode / Copilot / Pi) on your laptop | ~5–10 min during workshop | Your own environment + agent of choice, governed through Unity AI Gateway, no API keys |
| **C — Choose your own** | Anything you want | varies | You already have a healthcare app idea — use the shared data and your personal schema and build it |

The prompts below are written so they work in both Path A and Path B with no changes, **regardless of which agent you pick in `ucode`**. Path C participants are welcome to take what they want.

## Schedule

| Time | Block |
|------|-------|
| 0:00–0:05 | Setup — choose your path; Path B installs `ucode` and launches an agent |
| 0:05–0:28 | **Module 1** — Build the care gap outreach app (~23 min) |
| 0:28–0:43 | **Module 2** — Add per-user write state with Delta tables (~15 min) |
| 0:43–0:48 | **Wrap-up** — `ucode usage` + the AI Gateway dashboard: what did your build cost? (~5 min) |
| 0:48–0:50 | Q&A |

# Setup (5 min)

## Step 1 — Confirm you can query the shared data

The workshop's synthetic data lives in a shared catalog (the workshop admin will tell you the exact catalog name in their logistics email — call it `<CATALOG>` below). Read access is open to all workshop participants. Module 2 will have your app create its own write schema later — nothing to set up by hand.

Open the SQL editor in your workspace and run:

```sql
SELECT measure, priority, COUNT(*) AS gap_count
FROM <CATALOG>.care_gaps_demo.care_gaps
GROUP BY measure, priority
ORDER BY measure, priority;
```

You should see a breakdown of care gaps by HEDIS-style measure (BCS, COL, CDC-A1C, DEE, FluVax, CBP) and priority (overdue, due_soon, preventive). If this errors with a permissions issue, raise your hand — the admin's setup may not have completed.

## Step 2 (Path A only) — Open the Builder App

Open the URL the admin shared in the workshop logistics email. You should see the Builder App's chat interface. Click **New project** and give it a name like `care-gap-outreach`. You're ready to paste prompts.

## Step 2 (Path B only) — Install `ucode` and launch your agent

You have ~5–10 minutes. `ucode` runs your coding agent through Unity AI Gateway, so there are **no API keys or tokens to set** — it authenticates with your workspace over OAuth on first launch.

```bash
# 1. Install ucode (needs Python 3.12+ and uv — https://docs.astral.sh/uv).
uv tool install git+https://github.com/databricks/ucode

# 2. Scaffold the app project (ai-dev-kit is agent-neutral and provides the app template):
mkdir care-gap-outreach && cd care-gap-outreach
pip install ai-dev-kit && apx init

# 3. (Optional) wire Databricks MCP servers — SQL warehouse, Unity Catalog functions —
#    into your agent so it can query/act against the workspace directly:
ucode configure mcp

# 4. Launch the agent of your choice. First launch prompts for your workspace URL and
#    runs OAuth, then writes that agent's config and drops you into it:
ucode claude      # or: ucode codex | ucode gemini | ucode opencode | ucode copilot | ucode pi
```

That's it — no `ANTHROPIC_BASE_URL`, no PAT. Every model call is routed through the gateway and shows up in `ucode usage` (we'll look at that in the wrap-up). `ucode status` shows what's configured; `ucode revert` restores your original agent config files afterward.

**The app recipe.** The prompts tell your agent to follow the `workshop-app-recipe` (the OBO / scopes / resource-binding / deployment plumbing). The Builder App and `ucode claude` load it as a Claude skill automatically. With any other agent, clone this workshop repo and **attach or paste `skills/workshop-app-recipe/SKILL.md` as context** when you start — then the same prompts work unchanged.

You're ready to paste prompts.

## Step 2 (Path C only) — Skim, then go

Take the data shape from Step 1 and the agent of your choice. Build whatever you want. The prompts below are inspiration if you need a starting point.

## What to expect when the app deploys

Your app will use **on-behalf-of-user (OBO) authorization** — each user's queries run as their identity, so Unity Catalog row/column filters apply per-user. The first time you open your deployed app URL, you may need to **sign out and back in** (or open the URL in an incognito window) so Databricks issues you a fresh access token with the OAuth scopes your app requires. Plan on a ~10-second re-auth detour the first time. Subsequent visits will not require this.

# Module 1 — Build the care gap outreach app (25 min)

**Goal.** A deployed Databricks App showing open care gaps as a filterable, paginated table with a patient detail drawer.

## Why use OBO for SQL queries

Databricks Apps give you two ways to authenticate to data: the app's service principal (shared identity for all users) or **on-behalf-of-user** (each query runs as the requesting user). For a care coordination tool you almost always want OBO so each clinician's Unity Catalog row/column filters apply, audit trails attribute correctly, and team-scoped policies (e.g., "you can only see your panel's patients") just work.

## The prompt

Replace `<CATALOG>` with the catalog name from the admin's logistics email, then paste this into the Builder App chat (Path A) or your `ucode` agent (Path B). It's the same prompt either way.

```
Build a Databricks App named `care-gap-outreach`: Python FastAPI backend +
React frontend, served as a single deployable Databricks App.

Follow the `workshop-app-recipe` exactly for the app's plumbing (authorization,
scopes, resource binding, deployment, response shape). It loads automatically as
a skill in the Builder App and `ucode claude`; for other agents, use the
`SKILL.md` you attached at setup.

The app helps a care coordination team work through open care gaps and contact
patients to close them.

DATA SOURCE
Two Unity Catalog tables, joined on MRN. Query them via a serverless SQL warehouse.

- `<CATALOG>.care_gaps_demo.care_gaps` — gap_id, mrn, measure,
  measure_description, due_date, last_completed_date, priority, source
- `<CATALOG>.care_gaps_demo.patients` — mrn, first_name, last_name,
  age, sex, primary_pcp, insurance_plan, preferred_contact, phone, email,
  last_visit_date

UI

1. A filterable, sortable, paginated table of open care gaps. Columns:
   - Priority badge color-coded (overdue=red, due_soon=yellow, preventive=gray)
   - Patient name (first + last)
   - Age, sex
   - Measure (show abbreviation; tooltip shows the full description)
   - Due date plus a relative label ("3 days overdue" / "due in 12 days")
   - Primary PCP
   - Insurance plan
   - Preferred contact channel (with an icon)

2. Filter controls above the table:
   - Measure (multi-select)
   - Priority (multi-select: overdue / due_soon / preventive)
   - Primary PCP (searchable dropdown)
   - Insurance plan (multi-select)

3. Click a row to open a side drawer showing the patient's demographics,
   ALL of their open gaps (not just the clicked one), contact info with the
   preferred channel highlighted, and a "Log Outreach" button (placeholder —
   we'll wire it up next module).

Deploy and give me the app URL when it's running.
```

## Checkpoint

When the agent says it's done, open the deployed URL and confirm:

- The table renders with rows
- All filters change the visible rows when you toggle them
- The priority badges are color-coded
- A row click opens the patient drawer with all their gaps

If something is broken, stay in chat and describe what you see — the agent can debug from there. Common things to mention: which API path errored (check the browser DevTools network tab), or whether the page hangs on load vs renders empty.

## Stretch tasks (Module 1)

Pick one if you finish early. Paste as a follow-up prompt.

**Add measure metadata.** "Add a small info icon next to each measure abbreviation that opens a popover with the full HEDIS description, the at-risk age/sex criteria, and a link to the measure's CMS page. The descriptions can come from a small lookup map you hardcode for now."

**Sort by last-attempted-outreach.** "Add a column 'Last contacted' that shows when this gap was last touched (`last_completed_date` for now — we'll switch it to the outreach log in the next module). Make it sortable so coordinators can prioritize patients who haven't been contacted recently."

# Module 2 — Add app state with Delta tables (15 min)

**Goal.** Care coordinators can log outreach attempts (team-visible) and save filter combinations as named worklists (per-user). Both persist across sessions.

## Why Delta (and not Lakebase)

Lakebase is the production-correct choice for high-write-rate transactional app state — low latency, native Postgres semantics, natively integrated as a Databricks App resource. **For this workshop we keep things simple by writing to Delta tables in a single schema the app creates for itself**, using the same OBO SQL warehouse connection from Module 1. Same auth, no new provisioning step.

| Pattern | Best fit |
|---------|----------|
| Workshop demo of app writes | Delta in an app-owned schema (this module) |
| Production transactional state with hundreds of concurrent writes/sec | Lakebase Postgres |
| Analytical queries on the care-gap dataset | Unity Catalog Delta (where the care-gap data already lives) |

If you want to swap in Lakebase later, the API surface stays the same — only the connection layer changes.

## The prompt

Replace `<CATALOG>` and every `<YOUR_USERNAME>` placeholder before pasting. `<YOUR_USERNAME>` is the part of your Databricks email before the `@`, with `.` replaced by `_` (e.g., `jane.doe@org.com` → `jane_doe`).

```
Now add app state to care-gap-outreach using Delta tables. Same OBO SQL
warehouse connection from Module 1 handles the reads AND the writes — no
new auth or provisioning.

Continue to follow the `workshop-app-recipe` (OBO connection helper,
response envelope, `?` parameter binding, never DATABRICKS_TOKEN).

CREATE A SCHEMA FOR THE APP'S STATE

During the build, run:

    CREATE SCHEMA IF NOT EXISTS <CATALOG>.workshop_<YOUR_USERNAME>

The workshop admin already granted CREATE SCHEMA on the catalog to
participants, so the OBO connection has permission.

TABLES

Create both in that schema with `CREATE TABLE IF NOT EXISTS`:

    <CATALOG>.workshop_<YOUR_USERNAME>.outreach_log
    - id              STRING    NOT NULL   -- UUID, generated in app code
    - user_email      STRING    NOT NULL
    - mrn             STRING    NOT NULL
    - gap_id          STRING    NOT NULL
    - attempted_at    TIMESTAMP NOT NULL
    - channel         STRING    NOT NULL
    - outcome         STRING    NOT NULL
    - notes           STRING

    <CATALOG>.workshop_<YOUR_USERNAME>.saved_worklists
    - id              STRING    NOT NULL   -- UUID, generated in app code
    - user_email      STRING    NOT NULL
    - name            STRING    NOT NULL
    - filters         STRING    NOT NULL   -- JSON-serialized filter state
    - created_at      TIMESTAMP NOT NULL

Delta doesn't enforce CHECK constraints — validate `channel` and `outcome`
in the FastAPI handler with Pydantic Literal types:

    Channel = Literal['phone','email','portal','letter']
    Outcome = Literal['reached','voicemail','no_answer','scheduled','declined','wrong_contact']

USER IDENTITY

Read the user's email from request headers — `x-forwarded-email` preferred,
fall back to `x-forwarded-user`. Stamp every row's `user_email` with the
caller's identity.

API ENDPOINTS

Reuse the OBO `get_sql_connection(request)` helper from Module 1.

    - GET    /api/outreach?mrn=...   outreach history for a patient (all users,
                                     ordered by attempted_at DESC) — team-visible
    - POST   /api/outreach           accept {mrn, gap_id, channel, outcome, notes},
                                     generate UUID, insert with user_email and now()
    - GET    /api/worklists          saved worklists for the current user only
                                     (WHERE user_email = ?), ordered by created_at DESC
    - POST   /api/worklists          accept {name, filters}, JSON-serialize filters,
                                     generate UUID, insert with user_email and now()
    - DELETE /api/worklists/{id}     delete only if the row's user_email matches
                                     the request user; 404 otherwise

UI

- "Log Outreach" button on the patient drawer opens a modal with channel +
  outcome dropdowns and a notes textarea. On submit, POST to /api/outreach
  and close the modal.
- "History" panel inside the patient drawer lists past outreach attempts
  for this patient (date, channel, outcome, notes, by whom).
- "Save as Worklist" button next to the filter bar opens a modal asking for
  a name. POSTs the current filter state to /api/worklists.
- "My Worklists" sidebar lists the user's saved worklists. Click one to
  apply its filters. Each row has a × icon with a confirmation step.

Redeploy and give me the URL.
```

## Checkpoint

- Open a patient drawer, click "Log Outreach", submit a test attempt. Refresh — the history panel should show your attempt with your email next to it.
- Save a filter combination as a worklist, refresh, click the worklist in the sidebar, confirm filters re-apply.
- Query the schema in the SQL editor (`SELECT * FROM <CATALOG>.workshop_<YOUR_USERNAME>.outreach_log` — same username substitution you used in the prompt) to see the row you just wrote.

## Stretch task (Module 2)

**Add a personal notes column.** "Add a `notes_private` STRING column to `outreach_log` that's only visible to the coordinator who wrote the row — modify the GET /api/outreach handler to return `notes_private` only for rows where the row's `user_email` matches the requesting user, and null it out for everyone else's rows."

# Wrap-up — what did your build cost? (5 min, Path B)

You just vibe-coded a working app. Because Path B ran your agent through `ucode` → Unity AI Gateway, all of that token usage was **governed and tracked** — no personal API key, and the spend is attributable to you and your group. Let's look at it.

## Your usage from the CLI

```bash
ucode usage
```

This prints your Unity AI Gateway usage summary for the last 7 days — requests and token spend across whatever agent(s) you ran. Compare notes with the person next to you who picked a different agent.

## The admin / governance view

Your workshop admin can open the **AI Gateway dashboard** (AI Gateway page → **View dashboard**) to see usage, spend, and metrics **across every participant and agent** — broken down at the endpoint, user, or group level. That's the enterprise story: any coding agent your teams use (Codex, Claude, Gemini, …) routed through one governed gateway, with rate limits, permissions, and one invoice — instead of scattered personal API keys with no visibility.

## Why this matters

| Without a gateway | With `ucode` + Unity AI Gateway |
|---|---|
| Each dev brings their own API key | OAuth with workspace identity; no keys |
| Spend is invisible / un-attributable | Usage tracked per user, group, endpoint |
| No central rate limits or model governance | Limits + model permissions set centrally |
| Agent choice fragments tooling | Any supported agent, one governed path |

# Take it further (after the workshop)

These don't fit in the 50 minutes but make great take-home extensions. Each is a single prompt you can paste into your agent after the workshop.

## CI/CD with Databricks Asset Bundles

```
Convert this project into a Databricks Asset Bundle for CI/CD:

- Generate `databricks.yml` at the repo root with two targets: `dev` (current
  workspace) and `prod` (placeholder URL — I'll fill in later)
- Define the `care-gap-outreach` app and the SQL warehouse reference as
  resources (no Lakebase project — the workshop uses Delta in personal schemas)
- Generate `.github/workflows/deploy.yml` that:
  - Triggers on push to main
  - Sets up the Databricks CLI via databricks/setup-cli@main
  - Runs `databricks bundle validate -t dev` then `databricks bundle deploy -t dev`
  - Uses DATABRICKS_HOST and DATABRICKS_TOKEN GitHub Actions secrets

Validate with `databricks bundle validate -t dev` and tell me what to do next.
```

## LLM-drafted outreach messages

```
Add a "Draft message" button on the outreach modal. When clicked, generate
a personalized outreach message:

- Route the request through the `databricks-claude-sonnet-4` serving endpoint
- Include the patient's first name, the measure name (full description),
  how overdue it is, and adapt tone to their preferred contact channel:
  phone → brief script the coordinator can read; email → friendly + scannable;
  portal → action-oriented with a clear CTA
- Show the draft in a textarea the user can edit before submitting the
  outreach attempt
```

## Performance dashboard

```
Build a Lakeview dashboard on `outreach_log` and `care_gaps`. Show:

- Outreach volume by week
- Contact rate (reached + scheduled / total) by coordinator
- Close rate (% of gaps with at least one `reached` outreach that subsequently
  moved out of the open list) by measure
- Channel mix

Save the dashboard alongside the app so the team can pin it to a workspace
homepage.
```

## ABAC governance

```
Apply ABAC policies on the underlying tables so the app inherits row/column
access automatically:

- Mask `insurance_plan` and contact details for users not in the
  `care_coordination` group
- Apply a row-level policy that scopes care gaps to a coordinator's assigned
  panel (matching `primary_pcp`)

Confirm the app behavior reflects the policies with no code changes.
```

# Troubleshooting

**`ucode` install fails / `ucode: command not found`.** `ucode` needs Python 3.12+ and `uv`. Install `uv` first (https://docs.astral.sh/uv), then `uv tool install git+https://github.com/databricks/ucode`. If the command isn't found after install, make sure `uv`'s tool bin is on your `PATH` (`uv tool update-shell`, then restart your shell).

**First `ucode <agent>` launch can't authenticate / 403.** On first launch `ucode` asks for your workspace URL and runs OAuth in the browser — complete that flow. A 403 on model calls usually means the **Unity AI Gateway preview isn't enabled** for the account, or your user/group lacks access to the endpoint — flag it to the admin (this is an account-level prerequisite, not something you can fix locally). Run `ucode status` to see the workspace, base URLs, and selected models it's using.

**My agent's existing config got changed.** Expected — `ucode` writes each agent's config file (e.g. `~/.claude/settings.json`, `~/.codex/config.toml`) and backs up the original first. Run `ucode revert` to restore your pre-workshop config.

**Blank screen — browser console shows `/api/care-gaps` returning 500.** The most common cause is a missing OAuth scope. Check the app's configured scopes:

```bash
databricks apps get <your-app-name> --output json | jq '.user_api_scopes'
```

If `sql` is not in the list, add it:

```bash
databricks apps update <your-app-name> --json '{"name": "<your-app-name>", "user_api_scopes": ["sql", "catalog.catalogs:read", "catalog.schemas:read", "catalog.tables:read"]}'
```

Then open the app URL in an incognito window (or sign out + sign back in) to get a fresh token with the new scope. The table should render.

**The app deploys but the table never loads (for other reasons).** Open the browser DevTools network tab — look at the failing `/api/care-gaps` call's response. Other causes to check: (a) the warehouse isn't bound to the app (run `databricks apps add-resource` after deploy), (b) the code reads `DATABRICKS_TOKEN` instead of OBO (re-prompt the agent: "use on-behalf-of-user auth — read `x-forwarded-access-token` from request headers and pass it as `access_token` to `sql.connect()`"), or (c) the SQL warehouse is stopped — start it manually for the first cold start.

**The Builder App stalls on a long task.** Refresh the browser tab — the SSE connection sometimes drops while the agent is working. Conversation state persists in Lakebase, so reopening the project should let you continue.

**Writes fail with `[SCHEMA_NOT_FOUND]`.** The agent skipped the `CREATE SCHEMA` step or used a different schema name than the one in your tables. Confirm you replaced every `<YOUR_USERNAME>` placeholder with the same value before pasting. If you did, re-prompt: "Run `CREATE SCHEMA IF NOT EXISTS <CATALOG>.workshop_<YOUR_USERNAME>` before any INSERT, using the exact same schema name as in the table references."

**Genie Code refuses to use my catalog.** Make sure you're querying with `<CATALOG>.care_gaps_demo.<table>` — fully qualified. The shared synthetic schema is read-only.
