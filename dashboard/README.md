# BannerHealth Home preview (sample data)

This is **not** live Port. The cloud agent’s `http://localhost:4173` only works on **that** VM, not on your laptop.

## Easiest: no server

1. Pull this repo / this branch (`cursor/landing-dashboard-98a0`).
2. Double-click **`dashboard/OPEN-THIS.html`**.
3. If the file is in `tfc_port_configuration`, use **`home-preview-OPEN-THIS.html`** (copy from `dropin/tfc_port_configuration/`).

GitHub: download  
https://github.com/PriyaRudroju/devportal-self-service/blob/cursor/landing-dashboard-98a0/dashboard/OPEN-THIS.html  
→ **Raw** → Save As → open in Chrome/Edge.

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

Sample KPIs: Provisioned EC2 **3**, Provisioned S3 **2**, Failed runs **2**, Completed Tasks **3**. Below Quick Actions: **Recently viewed** only (no EC2/S3/Jira tables).
