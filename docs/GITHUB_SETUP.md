# GitHub Repository Setup (Three-Branch Port GitOps)

One-time configuration for `PriyaRudroju/devportal-self-service`.

## Branches

| Branch | Purpose | Default branch candidate |
|---|---|---|
| `dev` | Day-to-day development; Port dev playground | Yes (team preference) |
| `qa` | Pre-production validation; Port qa playground | No |
| `main` | Production source of truth; Port prod | No |

### Create branches (if not present)

After the restructure is merged, ensure all three branches exist on the remote:

```bash
git push -u origin dev
git push -u origin qa
git push -u origin main
```

### Set default branch

In **GitHub → Settings → General → Default branch**:

- Set to **`dev`** for day-to-day feature work, **or**
- Keep **`main`** if your team treats main as the canonical remote default (feature PRs still target `dev` first).

Document the choice in your team wiki.

## Branch protection rules

Configure in **Settings → Branches → Add rule**:

### `qa`

- Require pull request before merging
- Require approvals: 1 (optional)
- Restrict merges from: allow `dev` only (via ruleset or team process)

### `main`

- Require pull request before merging
- Require approvals: 1+ (production approvers)
- Restrict merges from: allow `qa` only (via ruleset or team process)
- Require GitHub Environment `production` for deploy workflow (already set in workflow YAML)

### `dev`

- Optional: require PR for direct pushes
- Allow feature branch merges freely

## GitHub Environments

Create in **Settings → Environments**:

| Name | Used by branch | Required reviewers |
|---|---|---|
| `development` | `dev` | No |
| `qa` | `qa` | Optional |
| `production` | `main` | **Yes** (recommended) |

### Variables (per environment)

| Variable | Example (dev) |
|---|---|
| `API_GATEWAY_URL` | `https://fvoyz6jb9i.execute-api.us-east-2.amazonaws.com` |
| `TFC_WORKSPACE` | `dev-portal-s3-dev` / `dev-portal-s3-qa` / `dev-portal-s3-prod` |
| `GITHUB_INSTALLATION_ID` | Only when using GitHub Ocean mode |

### Secrets (per environment or repo-level)

| Secret | Purpose |
|---|---|
| `PORT_CLIENT_ID` | Port API apply |
| `PORT_CLIENT_SECRET` | Port API apply |
| `TF_API_TOKEN` | Terraform Cloud (runtime EC2/S3 workflows) |
| `TF_CLOUD_ORGANIZATION` | Terraform Cloud org name |

Variable precedence: `port/environments/config.env` first, then GitHub Environment variables override in CI.

## Workflows per branch

Each branch should contain **only** these Port GitOps workflows (plus runtime workflows as needed):

| Branch | Port deploy | Port validate | Trigger branch |
|---|---|---|---|
| `dev` | `deploy-port-config.yml` | `validate-port-config.yml` | `dev` |
| `qa` | `deploy-port-config.yml` | `validate-port-config.yml` | `qa` |
| `main` | `deploy-port-config.yml` | `validate-port-config.yml` | `main` |

**Do not** add `promote-port-config.yml` — promotion is Git merge dev → qa → main.

## Port GitHub automation branch ref

S3 and EC2 automations pass **`ref`** as a **top-level dispatch branch parameter** in `integrationActionExecutionProperties` from entity **`gitRef`** (form **Git Branch**). **`ref` is not a GitHub workflow input** — do not include it in `workflowInputs`. If `ref` is missing at the top level, GitHub defaults to **`main`**.

On `ENTITY_UPDATED` triggers (S3 `pending → ready`, EC2 `pending → approved`), Port omits **unchanged** properties from `diff.after`. Read **`gitRef` from `diff.before.properties.gitRef`** in automation templates — same pattern as EC2. Using `diff.after` leaves `ref` empty and GitHub defaults to **`main`**.

| Branch | `GIT_REF_DEFAULT` in `config.env` |
|---|---|
| `dev` | `dev` |
| `qa` | `qa` |
| `main` | `main` |

Verify Port dispatches to the correct branch after changing default branch settings.

## S3 provisioning branch ref

S3 and EC2 automations pass **`ref`** as a **top-level** field in `integrationActionExecutionProperties` from entity **`gitRef`**. **`ref` is the Git branch for dispatch, not a GitHub workflow input** — do not include it in `workflowInputs` for [`provision-s3-bucket.yml`](../../.github/workflows/provision-s3-bucket.yml) (which only declares `bucket_name`, `environment`, `port_run_id`). Extra inputs cause GitHub to reject the dispatch.

| Symptom | Cause | Fix |
|---|---|---|
| Deploy Port Config 422 `github-ocean is not a valid integration` | Workflow node used Ocean integration in legacy mode | Use automation dispatch only (this repo on `dev`) |
| Provision S3 Bucket never starts / automation Failed | `ref` sent inside `workflowInputs` (undeclared GitHub input) | Keep `ref` top-level only; re-apply Port config |
| Automation never runs after form submit | Workflow `UPSERT_ENTITY` / in-workflow Port API calls do not emit catalog automation events | Mark ready via **external** Port API call (Lambda `POST /s3/mark-ready` or Teams-style handler) so `ENTITY_UPDATED` fires |
| Provision S3 Bucket runs on **`main`** | `ref` empty because automation reads `gitRef` from `diff.after` on status-only update | Use `diff.before.properties.gitRef` for `ref` (and other unchanged fields); re-apply Port config |
| Feature branch not in dropdown | `FEATURE_GIT_REFS` empty | Push `port/**` on `feature/*` branch to trigger Deploy Port Config |
| Wrong branch when using JSON mode | Used `environment: "dev"` or `git_branch` instead of `git_ref` | S3/EC2 forms use input **`git_ref`** for Git Branch; Terraform env is always `dev` on the entity |
| Old workflow inputs (`port_context`) in run logs | Dispatch used **`main`** branch workflow file | Confirm newest run shows correct branch and input **`port_run_id`** |
| `PATCH_RUN` 404 for `wfr_...` id | Port **workflow** runs use `wfr_` ids; `PATCH_RUN` only applies to **action** runs | S3 workflow uses catalog UPSERT only; automation uses `reportWorkflowStatus` |
