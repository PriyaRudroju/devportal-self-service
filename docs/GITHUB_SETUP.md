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

The **Provision S3 Bucket** request workflow creates the catalog entity as `pending`, then the **Trigger GitHub** node dispatches [`provision-s3-bucket.yml`](../../.github/workflows/provision-s3-bucket.yml) on the branch from the form field **Git Branch** (`{{ .outputs.trigger.git_ref }}`), and only marks the entity ready once that dispatch succeeds.

This org runs the **legacy Sunset** GitHub app, and Port rejects GitHub `INTEGRATION_ACTION` nodes **inside workflows** (it resolves them against the Ocean integration, which is not installed). So the node is a **WEBHOOK** that calls the GitHub REST dispatch API directly:

```
POST https://api.github.com/repos/<org>/<repo>/actions/workflows/provision-s3-bucket.yml/dispatches
body: { "ref": "<git branch>", "inputs": { bucket_name, environment, port_run_id } }
```

`ref` is the Git branch and belongs in the **body root**, not in `inputs` — `provision-s3-bucket.yml` only declares `bucket_name`, `environment`, `port_run_id`, and undeclared inputs cause GitHub to reject the dispatch.

### Required Port secret

The node authenticates with a Port organization secret named **`GITHUB_DISPATCH_TOKEN`**.

1. Port → **Settings → Secrets → + Secret**
2. Name: `GITHUB_DISPATCH_TOKEN`
3. Value: a GitHub token with **Actions: read and write** on this repo

Without it, **Trigger GitHub** fails with GitHub `401`.

**Git Branch** is required on the form and pre-filled with `GIT_REF_DEFAULT` (`dev` on this environment), so an empty branch can never dispatch to `main`. A branch that is not present in Git fails at **Trigger GitHub** with GitHub `422 No ref found`, and because the dispatch runs before mark-ready the entity stays at `status: pending`. Automation `trigger_github_on_s3_ready` stays unpublished so the form path does not dispatch twice.

S3 and EC2 **automations** (when published) pass **`ref`** as a **top-level** field from entity **`gitRef`**. On `ENTITY_UPDATED` triggers, Port omits unchanged properties from `diff.after` — use **`diff.before.properties.gitRef`**.

| Symptom | Cause | Fix |
|---|---|---|
| Deploy Port Config fails at **Apply Port configuration** after adding a GitHub node to a workflow | Port resolves workflow `INTEGRATION_ACTION` GitHub nodes against `github-ocean`, which is not installed in legacy mode | Dispatch from a **WEBHOOK** node against the GitHub REST API (current design), or dispatch from an automation |
| Deploy Port Config fails on a webhook node URL | Webhook `url` contained a runtime template such as `{{ .outputs.trigger.git_ref }}` | Keep templates in the **body**; the URL must be static after `config.env` substitution |
| Trigger GitHub fails with `401` | Port secret `GITHUB_DISPATCH_TOKEN` missing or lacks Actions write | Create/rotate the secret in Port → Settings → Secrets |
| Trigger GitHub fails with `422 No ref found` | Typed a branch that does not exist in Git | Use a real branch name |
| Catalog entity stuck at `pending` with no GitHub run | **Trigger GitHub** failed, so **Mark Catalog Entity Ready** never ran | Open the Port run, read the Trigger GitHub response, then delete or resubmit the entity |
| Provision S3 Bucket never starts / Trigger GitHub Failed | `ref` sent inside `inputs` (undeclared GitHub input) | Keep `ref` at the body root only; re-apply Port config |
| `POST /s3/validate-git-ref` returns 404 at runtime | API Gateway does not have that route deployed | Apply terraform for `dev-portal-integration-dev`, or leave branch checking to **Trigger GitHub** |
| Provision S3 Bucket runs on **`main`** | `ref` empty because Trigger GitHub is missing or `git_ref` did not interpolate | Request workflow must use `{{ .outputs.trigger.git_ref }}`; re-apply Port config. Run `python scripts/verify_s3_github_ref.py --check-live` |
| GitHub dispatch rejected / no run at all | Dispatched branch's workflow file expects **`port_context`** but dispatch sends **`port_run_id`** | Ensure the target branch (and **`main`**) declares `port_run_id` |
| Wrong branch when using JSON mode | Used `environment: "dev"` or `git_branch` instead of `git_ref` | S3/EC2 forms use input **`git_ref`** for Git Branch; Terraform env is always `dev` on the entity |
| Old workflow inputs (`port_context`) in run logs | Dispatch used **`main`** branch workflow file | Confirm newest run shows correct branch and input **`port_run_id`** |
| `PATCH_RUN` 404 for `wfr_...` id | Port **workflow** runs use `wfr_` ids; `PATCH_RUN` only applies to **action** runs | S3 workflow uses catalog UPSERT only |
