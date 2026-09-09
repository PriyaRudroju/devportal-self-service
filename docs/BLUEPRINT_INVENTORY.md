# Blueprint and action inventory (landing dashboard)

`BHGitOps/port_orchestration_repo` and `BHGitOps/tfc_port_configuration` are not readable from this environment (GitHub 404). Identifiers below are taken from:

- The live BannerHealth - Dev catalog sidebar
- Port Ocean defaults (`githubWorkflowRun`, `jiraIssue`)
- This repo’s GitOps blueprints (`s3Bucket`, `ec2ChangeRequest`)

When copying [`dropin/tfc_port_configuration/pages-home.tf`](../dropin/tfc_port_configuration/pages-home.tf) into `tfc_port_configuration`, replace any local that does not match `blueprints-*.tf` / `*-action.tf` / `feedback.tf`. See [`dropin/tfc_port_configuration/IDENTIFIERS.md`](../dropin/tfc_port_configuration/IDENTIFIERS.md).

Do **not** copy [`port/pages/home.json`](../port/pages/home.json) into `port_orchestration_repo` as a second `$home` source.

## Tables (blueprints) used on Home

| UI title (sidebar) | JSON identifier used in `home.json` / `pages-home.tf` | Status property for pies / KPIs | Source |
|---|---|---|---|
| Terraform-managed EC2 | `terraformManagedEc2` | `status` (confirm; may be `state`) | BannerHealth catalog — **must grep** `blueprints-terraform-cloud.tf` |
| GitHub Workflow Runs | `githubWorkflowRun` | pie: `conclusion`; failed KPI: `conclusion = failure` | Port GitHub Ocean default — confirm `blueprints-github.tf` |
| Jira Issue | `jiraIssue` | `status` (`!= Done` for open KPI) | Port Jira default — confirm `blueprints-jira.tf` |
| S3 Bucket | `s3Bucket` | `status` | this repo — not a v1 home widget |
| EC2 Change Request | `ec2ChangeRequest` | `approvalStatus` / `executionStatus` | this repo — pattern only |
| Service (proposed parent) | `service` | `environment` | [`port/resources/service.json`](../port/resources/service.json) — do not add a second Service blueprint in TFC if `blueprint-self-service.tf` already has one |
| User / Team | `_user` / `_team` | n/a | Port built-in; My entities + Owning teams filter |

## Filters (TFC + Port)

| Filter | Port mechanism | Expected values |
|---|---|---|
| Owning teams | Dashboard basic property (includes **My Teams**) | Port `$team` — needs blueprint `ownership { type = "Direct" }` (or equivalent) on Terraform-managed EC2 |
| Environment | Blueprint property `environment` on EC2 / service | Align with TFC workspace tags in `tfc_port_configuration` (`dev` / `qa` / `prod` unless that repo uses different names) |

## Self-service actions (replace dead widgets)

| UI title | Identifier in this demo `home.json` | Confirm in TFC |
|---|---|---|
| Provision EC2 Instance | `provision_ec2_request` | `ec2-action.tf` (drop-in default `create_ec2`; set `""` if absent) |
| Create S3 Bucket | `provision_s3_bucket` | `s3-action.tf` (drop-in default `create_s3`) |
| Submit Feedback | `submit_feedback` | `feedback.tf` |

If an action identifier 404s, remove it from the action-card widget (`local.home_action_* = ""`) rather than shipping another “action no longer exists” card.

## Phase-two (not on v1 home)

ECR Repositories, EKS Clusters, RDS, KMS Keys, S3 Bucket Policies, Classic Load Balancers, Security Groups, Subnets — present in the BannerHealth sidebar, not wired as home widgets.
