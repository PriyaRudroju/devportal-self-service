# Apply `$home` from BHGitOps/tfc_port_configuration

This folder is a **drop-in**. Copy files into `BHGitOps/tfc_port_configuration`; do not merge them into this demo org as BannerHealth GitOps.

`port_orchestration_repo` gets **no** `$home` file for v1.

This Cursor environment cannot clone `BHGitOps/*` or run TFC workspaces. After you copy `pages-home.tf` onto a branch in that repo, TFC applies as below.

## If Home still shows four catalog tables

Those cards come from **`pages-home.tf` in `tfc_port_configuration`**, not from this demo repo. Paste this into Copilot **in that repo**:

```text
Edit pages-home.tf (port_page.home / $home) only. Do not change the Organization sidebar or the BannerHealth Dev/QA/Prod org switcher.

DELETE every table-entities-explorer widget, including these titles if present:
- Provisioned EC2 Resources
- Provisioned S3 Resources
- Recent Failed Workflow Runs
- Recently Completed Tasks

After the three pie charts, the last layout row must be exactly:
- quickActions (action-card-widget, size 5) — Create EC2, Create S3, Submit Feedback
- recentlyViewed (recently-viewed-entities, size 7)

Do not add my-entities, recently-used-actions, owning-teams filters, or any other tables.
Keep Quick view links, the four number charts, and the three pies.
Copy widget JSON from PriyaRudroju/devportal-self-service dropin/tfc_port_configuration/pages-home.tf if unsure.
Do not put # comments inside jsonencode.
```

## Step 1 — Read identifiers

On `main` of `tfc_port_configuration`:

```bash
./extract_identifiers.sh .
# or:
rg -n "identifier|title" blueprints-terraform-cloud.tf blueprints-github.tf blueprints-jira.tf
rg -n "identifier|title" ec2-action.tf s3-action.tf feedback.tf
```

Edit `locals` at the top of `pages-home.tf` so they match. If an action id does not exist, set that local to `""` so the card is omitted (avoids “action no longer exists”).

Confirm status property names (pie `property#...` and KPI filters). If Terraform-managed EC2 uses `state` instead of `status`, change `home_ec2_status_property`.

## Step 2 — Copy file

Copy `pages-home.tf` to the **repo root** (same directory as `blueprints-github.tf`).

Do not put it under `environments/dev|qa|prod` unless that is how other Port resources are wired. Home is one `port_page`; each env workspace applies it to that Port environment.

Do not copy `port-configs/` JSON into this repo. Do not add a second Service / EC2 blueprint.

## Step 3 — Provider / beta flag

In TFC workspace variables for **dev** (then qa, prod), if apply fails on `port_page`:

```text
PORT_BETA_FEATURES_ENABLED=true
```

Check `versions.tf` / `providers.tf` for the Port provider version.

## Step 4 — Import existing Home

From the workspace that matches BannerHealth Dev (`environments/dev`). Port’s provider docs require escaping `$` in some shells:

```bash
terraform import 'port_page.home' '$home'
# equivalent:
terraform import port_page.home "\$home"
terraform plan
```

If the resource address in this file changes, use that address in `import`.

First apply must **import**, not create — there is already one Home page per Port org.

## Step 5 — Apply order

1. Branch from `main` in `tfc_port_configuration` (name it however that repo’s process requires).
2. PR → merge per their process.
3. TFC workspace for **dev** (`environments/dev`) applies first.
4. Open https://app.us.getport.io/org_VqQnsk9IJrhyJ9mA/organization/home
   - pies render or show empty state (empty is OK in Dev)
   - Quick Actions has three buttons only (Create EC2 / Create S3 / Submit Feedback)
   - next to Quick Actions: **Recently viewed entities** only
   - **no** catalog tables: Provisioned EC2 Resources, Provisioned S3 Resources, Recent Failed Workflow Runs, Recently Completed Tasks
5. TFC **qa** apply (`environments/qa`).
6. TFC **prod** apply (`environments/prod`).

If Owning teams / My entities do nothing for Terraform-managed EC2 after Dev QA, then — and only then — paste from `relations-owning-team.tf.example` into the **existing** EC2 blueprint file. Prefer native `ownership { type = "Direct" }` over a custom `owningTeam` relation.

## port_orchestration_repo

No file changes for v1. Do not add `port-configs/pages/home.json`.
