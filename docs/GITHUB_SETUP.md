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

Legacy EC2 automation (`trigger_github_on_ec2_approved`) includes a `ref` field matching the branch:

| Branch | `ref` value |
|---|---|
| `dev` | `dev` |
| `qa` | `qa` |
| `main` | `main` |

Verify Port dispatches to the correct branch after changing default branch settings.
