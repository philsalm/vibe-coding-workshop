# Deploying the Visual Builder App

One shared Visual Builder App from [`databricks-solutions/ai-dev-kit`](https://github.com/databricks-solutions/ai-dev-kit#visual-builder-app), deployed by the admin and used by every workshop participant (Path A). Deploy it from your laptop before the workshop.

> **No patch needed.** An async MCP-tool-execution bug used to require a workshop hotfix; that fix is now upstream on ai-dev-kit's default branch, so a fresh clone already includes it. (The fix landed independently of [PR #526](https://github.com/databricks-solutions/ai-dev-kit/pull/526) — `databricks_tools.py` now detects a returned coroutine and awaits it.)

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

## Deploy

```bash
git clone https://github.com/databricks-solutions/ai-dev-kit.git
cd ai-dev-kit/databricks-builder-app
./scripts/deploy.sh <your-app-name> --profile <your-cli-profile>
```

The first deploy takes 5–10 minutes (Lakebase provisioning + frontend build + skills upload + app start). When it finishes it prints the app URL.

Then continue with **Section 2** of `setup_workshop.py` to bind a SQL warehouse to the app and grant participants `CAN_USE`.
