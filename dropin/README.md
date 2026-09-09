# BHGitOps Home dashboard drop-in

One source of truth for Port `$home`: **`BHGitOps/tfc_port_configuration`**.

Do **not** add `port-configs/pages/home.json` in `port_orchestration_repo` (that would dual-write against Terraform).

| Copy these files into | Path in that repo |
|---|---|
| [`tfc_port_configuration/pages-home.tf`](tfc_port_configuration/pages-home.tf) | **root**, next to `blueprints-github.tf` |
| [`tfc_port_configuration/REFERENCE-DASHBOARD.html`](tfc_port_configuration/REFERENCE-DASHBOARD.html) | optional; double-click locked Home canvas (same file as `home-preview-OPEN-THIS.html`) |
| [`tfc_port_configuration/IDENTIFIERS.md`](tfc_port_configuration/IDENTIFIERS.md) | optional, for the PR description |
| [`tfc_port_configuration/APPLY.md`](tfc_port_configuration/APPLY.md) | optional runbook |

[`port_orchestration_repo/README.md`](port_orchestration_repo/README.md) is a **one-sentence** README addition only. No Home JSON.

Payload source in this demo repo: [`port/pages/home.json`](../port/pages/home.json). Widget ids and layout are already in `pages-home.tf`.
