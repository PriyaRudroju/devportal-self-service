# Landing dashboard

Port `$home` page for BannerHealth - Dev. Layout matches Port’s [dashboard page / Plan my day](https://docs.port.io/interface-builder/port-interface/page/dashboard-page/) pattern.

## What shipped in this PR

| Path | Purpose |
|---|---|
| [`port/pages/home.json`](../port/pages/home.json) | `$home` widgets: 4 KPIs, 3 pies, quick view, personal widgets, 2 tables |
| [`port/resources/service.json`](../port/resources/service.json) | Parent service blueprint with owner / team |
| [`port/resources/s3-bucket.json`](../port/resources/s3-bucket.json) | Relations: service, owningTeam, owner |
| [`port/resources/ec2-change-request.json`](../port/resources/ec2-change-request.json) | Same relations |
| [`docs/BLUEPRINT_INVENTORY.md`](BLUEPRINT_INVENTORY.md) | Identifier map (orchestration repo was not readable from CI) |
| [`dashboard/`](../dashboard/) | Local preview of the same layout (pies + filters) |

Pages are **opt-in**. Default `apply_port_config.py` still applies blueprints/actions/automations/workflows only, so this demo org is not overwritten with BannerHealth `$home`.

## Local preview

```bash
cd dashboard
python3 -m http.server 4173
```

Open http://localhost:4173

## Apply to BannerHealth Dev (orchestration GitOps)

`BHGitOps/port_orchestration_repo` is the apply target. After identifiers are confirmed:

1. Copy `port/pages/home.json` into that repo.
2. Remap any blueprint/action id listed in the inventory.
3. Apply pages with BannerHealth Port client credentials (`--resources pages`).
4. QA on Dev: pie empty states, My Teams filter, action cards resolve (no “action no longer exists”).
5. Promote with that repo’s branch model (typically dev → qa → main).

Do **not** apply `home.json` to `org_NaOn60IA22iSZcWo` (this repo’s prod).

## Widget map

- Number charts: pending EC2, TFC EC2 total, failed GitHub runs, open Jira
- Pies: EC2 by `status`, GitHub runs by `conclusion`, Jira by `status`
- Quick view: links + action cards (`provision_ec2_request`, `provision_s3_bucket`, `submit_feedback`)
- Personal: my-entities, recently-viewed, recently-used-actions
- Tables: terraformManagedEc2, githubWorkflowRun
- Filters: Owning teams, Environment
