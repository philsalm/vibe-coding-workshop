<!-- toc -->

# Healthcare Vibe Coding Workshop — Hands-On Content

A 50-minute hands-on session in which you build a **Care Gap Outreach** Databricks App. You can follow the scripted prompts below using either the shared Visual Builder App or your own coding agent (Claude Code / Cursor + ai-dev-kit), or go off-script and build something of your own using the synthetic data we've prepared.

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
| **B — Your own coding agent** | Claude Code (or Cursor) + ai-dev-kit on your laptop | ~10 min during workshop | Familiar dev environment, more control over file edits |
| **C — Choose your own** | Anything you want | varies | You already have a healthcare app idea — use the shared data and your personal schema and build it |

The prompts below are written so they work in both Path A and Path B with no changes. Path C participants are welcome to take what they want.

## Schedule

| Time | Block |
|------|-------|
| 0:00–0:05 | Setup — choose your path, create your personal schema, Path B starts install |
| 0:05–0:30 | **Module 1** — Build the care gap outreach app (~25 min) |
| 0:30–0:45 | **Module 2** — Add per-user write state with Delta tables (~15 min) |
| 0:45–0:50 | Buffer + Q&A |

# Setup (5 min)

## Step 1 — Confirm you can query the shared data

The workshop's synthetic data lives in a shared `mvp_quality_workshop` schema (the workshop admin will tell you the exact catalog name in their logistics email — call it `<CATALOG>` below). This is the **same governed dataset** a metric view reads in the companion Metric Views workshop — one source of truth, used here for an operational app. Read access is open to all workshop participants. Module 2 will have your app create its own write schema later — nothing to set up by hand.

Open the SQL editor in your workspace and run:

```sql
SELECT measure, priority, COUNT(*) AS gap_count
FROM <CATALOG>.mvp_quality_workshop.care_gaps
GROUP BY measure, priority
ORDER BY measure, priority;
```

You should see a breakdown of open care gaps by HEDIS-style measure (BCS, COL, CBP, CDC, CIS, WCV, FUH) and priority (overdue, due_soon, preventive). If this errors with a permissions issue, raise your hand — the admin's setup may not have completed.

## Step 2 (Path A only) — Open the Builder App

Open the URL the admin shared in the workshop logistics email. You should see the Builder App's chat interface. Click **New project** and give it a name like `care-gap-outreach`. You're ready to paste prompts.

## Step 2 (Path B only) — Install your tooling

You have ~10 minutes; you'll lose some build time later but it's the only way to use your own environment.

We install Claude Code with **`ucode`** — Databricks' Unity AI Gateway Coding CLI. `ucode` installs and configures the agent for you, authenticates to this workspace over **OAuth (no API keys or PATs)**, and routes every model call to the workspace's **Databricks-hosted Claude endpoint** so usage is governed and tracked centrally. ([Docs](https://learn.microsoft.com/en-us/azure/databricks/ai-gateway/coding-agent-integration-beta).)

```bash
# 1. Prerequisites: Python 3.12+, uv, and Node/npm (ucode uses npm to install the
#    Claude Code CLI for you). Install uv if you don't have it:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install ucode:
uv tool install git+https://github.com/databricks/ucode

# 3. Create an empty project directory and initialize an APX project:
mkdir care-gap-outreach && cd care-gap-outreach
pip install ai-dev-kit
apx init

# 4. Launch Claude Code through ucode. The FIRST run prompts for your workspace
#    URL and opens an OAuth login in your browser, then installs (if needed) and
#    configures Claude Code to use this workspace's Databricks Claude endpoint.
#    Later runs go straight to Claude Code.
ucode claude
```

You're ready to paste prompts.

> **Note.** `ucode` is in Beta and requires the **Unity AI Gateway** preview to be enabled on your account (the workshop admin handles this) plus a Unity Catalog–enabled workspace in a [supported region](https://learn.microsoft.com/en-us/azure/databricks/resources/feature-region-support). If `ucode claude` fails to authenticate with a 403, the workspace isn't enrolled yet — raise your hand. You can confirm routing later with `ucode usage` (your Unity AI Gateway usage for the last 7 days).

## Step 2 (Path C only) — Skim, then go

Take the data shape from Step 1 and the agent of your choice. Build whatever you want. The prompts below are inspiration if you need a starting point.

## What to expect when the app deploys

Your app will use **on-behalf-of-user (OBO) authorization** — each user's queries run as their identity, so Unity Catalog row/column filters apply per-user. The first time you open your deployed app URL, you may need to **sign out and back in** (or open the URL in an incognito window) so Databricks issues you a fresh access token with the OAuth scopes your app requires. Plan on a ~10-second re-auth detour the first time. Subsequent visits will not require this.

# Module 1 — Build the care gap outreach app (25 min)

**Goal.** A deployed Databricks App showing open care gaps as a filterable, paginated table with a patient detail drawer.

## Why use OBO for SQL queries

Databricks Apps give you two ways to authenticate to data: the app's service principal (shared identity for all users) or **on-behalf-of-user** (each query runs as the requesting user). For a care coordination tool you almost always want OBO so each clinician's Unity Catalog row/column filters apply, audit trails attribute correctly, and team-scoped policies (e.g., "you can only see your panel's patients") just work.

## The prompt

Replace `<CATALOG>` with the catalog name from the admin's logistics email, then paste this into the Builder App chat (Path A) or Claude Code (Path B).

```
Build and deploy a Databricks App named `care-gap-outreach`: a Python FastAPI
backend serving a React frontend as a single deployable Databricks App. No
separate services. The app helps a care coordination team work through open
care gaps and contact patients to close them.

DATA SOURCE
Two Unity Catalog views, joined on MRN, queried via a serverless SQL warehouse:
- `<CATALOG>.mvp_quality_workshop.care_gaps` — gap_id, mrn, measure,
  measure_description, due_date, last_completed_date, priority, source
- `<CATALOG>.mvp_quality_workshop.patients` — mrn, first_name, last_name,
  age, sex, primary_pcp, insurance_plan, preferred_contact, phone, email,
  last_visit_date

AUTHORIZATION — use on-behalf-of-user (OBO) so each user's Unity Catalog
permissions apply to their own queries:
- Create the app with `user_api_scopes=["sql"]`. Without this scope the user's
  OBO token cannot authenticate to the warehouse and every /api/... call returns
  HTTP 500.
- In the SQL connection helper, read the user's token from the
  `x-forwarded-access-token` request header and pass it as `access_token=...`
  to `sql.connect()`. Fall back to the app service principal (SDK `Config()`
  credentials_provider) only when that header is missing (local dev).
- NEVER read DATABRICKS_TOKEN — it is not set in the Apps runtime.

DATABRICKS APPS PLUMBING — non-obvious; follow exactly or the app fails to
deploy or errors at runtime:
- Create AND deploy with the Databricks SDK (`WorkspaceClient.apps.
  create_and_wait` then `deploy_and_wait`) or the REST API at
  `/api/2.0/apps/...`. Do NOT use the `manage_app` MCP tool — it is broken.
- At create time, bind a serverless SQL warehouse as an app resource named
  `sql-warehouse` with CAN_USE, passed in the create call's `resources` field
  (alongside `user_api_scopes`). List warehouses and pick a RUNNING serverless
  one if I haven't given an id. Do NOT hardcode the warehouse id — the
  `app.yaml` `resources:` block alone is NOT sufficient; the binding must be in
  the create call.
- In `app.yaml`, inject the warehouse id into env var `DATABRICKS_WAREHOUSE_ID`
  via `valueFrom: sql-warehouse` (must match the resource name above).
- Use `databricks-sql-connector`. The connector uses qmark paramstyle: bind
  with `?`, never `%s`.
- Convert cursor rows to dicts (dict(zip([c[0] for c in cur.description], row)))
  before returning — never return raw tuples.

BACKEND RESPONSE CONTRACT (prevents empty-table / "Cannot read undefined")
- Every list endpoint returns a uniform envelope, never a bare list:
    {"items": [...], "page": n, "page_size": n, "total": n}   # items always a list
- The filter-options endpoint returns one key per filter:
    {"measures": [...], "priorities": [...], "pcps": [...], "insurance_plans": [...]}
- The frontend always reads `data.items ?? []` and guards a non-ok response with
  `{ items: [] }` so it never crashes on undefined.

FRONTEND & STATIC SERVING (prevents deploy-succeeds-but-blank-screen)
- Build the single-page UI as a self-contained index.html — no build step, no
  transpiler. Do NOT transpile in the browser: no <script type="text/babel">
  and no Babel-standalone from a CDN (if Babel fails to load, the page renders
  blank with no console error).
- Use EXACTLY this module bootstrap. Importing from `htm/preact` pulls in a
  SECOND preact instance, so hooks throw on first render and the page goes
  blank — bind htm to the one preact `h` instead:

    <script type="importmap">{"imports":{
      "preact":"https://esm.sh/preact@10.19.3",
      "preact/hooks":"https://esm.sh/preact@10.19.3/hooks",
      "htm":"https://esm.sh/htm@3.1.1"
    }}</script>
    <script type="module">
      import { h, render } from 'preact';
      import { useState, useEffect, useCallback } from 'preact/hooks';
      import htm from 'htm';
      const html = htm.bind(h);   // single preact instance — do NOT import htm/preact
      // ... build the app with html`...` and render(html`<${App}/>`, document.getElementById('app'));
    </script>

  The HTML body must contain the matching mount node: <div id="app"></div>.
- Resolve static paths relative to the app file, never the working directory:
  BASE = pathlib.Path(__file__).resolve().parent; mount StaticFiles at
  directory=str(BASE / "static") and serve str(BASE / "static" / "index.html")
  with FileResponse. The Apps container CWD is not guaranteed to be the app dir.
- Register every /api/* route BEFORE the catch-all /{full_path:path} SPA route,
  and mount StaticFiles at /static so the catch-all never intercepts API or
  static requests; the catch-all returns index.html only for non-/api,
  non-/static paths.

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

Deploy, then VERIFY the page actually renders before giving me the URL: load
the app URL and confirm the table appears and the browser console is clean. A
blank page with a successful deployment is a frontend module error, not a
deploy success — fix it before reporting done. Then give me the app URL.
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
Now add app state to care-gap-outreach using Delta tables. The same OBO SQL
warehouse connection from Module 1 handles the reads AND the writes — no new
auth or provisioning.

DON'T REGRESS THE MODULE 1 PLUMBING
- Reuse the existing OBO get_sql_connection(request) helper for reads AND writes
  (x-forwarded-access-token, SP fallback; never DATABRICKS_TOKEN).
- Bind parameters with qmark `?`, never `%s`. Convert cursor rows to dicts.
- Register the NEW /api/* routes BEFORE the catch-all /{full_path:path} SPA
  route, or they'll be swallowed and return index.html instead of JSON.
- Keep __file__-relative static paths (BASE = pathlib.Path(__file__).resolve().
  parent) for the StaticFiles mount and the index.html FileResponse.
- Redeploy with the Databricks SDK (`apps.deploy_and_wait`) or REST — NOT the
  `manage_app` MCP tool.

DON'T REGRESS THE FRONTEND (this is the #1 way Module 2 breaks)
When you extend index.html for the new modals/history/worklists, keep the SAME
module bootstrap as Module 1 — no in-browser Babel, and a SINGLE preact
instance: import { h, render } from 'preact'; hooks from 'preact/hooks'; htm
from 'htm'; const html = htm.bind(h). Do NOT switch any import to 'htm/preact'
(it bundles a second preact instance → hooks throw → blank screen).

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

Redeploy, then VERIFY the page actually renders before giving me the URL: load
the app URL and confirm the table AND the new controls appear and the browser
console is clean. A blank page with a successful deployment is a frontend module
error (usually a second preact instance) — fix it before reporting done. Then
give me the URL.
```

## Checkpoint

- Open a patient drawer, click "Log Outreach", submit a test attempt. Refresh — the history panel should show your attempt with your email next to it.
- Save a filter combination as a worklist, refresh, click the worklist in the sidebar, confirm filters re-apply.
- Query the schema in the SQL editor (`SELECT * FROM <CATALOG>.workshop_<YOUR_USERNAME>.outreach_log` — same username substitution you used in the prompt) to see the row you just wrote.

## Stretch task (Module 2)

**Add a personal notes column.** "Add a `notes_private` STRING column to `outreach_log` that's only visible to the coordinator who wrote the row — modify the GET /api/outreach handler to return `notes_private` only for rows where the row's `user_email` matches the requesting user, and null it out for everyone else's rows."

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

**Genie Code refuses to use my catalog.** Make sure you're querying with `<CATALOG>.mvp_quality_workshop.<view>` — fully qualified. The shared synthetic schema is read-only.
