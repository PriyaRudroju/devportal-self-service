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

[`dashboard/`](../dashboard/) is a **sample-data** stand-in of the Home canvas (pending EC2/S3, failed runs, completed Jira). It does not apply to Port. Sidebar folders match live BannerHealth Dev and are not managed by `$home`.

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
5. TFC apply **dev**. QA Home: pies (empty OK), working action cards, My Teams, tables.
6. TFC apply **qa**, then **prod**.

Leave `port_orchestration_repo` unchanged for v1 (no `port-configs/pages/home.json`).

Do **not** apply `home.json` to `org_NaOn60IA22iSZcWo` (this repo’s prod).

## Widget map

- Number charts: pending EC2, TFC EC2 total, failed GitHub runs, open Jira
- Pies: EC2 by `status`, GitHub runs by `conclusion`, Jira by `status`
- Quick view: links + action cards (ids from `ec2-action.tf` / `s3-action.tf` / `feedback.tf`; omit any id that is not in those files)
- Personal: my-entities, recently-viewed, recently-used-actions
- Tables: Terraform-managed EC2, GitHub Workflow Runs
- Filters: Owning teams, Environment
