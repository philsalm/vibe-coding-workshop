---
name: workshop-app-recipe
description: "Deterministic recipe for vibe-coding workshop Databricks Apps that query data via on-behalf-of-user (OBO) authorization. Use this skill whenever building a Databricks App that needs OBO SQL warehouse access — covers app creation with user_api_scopes including 'sql', warehouse resource binding at create time, OBO + SP-fallback auth code, and reliable SDK/REST-based deployment that avoids the broken manage_app MCP tool."
---

# Workshop App Recipe

A deterministic plumbing recipe for Databricks Apps that:

- Query data via on-behalf-of-user (OBO) authorization
- Read SQL warehouses through the user's identity so Unity Catalog row/column filters apply
- Need a SQL warehouse bound as an app resource

If the user's prompt asks you to build a Databricks App matching these conditions, follow this recipe exactly. Do not paraphrase or improvise the patterns below — each one exists because the failure mode it prevents has been observed.

---

## Critical Rules (always follow)

- **MUST** include `"sql"` in `user_api_scopes` when creating the app. Without it, the user's OBO token cannot authenticate to a SQL warehouse — the app deploys and starts but every `/api/...` call returns HTTP 500 with `databricks.sql.exc.RequestError`.
- **MUST** bind the SQL warehouse as an app resource at app-creation time (not after). The `app.yaml` `resources:` block alone is not sufficient; the platform-level binding comes from the `resources` field in the create API call.
- **MUST** create and deploy the app via `WorkspaceClient.apps.*` SDK methods or the REST API at `/api/2.0/apps/...`. **Do NOT use the `manage_app` MCP tool** — it errors with `'str' object has no attribute 'value'` on `create_or_update`, and it does not accept `user_api_scopes` or `resources` parameters even when it works.
- **MUST** authenticate SQL connections using OBO: read the user's token from the `x-forwarded-access-token` header per request and pass it as `access_token` to `sql.connect()`. Fall back to the service principal (via `Config().authenticate`) only when the header is missing.
- **NEVER** read `DATABRICKS_TOKEN` from the environment — that variable is not set in the Databricks Apps runtime. The SDK's `Config()` auto-detects the SP's OAuth M2M credentials from `DATABRICKS_CLIENT_ID` + `DATABRICKS_CLIENT_SECRET` automatically.

---

## Step 1 — Create the app

Use the SDK. One call sets the name, scopes, and resources atomically.

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import (
    App,
    ApplicationResource,
    ApplicationResourceSqlWarehouseResource,
    ApplicationResourceSqlWarehouseResourceSqlWarehousePermission,
)

w = WorkspaceClient()

app = w.apps.create_and_wait(
    app=App(
        name="<app-name>",
        description="<short description>",
        user_api_scopes=["sql"],  # required for OBO SQL warehouse queries
        resources=[
            ApplicationResource(
                name="sql-warehouse",
                sql_warehouse=ApplicationResourceSqlWarehouseResource(
                    id="<warehouse-id>",
                    permission=ApplicationResourceSqlWarehouseResourceSqlWarehousePermission.CAN_USE,
                ),
            ),
        ],
    ),
)

print(f"Created app: {app.name}")
print(f"Service principal client ID: {app.service_principal_client_id}")
print(f"URL (compute starting): {app.url}")
```

If you don't know the warehouse id, list them first and pick a `RUNNING` serverless one:

```python
for wh in w.warehouses.list():
    print(wh.id, wh.name, wh.state)
```

---

## Step 2 — Deploy the app's source code

After the app exists, deploy the staged code:

```python
from databricks.sdk.service.apps import AppDeployment, AppDeploymentMode

deployment = w.apps.deploy_and_wait(
    app_name="<app-name>",
    app_deployment=AppDeployment(
        source_code_path="<full /Workspace/... path to the staged code>",
        mode=AppDeploymentMode.SNAPSHOT,
    ),
)

print(f"Deployment status: {deployment.status.state}")
print(f"Deployment message: {deployment.status.message}")
```

If the SDK call fails for any reason, fall back to raw REST:

```python
import requests, json
host = w.config.host.rstrip("/")
headers = w.config.authenticate()
headers["Content-Type"] = "application/json"

resp = requests.post(
    f"{host}/api/2.0/apps/<app-name>/deployments",
    headers=headers,
    json={
        "source_code_path": "<full /Workspace/... path>",
        "mode": "SNAPSHOT",
    },
)
print(resp.status_code, json.dumps(resp.json(), indent=2))
```

---

## Step 3 — Backend SQL connection (OBO + SP fallback)

Every endpoint that queries data calls a helper like this. Paste this verbatim into the app's backend module and import `get_sql_connection` wherever needed.

```python
import os
from databricks.sdk.core import Config
from databricks import sql
from fastapi import Request


def get_host() -> str:
    """Return the workspace hostname without the https:// prefix."""
    cfg = Config()
    host = cfg.host
    for prefix in ("https://", "http://"):
        if host.startswith(prefix):
            host = host[len(prefix):]
    return host.rstrip("/")


def get_sql_connection(request: Request):
    """SQL connection that uses OBO when available, SP otherwise.

    Prefer the user's forwarded OAuth token so Unity Catalog permissions apply
    per-user. If the header is missing (local dev or apps without user-auth
    scopes), fall back to the service principal's OAuth M2M credentials,
    which `Config()` auto-detects from DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET.
    """
    warehouse_id = os.environ["DATABRICKS_WAREHOUSE_ID"]
    host = get_host()
    http_path = f"/sql/1.0/warehouses/{warehouse_id}"

    user_token = request.headers.get("x-forwarded-access-token")
    if user_token:
        return sql.connect(
            server_hostname=host,
            http_path=http_path,
            access_token=user_token,
        )

    cfg = Config()
    return sql.connect(
        server_hostname=host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )
```

`DATABRICKS_WAREHOUSE_ID` comes from `app.yaml` (next step).

---

## Step 4 — `app.yaml` runtime config

The deployed code's `app.yaml` declares the warehouse via `valueFrom` so the platform injects the warehouse id at runtime.

```yaml
command:
  - uvicorn
  - app:app
  - --host
  - 0.0.0.0
  - --port
  - "8000"

env:
  - name: DATABRICKS_WAREHOUSE_ID
    valueFrom: sql-warehouse
```

The `valueFrom: sql-warehouse` reference must match the resource `name` field from Step 1.

---

## Step 5 — Backend response shape (FE/BE contract)

The two most common app failures in this workshop have been (a) the React frontend crashing with `Cannot read properties of undefined` and (b) the table rendering empty even when data exists. Both come from a sloppy backend-to-frontend contract. Make the contract explicit.

**Every list endpoint returns a uniform envelope:**

```python
from fastapi import Request
from databricks import sql

@app.get("/api/care-gaps")
def get_care_gaps(request: Request, page: int = 1, page_size: int = 25):
    with get_sql_connection(request) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ... FROM ... LIMIT %s OFFSET %s",
                        (page_size, (page - 1) * page_size))
            # MUST convert tuples to dicts so the frontend can access fields by name
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]

    return {
        "items": rows,        # always a list (possibly empty)
        "page": page,
        "page_size": page_size,
        "total": len(rows),   # or a separate COUNT query for true total
    }
```

**Frontend always reads from `data.items`** and defends against an undefined response:

```typescript
const res = await fetch("/api/care-gaps?...");
const data = res.ok ? await res.json() : { items: [] };
const rows = data.items ?? [];
return <Table rows={rows} />;
```

**Do not** return raw `cur.fetchall()` tuples — they serialize as `[[...], [...], [...]]` and the frontend has no way to know which column is which.

**Do not** return a bare list (`return rows`) — wrap it in an envelope so future additions (pagination, total counts, errors) don't break the contract.

**Filter endpoints** (e.g., `/api/filters` for populating dropdowns) return the same envelope shape, one key per filter:

```python
return {
    "measures": [...],
    "priorities": [...],
    "pcps": [...],
    "insurance_plans": [...],
}
```

### SQL parameter binding — use `?`, not `%s`

The `databricks-sql-connector` uses DBAPI 2.0 `paramstyle="qmark"` (positional `?` placeholders), NOT the `%s` placeholders common in psycopg2 / mysql-connector. Use `?` everywhere:

```python
# CORRECT
cur.execute(
    "SELECT * FROM care_gaps WHERE mrn = ? ORDER BY due_date",
    (mrn,),
)

# WRONG — raises "It looks like this query may contain un-named query
# markers like %s. This format is not supported when use_inline_params=False"
cur.execute(
    "SELECT * FROM care_gaps WHERE mrn = %s ORDER BY due_date",
    (mrn,),
)
```

This applies to every endpoint that takes a parameter — patient detail, filtered list queries, anything with a `WHERE x = ?` clause. Pagination with `LIMIT ? OFFSET ?` follows the same pattern.

---

## Step 6 — Verify

After deploy completes:

```python
app = w.apps.get(name="<app-name>")
print("compute_status:", app.compute_status.state)
print("active_deployment status:", app.active_deployment.status.state)
print("user_api_scopes:", app.user_api_scopes)
print("resources:", [r.name for r in (app.resources or [])])
print("URL:", app.url)
```

Confirm all four:

- `compute_status.state == "ACTIVE"`
- `active_deployment.status.state == "SUCCEEDED"`
- `"sql"` is in `user_api_scopes`
- A resource named `"sql-warehouse"` exists in `resources`

If `"sql"` is missing from scopes, the app will deploy and run but every data query will fail. Update scopes via `w.apps.update(name="<app-name>", app=App(name="<app-name>", user_api_scopes=["sql", ...existing...]))`.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| HTTP 500 on `/api/...` calls; `databricks.sql.exc.RequestError` in app logs | App is missing the `sql` user-auth scope | Check `app.user_api_scopes`; add `"sql"` via `w.apps.update(...)`; user must re-authenticate (incognito window) |
| `'str' object has no attribute 'value'` | You called the `manage_app` MCP tool | Use `WorkspaceClient.apps.*` or REST API instead |
| App deploys but every request hangs > 60s | Warehouse cold-start or warehouse not bound | Check `app.resources` includes the warehouse; check warehouse state via `w.warehouses.get(<id>)` |
| Browser shows blank page after scope changes | User's token doesn't have the new scope yet | Open the app URL in an incognito window or sign out + sign back in |
| `KeyError: 'DATABRICKS_WAREHOUSE_ID'` at runtime | `valueFrom` not set in `app.yaml`, or the env var name doesn't match | Confirm `app.yaml` has `env: - name: DATABRICKS_WAREHOUSE_ID  valueFrom: sql-warehouse` |
