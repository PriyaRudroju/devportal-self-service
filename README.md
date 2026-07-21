# devportal-self-service

Self-service developer portal demos using Port.io, GitHub Actions, Terraform Cloud, AWS, and Microsoft Teams.

## Use cases in this repo

| Use case | Flow |
|---|---|
| **S3 bucket provisioning** | Port → GitHub → Terraform Cloud → AWS S3 → Port catalog |
| **EC2 provisioning with Teams approval** | Port (approval) → Teams card → Lambda → Port approve → GitHub → Terraform Cloud → AWS EC2 → Port catalog |

## Architecture

### S3 provisioning

```
Port.io Self-Service Action
  → GitHub Actions (workflow_dispatch)
    → Terraform Cloud (remote state + apply)
      → AWS S3 bucket
        → Port.io catalog updated (UPSERT on success)
```

### EC2 provisioning with Teams approval

```
Port self-service (requiredApproval: true)
  → Port automations
      → UPSERT catalog entity (approvalStatus=pending)
      → WEBHOOK → Lambda/API Gateway → Teams approval card
  → Approver clicks Approve/Reject in Teams
      → Lambda → Port approval API
  → Port automations
      → UPSERT catalog entity (approved/rejected)
  → After approval: GitHub Actions → Terraform Cloud → AWS EC2
      → Port catalog UPSERT (executionStatus=completed)
```

## Repository structure

```
.github/workflows/
  provision-s3-bucket.yml              # S3 GitHub workflow
  change-ec2-instance.yml              # EC2 GitHub workflow (post-approval)
lambda/
  teams-approval/                      # Teams + Port approval Lambda source
port/
  blueprints/
    s3-bucket.json
    ec2-change-request.json
  actions/
    provision-s3-bucket.json
    change-ec2-instance.json
  automations/
    upsert-pending-entity-on-run-created.json
    notify-teams-on-approval-request.json
    sync-entity-on-approval-decision.json
terraform/
  modules/
    s3-bucket/
    ec2-instance/
    lambda-teams-approval/
  environments/
    dev/                               # S3 (workspace: dev-portal-s3-dev)
    dev-ec2/                           # EC2 (workspace: dev-portal-ec2-dev)
    dev-integration/                   # Lambda + API Gateway (workspace: dev-portal-integration-dev)
```

## Setup order (recommended)

Complete these in order for the EC2 + Teams flow:

1. Terraform Cloud workspaces and AWS credentials
2. Deploy integration Lambda (`dev-integration`)
3. Wire Port automation webhook URL
4. Import Port blueprint, action, and automations
5. Run end-to-end demo

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
export TF_VAR_teams_webhook_url="https://outlook.office.com/webhook/..."
export TF_VAR_port_client_id="..."
export TF_VAR_port_client_secret="..."
terraform init
terraform apply
```

Copy the `approval_request_url` output.

---

## 2. GitHub

1. Push this repo to `main` (Port reads workflows from the default branch)
2. Add repository secrets listed above
3. Confirm the Port GitHub App has **Actions Read/Write** on this repo

---

## 3. Microsoft Teams

1. Create or choose a channel for approvals
2. Add an **Incoming Webhook** connector
3. Store the webhook URL in Terraform Cloud workspace variable `teams_webhook_url` for `dev-portal-integration-dev`

---

## 4. Port.io

### GitHub data source

**Builder → Sources → GitHub** — install the app on `devportal-self-service`.

### Import blueprint

**Builder → Data model → + Blueprint → Edit JSON**

Paste [`port/blueprints/ec2-change-request.json`](port/blueprints/ec2-change-request.json).

### Import self-service action

**Self-service → + Action → Edit JSON**

Paste [`port/actions/change-ec2-instance.json`](port/actions/change-ec2-instance.json).

Then open the action **Permissions** tab:

- **Enforce manual approval** = Yes
- Add approver users/teams

### Import automations

**Automations → + Automation → Edit JSON**

Import all files from [`port/automations/`](port/automations/).

Before publishing `notify-teams-on-approval-request.json`, replace the webhook URL placeholder:

```json
"url": "https://<api-id>.execute-api.us-east-1.amazonaws.com/teams/approval-request"
```

Use the `approval_request_url` output from the integration Terraform apply.

---

## 5. Verify S3 flow

1. Run **Provision S3 Bucket** from Port Self-service
2. Check GitHub Actions workflow `Provision S3 Bucket`
3. Check TFC workspace `dev-portal-s3-dev`
4. Confirm bucket in AWS S3 (`us-east-1`)
5. Confirm Port catalog entity with `status: provisioned`

---

## 6. Verify EC2 + Teams flow

1. Run **Provision EC2 Instance** from Port Self-service
2. Confirm Port run status = `WAITING_FOR_APPROVAL`
3. Confirm catalog entity with `approvalStatus=pending`
4. Confirm Teams card appears in the channel
5. Click **Approve** in Teams
6. Confirm Port run moves to `IN_PROGRESS`, then GitHub workflow `Provision EC2 Instance` starts
7. Confirm TFC workspace `dev-portal-ec2-dev` apply succeeds
8. Confirm EC2 instance in AWS console
9. Confirm catalog entity: `approvalStatus=approved`, `executionStatus=completed`, `instanceId` populated

Reject path:

1. Click **Reject** in Teams
2. Port run = `DECLINED`
3. Catalog entity: `approvalStatus=rejected`, `executionStatus=failed`
4. GitHub workflow should **not** start

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
| Port run stuck in `WAITING_FOR_APPROVAL` | Port automations + Lambda logs | Teams notify automation URL wrong or Lambda not deployed |
| No Teams card | CloudWatch `/aws/lambda/devportal-teams-approval` | Invalid `teams_webhook_url` |
| Approve click does nothing | API Gateway + Lambda logs | Wrong API URL in card; Port credentials missing on Lambda |
| Approved but GitHub not started | Port run page + action backend | `requiredApproval` not enabled or approval PATCH failed |
| GitHub Terraform init fails | GitHub Actions logs | `TF_API_TOKEN` or workspace name mismatch |
| Terraform apply fails | TFC run logs | AWS credentials or IAM permissions |
| Catalog missing `instanceId` | GitHub `Capture Terraform outputs` step | Apply failed or output step skipped |
| `port_context` parse error | Port action JSON | Must be `{"runId":"..."}` JSON string (EC2 action already uses this format) |

---

## Status fields (EC2 catalog)

| Field | Set when | Values |
|---|---|---|
| `approvalStatus` | Port automations after submit/approve/reject | `pending`, `approved`, `rejected` |
| `executionStatus` | Port automations + GitHub workflow | `not_started`, `in_progress`, `completed`, `failed` |

GitHub sets `executionStatus=completed` only after Terraform apply succeeds.

---

## Extending

- Add Jira ticket creation/update on run start/end
- Add in-place EC2 resize for existing instance IDs
- Add S3 hardening (encryption, public access block)
- Add destroy/deprovision self-service actions
