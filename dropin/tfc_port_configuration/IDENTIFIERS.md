# Identifier checklist (`tfc_port_configuration`)

This Cursor environment still cannot clone `BHGitOps/tfc_port_configuration` (GitHub 404). Values below mix **Port official defaults** (safe to keep unless that `.tf` file uses a custom id) with **placeholders you must grep on `main`**.

Do not guess action ids in the BHGitOps PR. If an id is not in `*-action.tf` / `feedback.tf`, set that local to `""` so the card is omitted.

## Confirmed from Port docs (still grep the `.tf` files)

| Confirm in file | What to copy into `pages-home.tf` locals | Default in drop-in | Why this default |
|---|---|---|---|
| `blueprints-github.tf` | GitHub workflow run blueprint + conclusion property | `githubWorkflowRun`, `conclusion`, failed = `failure` | [Port GitHub Ocean](https://docs.port.io/context-lake/ingestion/ingest-data-into-port/native-integrations/git/github-ocean/examples/) — matches BannerHealth sidebar title **GitHub Workflow Runs** |
| `blueprints-jira.tf` | Jira issue blueprint + status property | `jiraIssue`, `status`, completed = `Done` | Home KPI is **Completed Tasks** (`status = Done`), not open issues. |

## Must grep (do not treat as live BannerHealth ids)

| Confirm in file | What to copy into `pages-home.tf` locals | Default in drop-in | Why this default |
|---|---|---|---|
| `blueprint-self-service.tf` | Self-service infra blueprint + resource + provisioning_status | `selfServiceInfraResources`, `resource` = `ec2`/`s3`, `provisioning_status` = `provisioned` | Home KPIs/pies are **provisioned** real-time counts. Do not add catalog tables on Home. Confirm the property name if live uses `approval_status`. |
| `ec2-action.tf` / `variables.tf` | EC2 create action id | `create_ec2_instance` or `var.ec2_instance_create_action_identifier` | Set `""` if missing. |
| `s3-action.tf` / `variables.tf` | S3 create action id | `create_s3_bucket` or `var.s3_bucket_create_action_identifier` | Use the standard create action, not admin/policy. |
| `feedback.tf` / `variables.tf` | Submit Feedback action id | `submit_feedback` or `var.feedback_action_identifier` | Confirm the identifier. |
| `environments/dev/`, `qa/`, `prod/` | TFC workspace that applies Port for that env | apply Home via those workspaces | Home is one `port_page`; each env workspace applies it to that Port organization. |
| `versions.tf` / `providers.tf` | Port provider version + beta flag | `PORT_BETA_FEATURES_ENABLED=true` if `port_page` is gated | Provider docs: pages are beta. |

```bash
# From the root of tfc_port_configuration (or pass the path to the helper):
./dropin/tfc_port_configuration/extract_identifiers.sh /path/to/tfc_port_configuration

# Or by hand:
rg -n "identifier|title" blueprints-terraform-cloud.tf blueprints-github.tf blueprints-jira.tf
rg -n "identifier|title" ec2-action.tf s3-action.tf feedback.tf
rg -n "port_environment|PORT_BETA" environments/dev environments/qa environments/prod versions.tf providers.tf
```
