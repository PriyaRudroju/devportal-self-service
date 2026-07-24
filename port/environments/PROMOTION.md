# Port Config Promotion Runbook

Single Port org (`org_NaOn60IA22iSZcWo`), one GitHub repo (`PriyaRudroju/devportal-self-service`). Environments differ by folder and `config.env` values — not by separate Port orgs.

## Folder layout

```
port/
  blueprints/              # Shared schema (all environments)
  environments/
    dev/config.env         # Dev URLs, TFC workspace, etc.
    dev/workflows/
    dev/actions/           # Legacy (optional)
    dev/automations/       # Legacy (optional)
    qa/...
    prod/...
```

## Variable precedence

1. Values in `port/environments/<env>/config.env`
2. Environment variable overrides in CI: `API_GATEWAY_URL`, `GITHUB_INSTALLATION_ID`, `TFC_WORKSPACE`, etc.

GitHub Environment variables should override `config.env` placeholders in CI. Local apply can rely on `config.env` alone.

## Day-to-day: change Port config in dev

1. Edit JSON under `port/environments/dev/` (workflows, actions) or shared `port/blueprints/`.
2. Validate locally:
   ```bash
   python scripts/apply_port_config.py --env dev --plan
   ```
3. Commit and open PR → `validate-port-config.yml` runs `--plan` for dev, qa, prod.
4. Merge to `main` → `deploy-port-config.yml` applies **dev** to Port automatically.

## Promote dev → qa → prod

Promotion is **two steps**: sync Git folders, then apply to Port.

### Step 1 — Sync JSON via PR (keep each `config.env` unique)

1. Copy structural changes from `dev/workflows/` → `qa/workflows/` and `prod/workflows/`.
2. Adjust environment-specific fields (form enum, titles) — do **not** overwrite `qa/config.env` or `prod/config.env`.
3. Open PR; wait for validate workflow to pass.
4. Merge PR.

### Step 2 — Apply to Port (GitHub Actions)

| Target | Workflow | GitHub Environment |
|---|---|---|
| QA | **Promote Port Config** → `qa` | `qa` |
| Prod | **Promote Port Config** → `prod` | `production` (requires approvers) |

Or locally:

```bash
export PORT_CLIENT_ID=...
export PORT_CLIENT_SECRET=...
export API_GATEWAY_URL=...   # optional override
python scripts/apply_port_config.py --env qa --plan
python scripts/apply_port_config.py --env qa
```

Use `--skip-legacy` after migrating fully to Port Workflows.

## GitHub Environment setup (one-time)

Create environments: `development`, `qa`, `production`.

| Environment | Variables | Secrets |
|---|---|---|
| `development` | `API_GATEWAY_URL`, `GITHUB_INSTALLATION_ID`, `TFC_WORKSPACE` | `PORT_CLIENT_ID`, `PORT_CLIENT_SECRET` |
| `qa` | QA-specific URLs/workspace | Port creds (same or QA-specific) |
| `production` | Prod URLs/workspace | Prod creds + **required reviewers** |

## Demo script for stakeholders

> Port configuration lives as JSON in Git under `port/environments/`. When we merge to main, a pipeline applies dev config to our Port org. To promote to QA or Prod, we merge reviewed JSON changes and run a gated promote workflow. Same Port org throughout — only webhook URLs and Terraform workspace names change per environment.

## Troubleshooting

| Issue | Fix |
|---|---|
| `--plan` fails on `REPLACE_` | Set real values in `config.env` or export env vars before apply |
| Deploy workflow skips | Push must touch `port/**` or run workflow manually |
| Wrong API URL in Port | Check GitHub Environment variable for that env |
| 409 on create | Normal — script retries with PUT/PATCH update |
