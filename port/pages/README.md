# BannerHealth `$home` page (do not apply to this demo org by default)

[`home.json`](home.json) is the Port **home** page **payload** for BannerHealth (`org_VqQnsk9IJrhyJ9mA`). Copy it into Terraform, not into `port_orchestration_repo`.

This GitHub repo (`PriyaRudroju/devportal-self-service`) deploys to a **different** Port org. CI must **not** apply pages unless you pass `--resources pages` with BannerHealth credentials.

## Copy into `tfc_port_configuration`

1. Confirm blueprint and action identifiers against [`docs/BLUEPRINT_INVENTORY.md`](../../docs/BLUEPRINT_INVENTORY.md) and [`dropin/tfc_port_configuration/IDENTIFIERS.md`](../../dropin/tfc_port_configuration/IDENTIFIERS.md).
2. Copy [`dropin/tfc_port_configuration/pages-home.tf`](../../dropin/tfc_port_configuration/pages-home.tf) to the **root** of `BHGitOps/tfc_port_configuration` (next to `blueprints-github.tf`). Widget JSON already matches this `home.json`.
3. Import existing Home, then TFC apply **dev** (see [`dropin/tfc_port_configuration/APPLY.md`](../../dropin/tfc_port_configuration/APPLY.md)):

```bash
terraform import 'port_page.home' '$home'
```

Do **not** add `port-configs/pages/home.json` in `port_orchestration_repo` while Terraform also manages `$home`.
