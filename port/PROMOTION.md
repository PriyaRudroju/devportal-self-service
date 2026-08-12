# Port Config Promotion Runbook (Three-Branch Model)

Single Port org (`org_NaOn60IA22iSZcWo`), one GitHub repo (`PriyaRudroju/devportal-self-service`). Each **Git branch** maps to one Port environment. **Production (`main`) is the source of truth**; `dev` and `qa` are playgrounds.

## Folder layout (per branch)

Each branch contains the same structure; only the environment slice differs:

```
port/
  resources/                 # Shared blueprints (merged across branches)
    ec2-change-request.json
    s3-bucket.json
  environments/              # ONE environment per branch (flat, no dev|qa|prod subfolders)
    config.env               # PORT_ENV=dev|qa|prod
    actions/
    automations/
    workflows/
```

## Git branch → Port environment

| Git branch | `PORT_ENV` | GitHub Environment | Deploy trigger |
|---|---|---|---|
| `dev` | dev | `development` | Push to `dev` |
| `qa` | qa | `qa` | Push to `qa` |
| `main` | prod | `production` | Push to `main` |

Each branch contains **only** its Port deploy and validate workflows (no manual env picker, no promote workflow).

## Variable precedence

1. Values in `port/environments/config.env`
2. GitHub Environment variables override in CI (`API_GATEWAY_URL`, `TFC_WORKSPACE`, `FEATURE_GIT_REFS`, etc.)

## Git Branch dropdown (`config.env`)

Port self-service forms expose a **Git Branch** field (not AWS environment). Values are built at apply time:

| Variable | Purpose |
|---|---|
| `GIT_REF_DEFAULT` | Stable branch shown first (e.g. `dev`) |
| `FEATURE_GIT_REFS` | Comma-separated feature branches for testing (empty on stable `dev`) |

`scripts/apply_port_config.py` substitutes `{{GIT_REF_ENUM}}` into workflow/action JSON.

| Git branch | `GIT_REF_DEFAULT` | `FEATURE_GIT_REFS` | Port dropdown |
|---|---|---|---|
| `dev` | `dev` | empty | `dev` only |
| `feature/*` (push `port/**`) | `dev` | CI injects current branch | `dev` + feature branch |
| `qa` | `qa` | **must stay empty** | `qa` only |
| `main` | `main` | **must stay empty** | `main` only |

When promoting `dev → qa → main`, do **not** merge `FEATURE_GIT_REFS` values into qa/main `config.env`.

### Feature branch testing workflow

1. `git checkout -b feature/my-test dev`
2. Edit `port/**` if needed; push to origin
3. **Deploy Port Config** runs on `feature/**` and injects `FEATURE_GIT_REFS=feature/my-test`
4. Port form shows **Git Branch**: `dev` (stable) and `feature/my-test` (testing — see field description)
5. Selecting `dev` dispatches GitHub on `dev`; selecting the feature branch dispatches on that ref. Terraform still uses dev infrastructure.
6. After merge to `dev`, push `dev` with `FEATURE_GIT_REFS` empty to reset the dropdown.

## Day-to-day: change Port config in dev

1. Create a feature branch from `dev`.
2. Edit JSON under `port/resources/` (shared) or `port/environments/` (env-specific).
3. Validate locally:
   ```bash
   python scripts/apply_port_config.py --env dev --plan
   ```
4. Open PR → **target `dev`** → `validate-port-config.yml` runs `--plan` for dev.
5. Merge to `dev` → `deploy-port-config.yml` applies **dev** to Port automatically.

## Promote dev → qa → main (Git PRs, not manual workflow)

```text
feature branch  →  PR to dev   →  push applies Port dev
dev branch      →  PR to qa    →  push applies Port qa
qa branch       →  PR to main  →  push applies Port prod (approvers)
```

### PR rules

1. **Feature → `dev`:** Edit shared resources and dev environment JSON.
2. **`dev` → `qa`:** Merge shared resource changes. Keep qa-specific `config.env` and env enums. **Do not merge** `.github/workflows/` from dev — qa branch keeps its own workflow triggers (`branches: [qa]`).
3. **`qa` → `main`:** Same for prod; require production approvers on the PR and/or GitHub Environment.

### Workflow files differ by branch

`deploy-port-config.yml` and `validate-port-config.yml` have **branch-specific triggers** by design. When promoting via PR, exclude workflow files from the merge or resolve conflicts to keep the target branch's triggers.

## GitHub Environment setup (one-time)

Create environments: `development`, `qa`, `production`.

| Environment | Variables | Secrets |
|---|---|---|
| `development` | `API_GATEWAY_URL`, `GITHUB_INSTALLATION_ID`, `TFC_WORKSPACE` | `PORT_CLIENT_ID`, `PORT_CLIENT_SECRET` |
| `qa` | QA-specific URLs/workspace | Port creds (same or QA-specific) |
| `production` | Prod URLs/workspace | Prod creds + **required reviewers** |

See [`docs/GITHUB_SETUP.md`](../docs/GITHUB_SETUP.md) for branch protection and default branch configuration.

## Demo script for stakeholders

> Port configuration is JSON in Git. Dev and QA are playgrounds on the `dev` and `qa` branches; production on `main` is the source of truth. Merging to each branch auto-applies that environment to our Port org — no manual env selection in CI. Promotion is Git PR flow: dev → qa → main.

## Troubleshooting

| Issue | Fix |
|---|---|
| `--plan` fails on `REPLACE_` | Set real values in `config.env` or export env vars before apply |
| `PORT_ENV` mismatch | `--env` must match `PORT_ENV` in `config.env` on this branch |
| Deploy workflow skips | Push must touch `port/**` on `dev` or `feature/**`, or run workflow manually |
| Feature branch missing in Port dropdown | Push `port/**` on the feature branch so Deploy Port Config injects `FEATURE_GIT_REFS` | 
| Wrong API URL in Port | Check GitHub Environment variable for that env |
| EC2 workflow runs wrong branch | Automation `ref` must match branch (`dev`, `qa`, `main`) |
| S3 workflow runs on **`main`** instead of selected Git Branch | S3 automation must read `gitRef` from **`diff.before.properties.gitRef`** (not `diff.after`); re-apply Port config. Run `python scripts/verify_s3_github_ref.py --check-live` |
| S3 GitHub dispatch never starts | Mark-ready must use **external** Port API (Lambda `POST /s3/mark-ready` or E2E PATCH) so `ENTITY_UPDATED` fires; workflow-internal PATCH does not trigger legacy automations |
| 409 on create | Normal — script retries with PUT/PATCH update |
