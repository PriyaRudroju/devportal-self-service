# Identifier checklist (`tfc_port_configuration`)

This Cursor environment still cannot clone `BHGitOps/tfc_port_configuration` (GitHub 404). Values below mix **Port official defaults** (safe to keep unless that `.tf` file uses a custom id) with **placeholders you must grep on `main`**.

Do not guess action ids in the BHGitOps PR. If an id is not in `*-action.tf` / `feedback.tf`, set that local to `""` so the card is omitted.

## Confirmed from Port docs (still grep the `.tf` files)

| Confirm in file | What to copy into `pages-home.tf` locals | Default in drop-in | Why this default |
|---|---|---|---|
| `blueprints-github.tf` | GitHub workflow run blueprint + conclusion property | `githubWorkflowRun`, `conclusion`, failed = `failure` | [Port GitHub Ocean](https://docs.port.io/context-lake/ingestion/ingest-data-into-port/native-integrations/git/github-ocean/examples/) — matches BannerHealth sidebar title **GitHub Workflow Runs** |
| `blueprints-jira.tf` | Jira issue blueprint + status property | `jiraIssue`, `status`, open = status `!=` `Done` | [Port Jira](https://docs.port.io/context-lake/ingestion/ingest-data-into-port/native-integrations/project-management/jira/) — matches sidebar **Jira Issue** |

## Must grep (do not treat as live BannerHealth ids)

| Confirm in file | What to copy into `pages-home.tf` locals | Default in drop-in | Why this default |
|---|---|---|---|
| `blueprints-terraform-cloud.tf` | Terraform-managed EC2 blueprint id + status property + pending enum | `terraformManagedEc2`, `status`, `pending` | UI title only. Live catalog also has **EC2 Instances** (`ec2Instance` / `instance_state` in Port AWS docs) — that is a **different** blueprint. If the TFC file uses `state` instead of `status`, change `home_ec2_status_property`. |
| `ec2-action.tf` | EC2 self-service action id | `create_ec2` | Filename only. Demo repo uses `provision_ec2_request`. Set `""` if the identifier is not in this file. |
| `s3-action.tf` | S3 self-service action id | `create_s3` | Filename only. Demo repo uses `provision_s3_bucket`. |
| `feedback.tf` | Submit Feedback action id | `submit_feedback` | Live Home already has a working **Submit Feedback** card; confirm the identifier. |
| `environments/dev/`, `qa/`, `prod/` | TFC workspace that applies Port for that env | apply Home via those workspaces | Plan: “hardcode `port_environment` per env”. Home is one `port_page`; each env workspace applies it to that Port environment. |
| `versions.tf` / `providers.tf` | Port provider version + beta flag | `PORT_BETA_FEATURES_ENABLED=true` on the TFC workspace if `port_page` is gated | Provider docs: pages are beta. |

```bash
# From the root of tfc_port_configuration (or pass the path to the helper):
./dropin/tfc_port_configuration/extract_identifiers.sh /path/to/tfc_port_configuration

# Or by hand:
rg -n "identifier|title" blueprints-terraform-cloud.tf blueprints-github.tf blueprints-jira.tf
rg -n "identifier|title" ec2-action.tf s3-action.tf feedback.tf
rg -n "port_environment|PORT_BETA" environments/dev environments/qa environments/prod versions.tf providers.tf
```
