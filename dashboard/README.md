# BannerHealth Home preview (sample data)

This is **not** live Port. The cloud agent’s `http://localhost:4173` only works on **that** VM, not on your laptop.

## Reference dashboard (open this)

Locked Home canvas: Quick view, four KPIs, three pies, then **Quick Actions + Recently viewed** only.

1. Download **Raw** [`dashboard/REFERENCE-DASHBOARD.html`](https://github.com/PriyaRudroju/devportal-self-service/blob/cursor/landing-dashboard-98a0/dashboard/REFERENCE-DASHBOARD.html)
2. Save As → open in Chrome/Edge (double-click; no Python).

Same file: [`OPEN-THIS.html`](https://github.com/PriyaRudroju/devportal-self-service/blob/cursor/landing-dashboard-98a0/dashboard/OPEN-THIS.html). In `tfc_port_configuration`, copy `dropin/tfc_port_configuration/REFERENCE-DASHBOARD.html`.

## Optional: Python server (your PC)

In **PowerShell**, from the folder that contains `index.html`:

```powershell
cd path\to\devportal-self-service\dashboard
py -m http.server 4173
```

If `py` fails:

```powershell
python -m http.server 4173
```

Then open **http://127.0.0.1:4173/** (not the agent chat URL).

Sample KPIs: Provisioned EC2 **3**, Provisioned S3 **2**, Failed runs **2**, Completed Tasks **3**. Next to Quick Actions: **Recently viewed** only (no EC2/S3/Jira tables).
