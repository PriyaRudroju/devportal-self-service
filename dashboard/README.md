# BannerHealth Home preview (sample data)

Static stand-in for the `$home` canvas in `tfc_port_configuration/pages-home.tf`.

**Not live Port.** Counts, pies, and tables are fake so you can confirm layout. The sidebar copies BannerHealth Dev Organization folders and is not managed by Terraform.

```bash
cd dashboard
python3 -m http.server 4173
```

Open http://localhost:4173

| Widget | Sample numbers |
|---|---|
| Provisioned EC2 | 3 |
| Provisioned S3 | 2 |
| Failed Workflow Runs | 2 |
| Completed Tasks (Jira Done) | 3 |

Quick Actions is three buttons only. Provisioned EC2/S3 tables sit **below** that row.

The Dev / QA / Prod control only changes the greeting in this preview.
