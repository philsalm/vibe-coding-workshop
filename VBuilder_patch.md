# Patching the Visual Builder App before deploying

The upstream `databricks-solutions/ai-dev-kit` Builder App has a known async-handler bug that causes MCP tool calls to silently return coroutine-object reprs instead of real results. With the bug in place, the agent stalls on the first non-trivial task. This doc walks through applying the workshop's bundled patch.

**Tracking PR:** [databricks-solutions/ai-dev-kit#526](https://github.com/databricks-solutions/ai-dev-kit/pull/526) — drop this whole doc once it merges.

## Prerequisites

Install these on your laptop before deploying.

| Tool | Check | Install |
|------|-------|---------|
| Databricks CLI v0.287.0+ | `databricks --version` | [docs.databricks.com/dev-tools/cli/install](https://docs.databricks.com/aws/en/dev-tools/cli/install) |
| Node.js 20+ | `node --version` | [nodejs.org](https://nodejs.org) |
| `uv` package manager | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `terraform` (any 1.5.x+) | `terraform --version` | [developer.hashicorp.com/terraform/install](https://developer.hashicorp.com/terraform/install) |
| CLI profile for the target workspace | `databricks auth profiles` | `databricks auth login --host <your-workspace-url>` |

## Terraform workaround for bundle deploys

The Databricks CLI's bundle commands download a pinned Terraform binary, and the upstream HashiCorp signing key has expired — so the download fails with `error downloading Terraform: unable to verify checksums signature: openpgp: key expired`. Point the CLI at your local Terraform install instead by exporting two env vars **before** running the deploy script:

```bash
export DATABRICKS_TF_EXEC_PATH="$(which terraform)"
export DATABRICKS_TF_VERSION="$(terraform version -json | python3 -c 'import sys,json; print(json.load(sys.stdin)["terraform_version"])')"
```

Add those to your shell's rc file if you'll deploy frequently.

## Apply the patch

```bash
# Clone the upstream repo
git clone https://github.com/databricks-solutions/ai-dev-kit.git
cd ai-dev-kit

# Apply the patch from the workshop repo
curl -sSL https://raw.githubusercontent.com/philsalm/vibe-coding-workshop/main/patches/fix-async-mcp-tool-execution.patch | git apply

# Verify it applied
git diff --stat
```

You should see:

```
databricks-builder-app/server/services/databricks_tools.py | 24 ++++++++++++++++++------
1 file changed, 20 insertions(+), 4 deletions(-)
```

## Deploy

```bash
cd databricks-builder-app
./scripts/deploy.sh <your-app-name> --profile <your-cli-profile>
```

The first deploy takes 5–10 minutes (Lakebase provisioning + frontend build + skills upload + app start).
