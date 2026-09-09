# Landing dashboard

Port `$home` page for BannerHealth - Dev. Layout matches Port’s [dashboard page / Plan my day](https://docs.port.io/interface-builder/port-interface/page/dashboard-page/) pattern.

**GitOps source of truth:** `BHGitOps/tfc_port_configuration/pages-home.tf` (Terraform `port_page`). Not `port_orchestration_repo` and not this demo org.

## What shipped in this PR

| Path | Purpose |
|---|---|
| [`port/pages/home.json`](../port/pages/home.json) | Widget **payload** copied into the Terraform drop-in (do not apply to this demo org) |
| [`dropin/tfc_port_configuration/pages-home.tf`](../dropin/tfc_port_configuration/pages-home.tf) | Copy to `tfc_port_configuration` root as `port_page` `$home` |
| [`dropin/tfc_port_configuration/IDENTIFIERS.md`](../dropin/tfc_port_configuration/IDENTIFIERS.md) | Grep checklist for live blueprint/action ids |
| [`dropin/tfc_port_configuration/APPLY.md`](../dropin/tfc_port_configuration/APPLY.md) | Import `$home` → TFC apply **dev**, QA, then **qa** / **prod** |
| [`port/resources/service.json`](../port/resources/service.json) | Parent service blueprint with owner / team (demo org only) |
| [`port/resources/s3-bucket.json`](../port/resources/s3-bucket.json) | Relations: service, owningTeam, owner (demo org only) |
| [`port/resources/ec2-change-request.json`](../port/resources/ec2-change-request.json) | Same relations (demo org only) |
| [`docs/BLUEPRINT_INVENTORY.md`](BLUEPRINT_INVENTORY.md) | Identifier map |
| [`dashboard/`](../dashboard/) | Local preview of the same layout (pies + filters) |

Pages are **opt-in** in this demo repo. Default `apply_port_config.py` still applies blueprints/actions/automations/workflows only.

## Local preview

Open [`dashboard/REFERENCE-DASHBOARD.html`](../dashboard/REFERENCE-DASHBOARD.html) (or Raw on GitHub) for the locked Home canvas. Sample data; after the pies: Quick Actions + Recently viewed only. No catalog tables. Sidebar folders match live BannerHealth Dev and are not managed by `$home`.

```bash
cd dashboard
python3 -m http.server 4173
```

Open http://localhost:4173

## Apply to BannerHealth (`tfc_port_configuration`)

1. Grep identifiers in `tfc_port_configuration` (`IDENTIFIERS.md` / `extract_identifiers.sh`).
2. Copy `dropin/tfc_port_configuration/pages-home.tf` to that repo’s **root**. Remap `locals`.
3. `terraform import 'port_page.home' '$home'` in the **dev** TFC workspace.
4. Set `PORT_BETA_FEATURES_ENABLED=true` if the provider still gates pages.
5. TFC apply **dev**. QA Home: pies (empty OK), three action cards, Recently viewed. No catalog tables.
6. TFC apply **qa**, then **prod**.

Leave `port_orchestration_repo` unchanged for v1 (no `port-configs/pages/home.json`).

Do **not** apply `home.json` to `org_NaOn60IA22iSZcWo` (this repo’s prod).

## Widget map

- Number charts: provisioned EC2, provisioned S3, failed GitHub runs, completed Jira
- Pies: EC2 by `provisioning_status` (resource=ec2), S3 by `provisioning_status` (resource=s3), GitHub runs by `conclusion`
- Quick view: Self-service hub, Self Service Infra Resources, GitHub Workflow Runs, Users
- Quick Actions: three action cards only (EC2 / S3 / Feedback)
- Recently viewed entities (Port personal widget). No catalog tables on Home.
- Sidebar and Dev/QA/Prod org switcher are unchanged
