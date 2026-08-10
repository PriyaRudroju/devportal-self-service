# devportal-self-service

Self-service developer portal demos using Port.io, GitHub Actions, Terraform Cloud, AWS, and Microsoft Teams.

## Use cases in this repo

| Use case | Flow |
|---|---|
| **S3 bucket provisioning** | Port → GitHub → Terraform Cloud → AWS S3 → Port catalog |
| **EC2 provisioning with Teams approval** | Port → Lambda → Teams → Lambda → Port automation → GitHub → Terraform Cloud → AWS EC2 → Port catalog |

## Architecture

### S3 provisioning

```
Port.io Self-Service Workflow (form → catalog entity)
  → Port automation trigger_github_on_s3_ready (legacy GitHub app)
  → GitHub Actions (workflow_dispatch on branch from gitRef)
    → Terraform Cloud (remote state + apply)
      → AWS S3 bucket
        → Port.io catalog updated (UPSERT on success)
```

### EC2 provisioning with Teams approval (Lambda-first)

```
Port self-service action (WEBHOOK backend)
  → Lambda POST /ec2/request
      → Port API UPSERT catalog entity (approvalStatus=pending)
      → Teams Workflow HTTP trigger (approval card)
  → Approver clicks Approve/Reject in Teams
      → Lambda GET /approval-decision
      → Port API UPSERT (approved/rejected)
  → Port automation (ENTITY_UPDATED pending→approved)
      → GitHub Actions → Terraform Cloud → AWS EC2
          → Port catalog UPSERT (executionStatus=completed)
```

Approval happens in Teams/Lambda, not Port native approval. GitHub runs only after the catalog entity moves to `approvalStatus=approved`.

## Repository structure

```
.github/workflows/
  provision-s3-bucket.yml              # S3 GitHub workflow
  change-ec2-instance.yml              # EC2 GitHub workflow (post-approval)
  deploy-port-config.yml               # Port GitOps apply (branch-specific trigger)
  validate-port-config.yml             # Port GitOps plan on PR (branch-specific)
lambda/
  teams-approval/                      # Port UPSERT + Teams notification Lambda
port/
  resources/                           # Shared blueprints (all branches)
    s3-bucket.json
    ec2-change-request.json
  environments/                        # ONE environment per Git branch
    config.env                         # PORT_ENV=dev|qa|prod
    workflows/                         # Port Workflows
    actions/                           # Legacy actions (optional)
    automations/                       # Legacy automations (optional)
  PROMOTION.md                         # Three-branch promotion runbook
terraform/
  modules/
    s3-bucket/
    ec2-instance/
    lambda-teams-approval/
  environments/
    dev/                               # S3 (workspace: dev-portal-s3-dev)
    dev-ec2/                           # EC2 (workspace: dev-portal-ec2-dev)
    dev-integration/                   # Lambda + API Gateway
scripts/
  apply_port_config.py                 # Apply Port JSON to single org via API
  load_env_config.sh                   # Source config.env in CI
docs/
  GITHUB_SETUP.md                      # Branch protection and GitHub Environments
```

## Port config GitOps (three-branch: dev → qa → main)

Port configuration lives as JSON in Git. Each **Git branch** maps to one Port environment in the **same Port org** (`org_NaOn60IA22iSZcWo`). **Production (`main`) is the source of truth**; `dev` and `qa` are playgrounds.

**Talking point for stakeholders:**

> Port configuration is JSON in Git. Each branch auto-deploys its environment on push — no manual env selection in CI. Dev and QA are playgrounds; production on main is canonical. Promotion is Git PR flow: dev → qa → main.

### How promotion works

| Stage | What happens |
|---|---|
| Feature work | PR to **`dev`** → validate plans dev → merge applies dev |
| Promote to QA | PR **`dev` → `qa`** → merge applies qa (keep qa `config.env`) |
| Promote to Prod | PR **`qa` → `main`** → merge applies prod (approvers) |

See [`port/PROMOTION.md`](port/PROMOTION.md) and [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md) for the full runbook and GitHub setup.

### GitHub Environment setup (one-time)

Create GitHub Environments: `development`, `qa`, `production` (prod requires reviewers).

| GitHub Environment | Git branch | Variables | Secrets |
|---|---|---|---|
| `development` | `dev` | `API_GATEWAY_URL`, `GITHUB_INSTALLATION_ID`, `TFC_WORKSPACE` | `PORT_CLIENT_ID`, `PORT_CLIENT_SECRET` |
| `qa` | `qa` | QA API URL, QA TFC workspace | Port creds (same or QA-specific) |
| `production` | `main` | Prod API URL, prod TFC workspace | Prod creds + required reviewers |

Example dev values:

| Variable | Example |
|---|---|
| `API_GATEWAY_URL` | `https://fvoyz6jb9i.execute-api.us-east-2.amazonaws.com` |
| `TFC_WORKSPACE` | `dev-portal-s3-dev` |
| `GITHUB_INSTALLATION_ID` | GitHub Ocean app installation ID for this repo |

Variable precedence: `port/environments/config.env` first, then GitHub Environment variables override in CI.

### Local validate and apply

```bash
python scripts/apply_port_config.py --env dev --plan
export PORT_CLIENT_ID=... PORT_CLIENT_SECRET=...
python scripts/apply_port_config.py --env dev
```

Use `--skip-legacy` after migrating fully to Port Workflows. Use `--resources blueprints,workflows` for partial apply.

### CI workflows (per branch)

Each branch contains only its Port GitOps workflows:

| Workflow | Trigger | Purpose |
|---|---|---|
| `validate-port-config.yml` | PR to current branch | Plan this branch's Port env |
| `deploy-port-config.yml` | Push to current branch | Apply this branch's Port env |

| Branch | Deploy trigger | Port env |
|---|---|---|
| `dev` | Push to `dev` | dev |
| `qa` | Push to `qa` | qa |
| `main` | Push to `main` | prod |

## Setup order (recommended)

Complete these in order for the EC2 + Teams flow:

1. Terraform Cloud workspaces and AWS credentials
2. Deploy integration Lambda (`dev-integration`)
3. Create Teams Workflow HTTP trigger (or use browser approve URL for demo)
4. Import Port blueprint, action, and automation
5. Disable old Port automations if already imported
6. Run end-to-end demo

---

## 1. Terraform Cloud

Create organization at [app.terraform.io](https://app.terraform.io) and these **API-driven** workspaces:

| Workspace | Purpose | Required variables |
|---|---|---|
| `dev-portal-s3-dev` | S3 provisioning | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| `dev-portal-ec2-dev` | EC2 provisioning | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| `dev-portal-integration-dev` | Teams approval Lambda | `teams_webhook_url`, `port_client_id`, `port_client_secret` |

Generate a user API token and store in GitHub secrets:

| GitHub secret | Purpose |
|---|---|
| `TF_API_TOKEN` | Terraform Cloud API token |
| `TF_CLOUD_ORGANIZATION` | Terraform Cloud organization name |
| `PORT_CLIENT_ID` | Port.io API client ID |
| `PORT_CLIENT_SECRET` | Port.io API client secret |

### Deploy integration Lambda locally

```bash
cd terraform/environments/dev-integration
export TF_VAR_teams_webhook_url="https://prod-xx.westus.logic.azure.com:443/workflows/..."
export TF_VAR_port_client_id="..."
export TF_VAR_port_client_secret="..."
terraform init
terraform apply
```

Copy the `ec2_request_url` output for the Port action webhook URL.

---

## 2. GitHub

1. Push this repo to `main` (Port reads workflows from the default branch)
2. Add repository secrets listed above
3. Confirm the Port GitHub App has **Actions Read/Write** on this repo

---

## 3. Microsoft Teams (Workflow HTTP trigger)

Many tenants hide **Incoming Webhook / Connectors**. Use a **Teams Workflow** with an **HTTP request trigger** instead.

### Create the workflow

1. Open the target Teams channel → **Workflows** → **Create from blank**
2. Trigger: **When a HTTP request is received**
3. Action: **Post card in chat or channel** with dynamic Approve/Reject links, for example:
   - Approve: `@{triggerBody()?['approve_url']}`
   - Reject: `@{triggerBody()?['reject_url']}`
4. Save the workflow and copy the **HTTP POST URL**
5. Store that URL in Terraform Cloud workspace variable `teams_webhook_url` for `dev-portal-integration-dev`
6. Re-run `terraform apply` if the Lambda was deployed before the URL was set

Lambda sends this JSON body to the workflow (default `TEAMS_PAYLOAD_FORMAT=workflow`):

```json
{
  "runId": "...",
  "instance_name": "...",
  "instance_type": "...",
  "environment": "...",
  "requested_by": "...",
  "port_run_url": "...",
  "approve_url": "https://<api-id>.execute-api.us-east-1.amazonaws.com/approval-decision?runId=...&decision=approve",
  "reject_url": "https://<api-id>.execute-api.us-east-1.amazonaws.com/approval-decision?runId=...&decision=reject"
}
```

### Fallbacks

| Scenario | What to do |
|---|---|
| IT enables Incoming Webhook later | Set `teams_webhook_url` to the connector URL and Lambda env `TEAMS_PAYLOAD_FORMAT=messagecard` |
| No Teams for demo | Open the `approve_url` from Lambda logs or construct `approval_decision_url?runId=<runId>&decision=approve` in a browser |

---

## 4. Port.io

### GitHub data source

**Builder → Sources → GitHub** — install the app on `devportal-self-service`.

### Import blueprint

**Builder → Data model → + Blueprint → Edit JSON**

Paste [`port/resources/ec2-change-request.json`](port/resources/ec2-change-request.json).

### Import self-service action

**Self-service → + Action → Edit JSON**

Paste [`port/environments/actions/change-ec2-instance.json`](port/environments/actions/change-ec2-instance.json) (or apply via `apply_port_config.py` on the `dev` branch).

Replace the webhook URL placeholder:

```json
"url": "https://<api-id>.execute-api.us-east-1.amazonaws.com/ec2/request"
```

Use the `ec2_request_url` output from the integration Terraform apply.

The action backend is **Webhook** (not GitHub). Do **not** enable Port native manual approval on this action.

### Import automation

**Automations → + Automation → Edit JSON**

Import [`port/environments/automations/trigger-github-on-ec2-approved.json`](port/environments/automations/trigger-github-on-ec2-approved.json) and publish it.

---

## 5. Verify S3 flow

1. Run **Provision S3 Bucket** from Port Self-service
2. Confirm the Port workflow run completes (**S3 Request Form** → **Create Ready Catalog Entity**)
3. Confirm automation **Trigger GitHub When S3 Ready** runs (Port → Automations)
4. Check GitHub Actions workflow `Provision S3 Bucket` (branch should match form **Environment**, e.g. `dev`)
5. Check TFC workspace `dev-portal-s3-dev`
6. Confirm bucket in AWS S3 (`us-east-1`)
7. Confirm Port catalog entity with `status: provisioned`

---

## 6. Verify EC2 + Teams flow

1. Run **Provision EC2 Instance** from Port Self-service
2. Confirm Lambda logs show Port UPSERT pending + Teams POST
3. Confirm catalog entity with `approvalStatus=pending`, `executionStatus=not_started`
4. Confirm Teams card appears in the channel (or use browser approve URL)
5. Click **Approve** in Teams
6. Confirm catalog entity: `approvalStatus=approved`, `executionStatus=in_progress`
7. Confirm Port automation `Trigger GitHub When EC2 Approved` runs
8. Confirm GitHub workflow `Provision EC2 Instance` starts
9. Confirm TFC workspace `dev-portal-ec2-dev` apply succeeds
10. Confirm EC2 instance in AWS console
11. Confirm catalog entity: `approvalStatus=approved`, `executionStatus=completed`, `instanceId` populated

Reject path:

1. Click **Reject** in Teams (or `decision=reject` in browser)
2. Catalog entity: `approvalStatus=rejected`, `executionStatus=failed`
3. GitHub workflow should **not** start

### Demo script

> When a developer submits the EC2 self-service form, Port calls our Lambda. Lambda creates a catalog row with status pending and posts a Teams approval card. When the approver clicks Approve, Lambda updates the catalog to approved. That entity update triggers a Port automation which starts the GitHub Actions workflow. GitHub runs Terraform, provisions EC2, and updates the catalog to completed.

---

## Local development

### S3

```bash
cd terraform/environments/dev
export TF_CLOUD_ORGANIZATION="your-org-name"
terraform init
terraform plan -var="bucket_name=my-test-bucket-12345"
```

### EC2

```bash
cd terraform/environments/dev-ec2
export TF_CLOUD_ORGANIZATION="your-org-name"
terraform init
terraform plan \
  -var="instance_name=devportal-demo-ec2" \
  -var="instance_type=t3.micro"
```

---

## Troubleshooting

| Symptom | Where to look | Likely cause |
|---|---|---|
| Port run succeeds but no catalog entity | Lambda CloudWatch logs | Port credentials missing or UPSERT failed |
| No Teams card | CloudWatch `/aws/lambda/devportal-teams-approval` | Invalid `teams_webhook_url` or workflow not published |
| Approve click does nothing | API Gateway + Lambda logs | Wrong `approve_url` in workflow card |
| Approved but GitHub not started | Port automations | `trigger_github_on_ec2_approved` not published or entity did not transition pending→approved |
| GitHub Terraform init fails | GitHub Actions logs | `TF_API_TOKEN` or workspace name mismatch |
| Terraform apply fails | TFC run logs | AWS credentials or IAM permissions |
| Catalog missing `instanceId` | GitHub `Capture Terraform outputs` step | Apply failed or output step skipped |
| Old automations still firing | Port automations list | Disable deprecated automations from prior setup |

---

## Status fields (EC2 catalog)

| Field | Set when | Values |
|---|---|---|
| `approvalStatus` | Lambda on request / approve / reject | `pending`, `approved`, `rejected` |
| `executionStatus` | Lambda on approve/reject + GitHub workflow | `not_started`, `in_progress`, `completed`, `failed` |

Lambda sets `executionStatus=in_progress` on approve. GitHub sets `executionStatus=completed` only after Terraform apply succeeds.

---

## Extending

- Add Jira ticket creation/update on run start/end
- Add in-place EC2 resize for existing instance IDs
- Add S3 hardening (encryption, public access block)
- Add destroy/deprovision self-service actions
