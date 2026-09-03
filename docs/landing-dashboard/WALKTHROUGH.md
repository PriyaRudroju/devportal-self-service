# How to walk Sanjay (and Farida) through this dashboard design

**Meeting length:** 20–25 minutes
**Goal of the meeting:** Lock the wireframe so implementation can start. Do not implement live.
**What to share:** this folder, especially the wireframe image and `DESIGN.md`.
**Ask at the end:** approval on the 5 decisions in `DESIGN.md` section 7.

Print or screenshare in this order. Do not start with catalog tables — start with the user problem, then the picture, then the data work.

---

## Before the meeting (10 minutes of prep)

1. Open Port Home in BannerHealth-Dev so you can show the **current** page (setup links, empty My entities, broken action).
2. Open Self-Service Hub so they remember create/delete already lives there.
3. Have **Option A** ready: `docs/landing-dashboard/assets/port-home-executive.png`. Keep the overview slide and the first wireframe in reserve.
4. Have Builder → Data model ready if they ask "which table is that?"
5. Know the date: **Home v1 in QA by the 11th** if we lock design today. Relationships and team-scoped filters can trail.

Opening line:

> "This is the initial Home wireframe — not the built dashboard. If we lock what information sits on Home, we can start pulling records, attributes, and filters next. Implementation then QA then prod still has to happen, which is why we needed this design first."

---

## Step 1 — Frame the priority (1 minute)

Say:

> "Automation and the TFC repo work continue, but the priority you called out is the landing dashboard. Today we are only asking for a design lock: what should be on Home, which tables feed it, and what we will not try to finish by the 11th."

If they bring up other repos: acknowledge, then put it in the parking lot. TFC workspace mapping is a **relationship** we will need later, not a reason to delay the wireframe.

---

## Step 2 — Show the current Home and name the problem (2 minutes)

Screenshare **current** Port Home. Point at four things only:

1. Quick Access is still **setup** ("Set up service catalog") even though the catalog already has AWS, GitHub, Jira, Dynatrace.
2. **My entities is empty** — so ownership is not mapped yet. That is a data problem, not a widget problem.
3. The only working content is recently viewed + Submit Feedback.
4. The self-service widget is **broken** ("The action that was here no longer exists").

Say:

> "Home is not a cockpit yet. People land here and get configuration tasks, not 'what needs me' or 'request an EC2'. Dynamics-style dashboards work because they lead with numbers, queues, and actions. That is the pattern we are copying."

Do **not** walk the whole left sidebar. One sentence is enough: "The data is already in those catalog tables. Home just does not use it."

---

## Step 3 — Show the recommended Home (8 minutes)

Open **Option A** (`port-home-executive.png`). Walk **rows**, not random widgets. Pause after each row for "any change?"

If they want the full widget list, the original wireframe is the inventory; Option A is the client look. If they ask for more designs, show the overview slide, then Platform ops and Plan my day. Recommend: Home = Option A, extra pages optional.

### Row 1 — Quick Links + welcome

> "First thing on the page is Quick Links. Eight destinations, not the whole sidebar."

Read the eight:

1. Self-Service Hub
2. Plan my day
3. My team's work
4. Scorecards
5. EC2 catalog
6. Jira Issues
7. GitHub Runs
8. Submit Feedback

Then:

> "The welcome card replaces the setup checklist. It tells you to request, track approvals, or check failures. Optional extra: a small 'Platform consoles' list for AWS, Terraform Cloud, GitHub, Jira, Dynatrace — I would like a yes/no on that."

**If they ask for more links:** "Hub already has every create/delete card. If we put all of them on Home, Home becomes a second Hub. Extra links can live under Platform consoles or the sidebar."

### Row 2 — Four KPI tiles

> "Same idea as Dynamics tiles. One number, click to drill into the rows."

| Tile | Source table |
|---|---|
| Pending approvals | EC2 Change Request, `approvalStatus = pending` |
| Failed workflow runs | GitHub Workflow Runs |
| Open Dynatrace problems | Dynatrace Problem (swap to Jira bugs if this table is thin) |
| Active EC2 instances | EC2 / Terraform-managed EC2 |

> "If a table has almost no entities, we will not fake a tile. We will drop it in implementation after we count records."

### Row 3 — Charts

> "Pie: self-service requests by status. Bar: GitHub runs for the last 7 days. That is the 'is the platform healthy?' glance."

### Row 4 — Actions + Needs attention

> "Request something: only EC2, S3, GitHub repo, and Feedback. Everything else stays on Self-Service Hub."

> "Needs attention is a filtered table, not a new system. For the 11th we use the tables we already have: pending EC2 requests, failed/pending S3, failed GitHub runs. One unified work-item blueprint would be nicer later, but it is extra scope."

### Row 5 — Personal widgets

> "My entities, recently viewed, recently used actions stay — but they move **below** the work. Today they dominate the page while empty. We also fix the broken action widget."

Stop. Ask: **"Does this layout match what you want people to see when they open Port?"**

---

## Step 4 — Map information to tables (4 minutes)

Switch to `DESIGN.md` section 4 (or a shared screen of the table). This is the part they asked for: *what information comes from which tables.*

Talk in this order:

1. **Records we already have**
   - EC2 Change Request → pending approvals + request pie
   - S3 Bucket → pending/failed buckets
   - GitHub Workflow Run → failed runs KPI + 7-day bar
   - EC2 Instance → active count
   - Jira Issue / Dynatrace Problem → work and ops KPIs
   - Existing actions → action cards and recently used actions

2. **Attributes we must confirm**
   - `approvalStatus`, `executionStatus` on EC2 requests
   - `status` on S3
   - GitHub run conclusion/status and timestamp
   - EC2 instance state
   - Jira status / assignee
   - Dynatrace problem status

3. **Filters and policies**
   - Home dashboard filter: Environment
   - Widget filters: pending, failed, open
   - Do **not** change who is allowed to run prod create actions just because the button is on Home

4. **Relationships we still need** (be honest that this is the long pole)
   - Team owns resource → My entities and "my team" filters
   - Request → provisioned EC2/S3
   - Service → GitHub repo, Jira project, AWS
   - TFC workspace → S3/EC2 (Farida's other repo)

Say:

> "Home v1 can go live with step 1–3 using properties that already exist. Step 4 is why My entities is empty today. I am not blocking the 11th on a full service graph. I am blocking it on locking the widgets and confirming which tables actually have data."

---

## Step 5 — Show the path to the 11th (3 minutes)

Walk their own process back to them so it feels familiar:

| Step they already listed | What we will do |
|---|---|
| Pull records from the right tables | Entity count per blueprint; drop empty KPIs |
| Retrieve attributes | Confirm property keys in Data model |
| Filters and policies | Environment filter + status filters; keep action RBAC |
| Missing relationships | Phase 2; do not block Home v1 |
| Implement dashboard | Build on Port Home in **dev** |
| QA | Promote to QA environment |
| Production | After QA, same Git promotion path as other Port config |

**Proposed split:**

- **By the 11th:** Home v1 — quick links, 4 KPIs (or fewer if data is missing), 2 charts, 4 action cards, needs-attention tables, personal widgets cleaned up, broken widget removed.
- **After the 11th:** ownership relations, TFC repo mapping, team-scoped dashboard, optional Platform ops page, GitOps for pages.

Ask: **"Is Home v1 on that scope acceptable for the 11th, with relationships as a follow-on?"**

---

## Step 6 — Get the five decisions (3 minutes)

Do not leave without answers. Read them one by one:

1. Approve the **8 quick links**, or name replacements.
2. Approve the **4 KPIs**, or swap Dynatrace → Jira.
3. Approve **4 Home actions** (EC2, S3, GitHub repo, Feedback). Yes/no on adding more.
4. **Platform consoles** (AWS, TFC, GitHub, Jira, Dynatrace) on Home — yes or later.
5. **One Home for everyone**, or also a Platform ops dashboard before the 11th.

Write the answers in the meeting notes. That is the design lock.

---

## Step 7 — Close (1 minute)

Closing line:

> "I will turn this into the build checklist next: blueprint identifiers, filters, and which widgets we can place immediately. You will see the first Home in **dev**, then QA, then prod. I will not wait on the TFC repo review to start the widgets that already have data."

Offer the artifact: this folder in Git so they can comment on links and KPIs in the PR.

---

## If they push back

| They say | You say |
|---|---|
| "Put every self-service card on Home." | Hub already does that. Home is for status + the top 4 requests. Extra cards bury the KPIs. |
| "This looks like extra work before the 11th." | The 11th was always after design lock. Building without agreeing on tables is how we get another empty Home. |
| "My entities must work." | That needs ownership relations. We can keep the widget, but it will stay empty until we map Team → resource. |
| "Make it look like Dynamics exactly." | Same components: tiles, charts, views, quick create. Port's widgets are those components. |
| "Include AI Assist." | We can add the AI agent widget later. It should not replace KPIs on v1. |
| "What about the other TFC repo?" | It matters for relating workspaces to S3/EC2. It does not change the Home layout. We add that relation in phase 2. |

---

## Suggested spoken demo script (if you only have 10 minutes)

Use this verbatim:

1. "Current Home is a setup page. Catalog and self-service already exist; Home does not show them."
2. "Target Home is a Dynamics-style cockpit: links, four numbers, two charts, four request buttons, a needs-attention table."
3. "Quick links: Hub, Plan my day, team work, scorecards, EC2, Jira, GitHub runs, feedback."
4. "Numbers come from EC2 change requests, GitHub workflow runs, Dynatrace problems, and EC2 instances."
5. "By the 11th we implement that on Home in dev → QA → prod. Ownership graph and TFC relations follow so My entities and team filters start working."
6. "I need yes/no on the eight links, four KPIs, and four actions."
