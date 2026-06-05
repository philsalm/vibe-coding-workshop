# Databricks notebook source
# MAGIC %md
# MAGIC # Vibe Coding Workshop — Admin Pre-Workshop Setup
# MAGIC
# MAGIC **Audience:** the workshop admin runs this notebook **once** before the workshop. Participants do not run it.
# MAGIC
# MAGIC It does four things:
# MAGIC
# MAGIC 1. Generates a synthetic care-gap dataset (`patients` + `care_gaps`) in a catalog and schema of your choice.
# MAGIC 2. Opens read access to that dataset for all workshop participants, and grants them `CREATE SCHEMA` on the catalog so they can self-serve their own personal write schemas during the workshop.
# MAGIC 3. Walks you through deploying the shared **Visual Builder App** from the [`ai-dev-kit`](https://github.com/databricks-solutions/ai-dev-kit#visual-builder-app) and granting all participants `CAN_USE` on it.
# MAGIC 4. Grants the Builder App's service principal the permissions it needs to read your data.
# MAGIC
# MAGIC Plan ~30 minutes, including the Builder App deploy. You can run Section 1 immediately; Sections 2 and 3 depend on the Builder App being deployed first.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ⚠️ Prerequisite for the `ucode` participant path — Unity AI Gateway (do this first)
# MAGIC
# MAGIC Participants who use their own coding agent (Path B) launch it with **`ucode`**, which routes the agent
# MAGIC through **Unity AI Gateway**. This is a **Beta** feature with account-level prerequisites that this
# MAGIC notebook **cannot** set for you — an **account admin** must confirm them before the workshop:
# MAGIC
# MAGIC 1. **Enable the Unity AI Gateway preview** from the account console **Previews** page.
# MAGIC 2. The workshop workspace is **Unity Catalog–enabled** and in a [Unity AI Gateway supported region](https://learn.microsoft.com/en-us/azure/databricks/resources/feature-region-support#model-serving-features-availability).
# MAGIC 3. The `participants_group` has access to the gateway endpoint(s) the agents will use.
# MAGIC 4. (Optional) Create the OpenTelemetry UC tables so agent telemetry lands in Unity Catalog for the dashboard. See the
# MAGIC    [coding agent integration docs](https://learn.microsoft.com/en-us/azure/databricks/ai-gateway/coding-agent-integration-beta).
# MAGIC
# MAGIC If the gateway is not enabled, `ucode` agents will fail to authenticate. Smoke-test `ucode <agent>` against
# MAGIC this workspace yourself before the session. Path A (Visual Builder App) does **not** depend on this.
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC
# MAGIC Set the widgets at the top of the notebook before running any cells.
# MAGIC
# MAGIC | Widget | Description |
# MAGIC |--------|-------------|
# MAGIC | `catalog` | Unity Catalog name to write the workshop schema into. **Required.** You must have `CREATE SCHEMA` on this catalog (and `MANAGE` on it to issue downstream grants). |
# MAGIC | `schema` | Schema name to create. Default: `care_gaps_demo`. |
# MAGIC | `num_patients` | Number of synthetic patients to generate. Default: `500`. |
# MAGIC | `sql_warehouse_name` | Name of the serverless SQL warehouse the Builder App will use. Default: `Serverless Starter Warehouse`. |
# MAGIC | `participants_group` | **Account-level** group that gets read access to the synthetic data, `CAN_USE` on the Builder App, and `CREATE SCHEMA` on the catalog. Default: `account users` (every user in the Databricks account). **Important:** use the account-level group identifier, not a workspace-level group like `users` — Unity Catalog grants on schemas and tables resolve against account-level principals, and a workspace-only group will fail with `PRINCIPAL_DOES_NOT_EXIST`. |

# COMMAND ----------

dbutils.widgets.text("catalog", "", "Catalog (required)")
dbutils.widgets.text("schema", "care_gaps_demo", "Schema")
dbutils.widgets.text("num_patients", "500", "Number of patients")
dbutils.widgets.text("sql_warehouse_name", "Serverless Starter Warehouse", "SQL warehouse name")
dbutils.widgets.text("participants_group", "account users", "Workshop participants group")

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
NUM_PATIENTS = int(dbutils.widgets.get("num_patients"))
WAREHOUSE = dbutils.widgets.get("sql_warehouse_name").strip()
PARTICIPANTS_GROUP = dbutils.widgets.get("participants_group").strip() or "account users"

assert CATALOG, "Set the 'catalog' widget before running this notebook."
assert SCHEMA, "Set the 'schema' widget."
assert NUM_PATIENTS > 0, "num_patients must be a positive integer."
assert WAREHOUSE, "Set the 'sql_warehouse_name' widget."

print(f"Target:    {CATALOG}.{SCHEMA}")
print(f"Patients:  {NUM_PATIENTS}")
print(f"Warehouse: {WAREHOUSE}")
print(f"Group:     {PARTICIPANTS_GROUP}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 1 — Generate the synthetic dataset
# MAGIC
# MAGIC Creates two tables: `patients` (demographics, contact, insurance) and `care_gaps` (open HEDIS-style care gaps with priority and due dates).
# MAGIC
# MAGIC All data is synthetic — no PHI. The shape mirrors a real care-gap feed so the workshop queries and app behavior transfer directly to production data.

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Schema {CATALOG}.{SCHEMA} ready.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1a — Patients

# COMMAND ----------

import random
import uuid
from datetime import date, timedelta

random.seed(42)

FIRST_NAMES_F = ["Mary","Patricia","Jennifer","Linda","Elizabeth","Barbara","Susan","Jessica","Sarah","Karen","Nancy","Lisa","Margaret","Betty","Sandra","Ashley","Kimberly","Donna","Emily","Michelle","Carol","Amanda","Dorothy","Melissa","Deborah","Stephanie","Rebecca","Laura","Sharon","Cynthia","Kathleen","Helen","Amy","Shirley","Angela"]
FIRST_NAMES_M = ["James","Robert","John","Michael","David","William","Richard","Joseph","Thomas","Charles","Christopher","Daniel","Matthew","Anthony","Mark","Donald","Steven","Paul","Andrew","Joshua","Kenneth","Kevin","Brian","George","Edward","Ronald","Timothy","Jason","Jeffrey","Ryan","Jacob","Gary","Nicholas","Eric","Jonathan"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker","Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores","Green","Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell","Carter","Roberts"]
PCPS = ["Dr. Patel","Dr. Nguyen","Dr. Garcia","Dr. Johnson","Dr. Kim","Dr. Singh","Dr. Brown","Dr. Cohen","Dr. Anderson","Dr. Martinez","Dr. Lee","Dr. O'Brien","Dr. Williams","Dr. Khan"]

INSURANCE_PLANS = [
    ("Aetna Commercial", 0.13),
    ("BCBS Commercial", 0.13),
    ("United Commercial", 0.10),
    ("Aetna Medicare Advantage", 0.10),
    ("BCBS Medicare Advantage", 0.10),
    ("Humana Medicare Advantage", 0.07),
    ("Medicaid MCO - Aetna Better Health", 0.10),
    ("Medicaid MCO - Keystone First", 0.10),
    ("Self-pay / Uninsured", 0.05),
    ("Other / Unknown", 0.12),
]
CONTACT_PREFERENCES = [("phone", 0.55), ("portal", 0.30), ("email", 0.15)]
AGE_BUCKETS = [(18, 44, 0.20), (45, 64, 0.35), (65, 74, 0.30), (75, 89, 0.15)]


def weighted_choice(pairs):
    r = random.random()
    cum = 0.0
    for value, weight in pairs:
        cum += weight
        if r <= cum:
            return value
    return pairs[-1][0]


def random_age():
    bucket = random.choices(AGE_BUCKETS, weights=[w for _, _, w in AGE_BUCKETS])[0]
    return random.randint(bucket[0], bucket[1])


today = date.today()
patient_rows = []

for i in range(NUM_PATIENTS):
    sex = "F" if random.random() < 0.52 else "M"
    age = random_age()
    fn = random.choice(FIRST_NAMES_F if sex == "F" else FIRST_NAMES_M)
    ln = random.choice(LAST_NAMES)
    mrn = f"MRN{i + 10001:08d}"
    pcp = random.choice(PCPS)
    plan = weighted_choice(INSURANCE_PLANS)
    pref = weighted_choice(CONTACT_PREFERENCES)
    phone = f"(555) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
    email = f"{fn.lower()}.{ln.lower()}{random.randint(1, 99)}@example.com"
    last_visit_days_ago = int(random.triangular(0, 540, 90))
    last_visit = today - timedelta(days=last_visit_days_ago)

    # Hidden clinical flags used to generate plausible gaps below
    diabetic = random.random() < (0.08 if age < 45 else 0.18 if age < 65 else 0.22)
    hypertensive = random.random() < (0.10 if age < 45 else 0.35 if age < 65 else 0.55)

    patient_rows.append({
        "mrn": mrn,
        "first_name": fn,
        "last_name": ln,
        "age": age,
        "sex": sex,
        "primary_pcp": pcp,
        "insurance_plan": plan,
        "preferred_contact": pref,
        "phone": phone,
        "email": email,
        "last_visit_date": last_visit,
        "_diabetic": diabetic,
        "_hypertensive": hypertensive,
    })

# Write the patients table (without the hidden clinical flags)
patients_df = spark.createDataFrame(
    [{k: v for k, v in p.items() if not k.startswith("_")} for p in patient_rows]
)
patients_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.patients")
print(f"Wrote {patients_df.count()} rows to {CATALOG}.{SCHEMA}.patients")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1b — Care gaps

# COMMAND ----------

MEASURES = [
    # (code, description, eligibility, base_open_rate)
    ("BCS",     "Breast Cancer Screening (mammogram, women 50-74)", lambda p: p["sex"] == "F" and 50 <= p["age"] <= 74, 0.55),
    ("COL",     "Colorectal Cancer Screening (age 45-75)",          lambda p: 45 <= p["age"] <= 75,                    0.55),
    ("CDC-A1C", "Diabetes HbA1c Testing (annual)",                  lambda p: p["_diabetic"],                          0.45),
    ("DEE",     "Diabetic Eye Exam (annual)",                       lambda p: p["_diabetic"],                          0.55),
    ("FluVax",  "Influenza Vaccination (annual)",                   lambda p: p["age"] >= 18,                          0.50),
    ("CBP",     "Controlling High Blood Pressure",                  lambda p: p["_hypertensive"],                      0.45),
]

gap_rows = []
for p in patient_rows:
    for code, desc, eligible, base_rate in MEASURES:
        if not eligible(p):
            continue
        if random.random() > base_rate:
            continue

        bucket = random.choices(
            ["overdue", "due_soon", "preventive"],
            weights=[0.40, 0.30, 0.30],
        )[0]
        if bucket == "overdue":
            due_date = today - timedelta(days=random.randint(1, 180))
        elif bucket == "due_soon":
            due_date = today + timedelta(days=random.randint(1, 30))
        else:
            due_date = today + timedelta(days=random.randint(31, 365))

        last_completed = None
        if random.random() < 0.6:
            last_completed = due_date - timedelta(days=random.randint(330, 730))

        source = "HEDIS 2026" if random.random() < 0.85 else "internal"

        gap_rows.append({
            "gap_id": str(uuid.uuid4()),
            "mrn": p["mrn"],
            "measure": code,
            "measure_description": desc,
            "due_date": due_date,
            "last_completed_date": last_completed,
            "priority": bucket,
            "source": source,
        })

gaps_df = spark.createDataFrame(gap_rows)
gaps_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.care_gaps")
print(f"Wrote {gaps_df.count()} rows to {CATALOG}.{SCHEMA}.care_gaps")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1c — Validate the data

# COMMAND ----------

# MAGIC %md
# MAGIC Distribution of gaps by measure and priority:

# COMMAND ----------

display(spark.sql(f"""
    SELECT measure, priority, COUNT(*) AS gap_count
    FROM {CATALOG}.{SCHEMA}.care_gaps
    GROUP BY measure, priority
    ORDER BY measure, priority
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC Sample joined rows — what the workshop app will display:

# COMMAND ----------

display(spark.sql(f"""
    SELECT
      p.first_name, p.last_name, p.age, p.sex, p.insurance_plan, p.primary_pcp, p.preferred_contact,
      g.measure, g.priority, g.due_date
    FROM {CATALOG}.{SCHEMA}.care_gaps g
    JOIN {CATALOG}.{SCHEMA}.patients p ON g.mrn = p.mrn
    ORDER BY g.due_date
    LIMIT 15
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1d — Open access to workshop participants
# MAGIC
# MAGIC Three grants for the participants group (`account users` by default — the account-level system group containing every user in your Databricks account):
# MAGIC
# MAGIC 1. `USE CATALOG` + `USE SCHEMA` + `SELECT` on the synthetic data so participants can query it directly (and so the apps they build can query it on their behalf via on-behalf-of-user authorization).
# MAGIC 2. `CREATE SCHEMA` on the catalog so each participant can self-serve their own personal write schema (e.g., `workshop_<their_username>`) at the start of the workshop. Their personal schema is where their apps will write any UC-resident state during the workshop — keeping participants from overwriting one another.
# MAGIC 3. `CAN_USE` on the SQL warehouse via the workspace permissions API so the apps they build can route OBO queries through it. Warehouse permissions are not managed via SQL `GRANT` — we set them via `/api/2.0/permissions/warehouses/{id}`.

# COMMAND ----------

participant_grants_sql = f"""
-- Read access for participants on the synthetic data.
GRANT USE CATALOG ON CATALOG `{CATALOG}` TO `{PARTICIPANTS_GROUP}`;
GRANT USE SCHEMA  ON SCHEMA  `{CATALOG}`.`{SCHEMA}` TO `{PARTICIPANTS_GROUP}`;
GRANT SELECT      ON TABLE   `{CATALOG}`.`{SCHEMA}`.`patients`  TO `{PARTICIPANTS_GROUP}`;
GRANT SELECT      ON TABLE   `{CATALOG}`.`{SCHEMA}`.`care_gaps` TO `{PARTICIPANTS_GROUP}`;

-- Let each participant create their own personal write schema in the catalog.
GRANT CREATE SCHEMA ON CATALOG `{CATALOG}` TO `{PARTICIPANTS_GROUP}`;
"""

print(participant_grants_sql)

for stmt in [s.strip() for s in participant_grants_sql.strip().split(";") if s.strip() and not s.strip().startswith("--")]:
    try:
        spark.sql(stmt)
        print(f"OK:     {stmt[:90]}")
    except Exception as e:
        print(f"FAILED: {stmt[:90]}")
        print(f"        -> {type(e).__name__}: {str(e)[:160]}")

# COMMAND ----------

# MAGIC %md
# MAGIC Grant `CAN_USE` on the SQL warehouse to the participants group via the permissions API.

# COMMAND ----------

import json
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Look up the warehouse ID from the name
warehouse_id = None
for wh in w.warehouses.list():
    if wh.name == WAREHOUSE:
        warehouse_id = wh.id
        break
assert warehouse_id, f"Warehouse named '{WAREHOUSE}' not found in this workspace"

print(f"Warehouse '{WAREHOUSE}' resolved to id={warehouse_id}")

# Patch the warehouse permissions to add CAN_USE for the participants group
try:
    w.api_client.do(
        method="PATCH",
        path=f"/api/2.0/permissions/warehouses/{warehouse_id}",
        body={
            "access_control_list": [
                {"group_name": PARTICIPANTS_GROUP, "permission_level": "CAN_USE"}
            ]
        },
    )
    print(f"OK: granted CAN_USE on warehouse {warehouse_id} to '{PARTICIPANTS_GROUP}'")
except Exception as e:
    print(f"FAILED to grant warehouse CAN_USE: {type(e).__name__}: {str(e)[:200]}")
    print("If you don't have admin permission on this warehouse, ask a workspace admin to run the equivalent grant in the UI:")
    print(f"  SQL > SQL Warehouses > '{WAREHOUSE}' > Permissions > Add '{PARTICIPANTS_GROUP}' with Can use")

# COMMAND ----------

# MAGIC %md
# MAGIC Section 1 is done — shared data is created and accessible to participants, and the warehouse is opened up for their apps' OBO queries. Continue to Section 2 to deploy the shared Builder App.
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 2 — Deploy the shared Visual Builder App
# MAGIC
# MAGIC One Builder App, deployed by you, used by every workshop participant. Run these steps **from your laptop terminal**, not from this notebook — the install is a shell script that needs the Databricks CLI on your local machine.
# MAGIC
# MAGIC ### Prerequisites on your laptop
# MAGIC
# MAGIC | Tool | Check | Install |
# MAGIC |------|-------|---------|
# MAGIC | Databricks CLI v0.287.0+ | `databricks --version` | [docs.databricks.com/dev-tools/cli/install](https://docs.databricks.com/aws/en/dev-tools/cli/install) |
# MAGIC | Node.js 20+ | `node --version` | [nodejs.org](https://nodejs.org) |
# MAGIC | `uv` package manager | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
# MAGIC | CLI profile for this workspace | `databricks auth profiles` | `databricks auth login --host <your-workspace-url>` |
# MAGIC
# MAGIC ### Deploy steps
# MAGIC
# MAGIC ```bash
# MAGIC # 1. Clone the ai-dev-kit repo
# MAGIC git clone https://github.com/databricks-solutions/ai-dev-kit.git
# MAGIC cd ai-dev-kit/databricks-builder-app
# MAGIC
# MAGIC # 2. Deploy. Replace <your-cli-profile> with your CLI profile name.
# MAGIC ./scripts/deploy.sh my-builder-app --profile <your-cli-profile>
# MAGIC ```
# MAGIC
# MAGIC The deploy script provisions a Lakebase database, creates the Databricks App, configures Postgres permissions for the app's service principal, builds the React frontend, and starts the app. The first deploy takes ~5–10 minutes.
# MAGIC
# MAGIC When it finishes, it prints the app URL — something like `https://my-builder-app-<workspace-id>.<region>.databricksapps.com`. Open it. You should see the Builder App chat UI.
# MAGIC
# MAGIC ### Add the SQL warehouse as an app resource
# MAGIC
# MAGIC The `deploy.sh` script does not bind a SQL warehouse to the app — you need to do this explicitly. Binding the warehouse as an **app resource** is the right pattern: it auto-grants the app's service principal `CAN_USE` on the warehouse and exposes the warehouse ID to the app's runtime via env vars, so you don't have to hand-grant warehouse permissions separately.
# MAGIC
# MAGIC You can do this two ways:
# MAGIC
# MAGIC **From the CLI** (replace the warehouse ID with your own):
# MAGIC
# MAGIC ```bash
# MAGIC databricks apps add-resource my-builder-app --json '{
# MAGIC   "name": "sql-warehouse",
# MAGIC   "sql_warehouse": {
# MAGIC     "id": "<your-warehouse-id>",
# MAGIC     "permission": "CAN_USE"
# MAGIC   }
# MAGIC }' --profile <your-cli-profile>
# MAGIC ```
# MAGIC
# MAGIC Find your warehouse ID with `databricks warehouses list --profile <your-cli-profile>` (it's the value in the `ID` column for the warehouse you set in the `sql_warehouse_name` widget at the top of this notebook).
# MAGIC
# MAGIC **From the UI:** open **Compute > Apps > `my-builder-app` > Resources > Add resource**, choose **SQL Warehouse**, pick your warehouse, set permission to **Can use**, save. The app will redeploy automatically.
# MAGIC
# MAGIC ### Find the app's service principal
# MAGIC
# MAGIC Databricks Apps auto-provisions a service principal for each app. You'll need its **application ID** (a UUID) to grant Unity Catalog access in Section 3.
# MAGIC
# MAGIC 1. In the workspace UI, open **Compute > Apps**.
# MAGIC 2. Click `my-builder-app`.
# MAGIC 3. On the overview tab, find the row labeled **Service principal** or **Service principal client ID**. The value is a UUID, e.g., `bf7b7f5b-c9d4-4ce2-8f50-7b4725c047a1`.
# MAGIC 4. Copy the UUID and paste it into the `app_sp_client_id` widget at the top of Section 3 below.
# MAGIC
# MAGIC You can also retrieve it from the CLI: `databricks apps get my-builder-app --profile <your-cli-profile>` — look for `service_principal_client_id` in the output.
# MAGIC
# MAGIC ### Grant participants `CAN_USE` on the Builder App
# MAGIC
# MAGIC The deploy creates the app private to you. Open it up to your workshop participants group so they can launch it on the day.
# MAGIC
# MAGIC **From the CLI** (replace the group name to match your `participants_group` widget value):
# MAGIC
# MAGIC ```bash
# MAGIC databricks api patch /api/2.0/permissions/apps/my-builder-app \
# MAGIC   --profile <your-cli-profile> \
# MAGIC   --json '{
# MAGIC     "access_control_list": [
# MAGIC       {"group_name": "account users", "permission_level": "CAN_USE"}
# MAGIC     ]
# MAGIC   }'
# MAGIC ```
# MAGIC
# MAGIC **From the UI:** **Compute > Apps > `my-builder-app` > Permissions > Add**, pick the participants group, set permission to **Can use**, save.
# MAGIC
# MAGIC Participants will reach the app at the URL printed by `deploy.sh` (something like `https://my-builder-app-<workspace-id>.<region>.databricksapps.com`). Send them that URL in your workshop logistics email.
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 3 — Grant the Builder App's service principal access to your Unity Catalog data
# MAGIC
# MAGIC One Builder App, one service principal — this is the only SP that needs UC grants. Section 1d already covered direct user access; this section covers the app's own queries (for example, when the Builder App reads schema metadata to help a participant write SQL).
# MAGIC
# MAGIC Set the `app_sp_client_id` widget below to the UUID from Section 2, then run the next cells. The notebook prints the GRANT SQL and attempts to execute it; if you don't have admin privileges, copy the SQL and hand it to a workspace / metastore admin.

# COMMAND ----------

dbutils.widgets.text("app_sp_client_id", "", "Builder App service principal client ID (UUID)")

SP_CLIENT_ID = dbutils.widgets.get("app_sp_client_id").strip()

assert SP_CLIENT_ID, "Set the 'app_sp_client_id' widget to the service principal UUID from Section 2 before running."

grants_sql = f"""
-- Grant the Builder App's service principal read access on the workshop data.
-- Run as a workspace / metastore admin if any fail below.

GRANT USE CATALOG ON CATALOG `{CATALOG}` TO `{SP_CLIENT_ID}`;
GRANT USE SCHEMA  ON SCHEMA  `{CATALOG}`.`{SCHEMA}` TO `{SP_CLIENT_ID}`;
GRANT SELECT      ON TABLE   `{CATALOG}`.`{SCHEMA}`.`patients`  TO `{SP_CLIENT_ID}`;
GRANT SELECT      ON TABLE   `{CATALOG}`.`{SCHEMA}`.`care_gaps` TO `{SP_CLIENT_ID}`;
"""

print(grants_sql)

# COMMAND ----------

# Attempt to run each grant. Any that fail will be printed so you (or an admin) can rerun them.
statements = [s.strip() for s in grants_sql.strip().split(";") if s.strip() and not s.strip().startswith("--")]
for stmt in statements:
    try:
        spark.sql(stmt)
        print(f"OK:     {stmt[:90]}")
    except Exception as e:
        print(f"FAILED: {stmt[:90]}")
        print(f"        -> {type(e).__name__}: {str(e)[:160]}")

# COMMAND ----------

# MAGIC %md
# MAGIC The Builder App is now wired to your data. (The warehouse `CAN_USE` permission was handled in Section 2 when you added the warehouse as an app resource — no separate UI step needed here.)
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 4 — Smoke test (recommended)
# MAGIC
# MAGIC Confirm the Builder App can reach your data:
# MAGIC
# MAGIC 1. Open the Builder App URL.
# MAGIC 2. In the chat, paste a prompt like:
# MAGIC
# MAGIC ```
# MAGIC Connect to the SQL warehouse "<your-warehouse-name>" and query the catalog "<your-catalog>", schema "<your-schema>".
# MAGIC How many open care gaps are there by measure? Return a sorted list with counts.
# MAGIC ```
# MAGIC
# MAGIC Replace the placeholders with the values you set in the widgets at the top.
# MAGIC
# MAGIC **Expected:** counts grouped by measure (BCS, COL, CDC-A1C, DEE, FluVax, CBP). If you get that, permissions are wired correctly and you're ready for the workshop.
# MAGIC
# MAGIC **If you see a permission-denied error:** re-check the GRANT output in Section 3 (any FAILED lines need an admin to re-run), and double-check the warehouse Permissions UI step.
