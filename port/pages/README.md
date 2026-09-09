# BannerHealth `$home` page (do not apply to this demo org by default)

[`home.json`](home.json) is the Port **home** page payload for BannerHealth (`org_VqQnsk9IJrhyJ9mA`).

This GitHub repo (`PriyaRudroju/devportal-self-service`) deploys to a **different** Port org. CI must **not** apply pages unless you pass `--resources pages` with BannerHealth credentials.

## Copy into `port_orchestration_repo`

1. Confirm blueprint and action identifiers against [`docs/BLUEPRINT_INVENTORY.md`](../../docs/BLUEPRINT_INVENTORY.md).
2. Copy `home.json` into that repo’s Port pages folder (or paste in Port: Home → `...` → Edit JSON).
3. Apply with BannerHealth Port credentials:

```bash
python scripts/apply_port_config.py --env dev --resources pages
```

(`--env` must match `PORT_ENV` in that repo’s `config.env`.)
