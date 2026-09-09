# BannerHealth Home preview (sample data)

Static stand-in for the `$home` canvas in `tfc_port_configuration/pages-home.tf`.

**Not live Port.** Counts, pies, and tables are fake so you can confirm layout. The sidebar copies BannerHealth Dev Organization folders and does not change in Terraform.

```bash
cd dashboard
python3 -m http.server 4173
```

Open http://localhost:4173

| Widget | Sample numbers in this preview |
|---|---|
| Pending EC2 Requests | 3 |
| Pending S3 Requests | 2 |
| Failed Workflow Runs | 2 |
| Completed Tasks (Jira Done) | 3 |

The Dev / QA / Prod control at the top of the sidebar is the org switcher. In this preview it only changes the greeting label.
