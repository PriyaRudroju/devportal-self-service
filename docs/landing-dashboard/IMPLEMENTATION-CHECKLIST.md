# Home v1 implementation checklist

Use after the design review. Confirm identifiers in Port: Builder → Data model.

## 1. Count records (drop empty KPIs)

| Catalog table (UI title) | Blueprint identifier (fill in) | Entity count | Use on Home? |
|---|---|---|---|
| EC2 Change Request | `ec2ChangeRequest` | | Pending approvals + pie |
| S3 Bucket | `s3Bucket` | | Needs attention |
| EC2 Instances | | | Active EC2 KPI |
| Terraform-managed EC2 | | | Alternate EC2 KPI if this is the populated table |
| GitHub Workflow Runs | | | Failed runs KPI + 7-day bar |
| GitHub Workflows | | | Link only |
| Dynatrace Problem | | | KPI or swap to Jira |
| Jira Issue | | | Link + optional KPI |
| EKS Clusters | | | Not Home v1 unless count is useful |
| RDS DB Instances | | | Not Home v1 |
| ECR Repositories | | | Not Home v1 |
| Deployments | | | Not Home v1 until related to runs |

## 2. Confirm property keys

| Blueprint | Properties to verify | Enums to verify |
|---|---|---|
| `ec2ChangeRequest` | `approvalStatus`, `executionStatus`, `environment`, `requestedBy`, `instanceName` | pending / approved / rejected; not_started / in_progress / completed / failed |
| `s3Bucket` | `bucketName`, `environment`, `region`, `status` | pending / provisioned / failed |
| GitHub Workflow Run | status/conclusion, createdAt, name, repo relation | success / failure / cancelled |
| EC2 Instance | state, type, environment, region, owner/team | running / stopped |
| Jira Issue | status, issuetype, assignee, priority, project | |
| Dynatrace Problem | status, severity, entity | |

## 3. Place widgets on `$home` (Port UI)

- [ ] Links widget — 8 Home links from DESIGN.md
- [ ] Markdown welcome — replace setup Quick Access
- [ ] 4 number charts (or fewer if count is 0)
- [ ] Pie: request status
- [ ] Bar: GitHub runs
- [ ] Action card: EC2, S3, GitHub repo, Feedback
- [ ] Tables: pending EC2, failed/pending S3, failed GitHub runs
- [ ] Move My entities / recently viewed / recently used actions to the bottom
- [ ] Delete broken self-service action widget
- [ ] Optional: Platform consoles links (if approved)

## 4. Filters and permissions

- [ ] Dashboard filter: Environment (where the property exists)
- [ ] Widget filters as in DESIGN.md
- [ ] Confirm action RBAC unchanged for create-EC2 / create-S3

## 5. Relationships (phase 2 — do not block Home v1)

- [ ] Team / Group → AWS and GitHub entities (My entities)
- [ ] `ec2ChangeRequest` → EC2 Instance via `instanceId`
- [ ] S3 / EC2 → Terraform Cloud workspace (other TFC repo)
- [ ] Service → GitHub repo, Jira project, EKS/RDS

## 6. Promote

- [ ] Review Home on BannerHealth-Dev
- [ ] QA
- [ ] Production after QA
