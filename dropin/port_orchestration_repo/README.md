# port_orchestration_repo — v1 Home dashboard

No `$home` (or `port-configs/pages/`) change for v1.

This repo owns self-service JSON under `port-configs/` (`ec2`, `s3`, `kms`, `ebs`, `loadbalancer`, `secretsmanager`, …). The Port Home canvas is owned by `tfc_port_configuration/pages-home.tf`.

Only edit a blueprint JSON here later if Dev QA shows a missing `environment` or `owningTeam` property that Terraform does not define.

Optional README sentence for this repo:

> Port Home (`$home`) is managed in `BHGitOps/tfc_port_configuration` (`pages-home.tf`), not in `port-configs/`.
