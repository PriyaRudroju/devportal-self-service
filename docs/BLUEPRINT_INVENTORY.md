# Blueprint and action inventory (landing dashboard)

`BHGitOps/port_orchestration_repo` and `BHGitOps/tfc_port_configuration` are not readable from this environment (GitHub 404). Identifiers below are taken from:

- The live BannerHealth - Dev catalog sidebar
- Port Ocean defaults (`githubWorkflowRun`, `jiraIssue`)
- This repo’s GitOps blueprints (`s3Bucket`, `ec2ChangeRequest`)

When copying [`port/pages/home.json`](../port/pages/home.json) into `port_orchestration_repo`, replace any identifier that does not match the live org.

## Tables (blueprints) used on Home

| UI title (sidebar) | JSON identifier used in `home.json` | Status property for pies / KPIs | Source |
|---|---|---|---|
| Terraform-managed EC2 | `terraformManagedEc2` | `status` | BannerHealth catalog (confirm in orchestration repo) |
| GitHub Workflow Runs | `githubWorkflowRun` | pie: `conclusion`; failed KPI: `conclusion = failure` | Port GitHub Ocean default |
| Jira Issue | `jiraIssue` | `status` | Port Jira integration default |
| S3 Bucket | `s3Bucket` | `status` | this repo — not a v1 home widget |
| EC2 Change Request | `ec2ChangeRequest` | `approvalStatus` / `executionStatus` | this repo — pattern only |
| Service (proposed parent) | `service` | `environment` | [`port/resources/service.json`](../port/resources/service.json) |
| User / Team | `_user` / `_team` | n/a | Port built-in; My entities + Owning teams filter |

## Filters (TFC + Port)

| Filter | Port mechanism | Expected values |
|---|---|---|
| Owning teams | Dashboard basic property (includes **My Teams**) | Port `_team` |
| Environment | Blueprint property `environment` on EC2 / service | Align with TFC workspace tags in `tfc_port_configuration` (`dev` / `qa` / `prod` unless that repo uses different names) |

## Self-service actions (replace dead widgets)

| UI title | Identifier in `home.json` | Confirm in orchestration repo |
|---|---|---|
| Provision EC2 Instance | `provision_ec2_request` | this repo workflow id |
| Create S3 Bucket | `provision_s3_bucket` | may differ in BannerHealth |
| Submit Feedback | `submit_feedback` | live org already has this action |

If an action identifier 404s, remove it from the action-card widget rather than shipping another “action no longer exists” card.

## Phase-two (not on v1 home)

ECR Repositories, EKS Clusters, RDS, KMS Keys, S3 Bucket Policies, Classic Load Balancers, Security Groups, Subnets — present in the BannerHealth sidebar, not wired as home widgets.
