# ServiceNow setup (Port form to ServiceNow ticket)

This is the prototype slice: a Port self-service form creates one real ServiceNow catalog request, and the ticket number and a tracking link appear on the Port catalog entity. The developer never opens a ServiceNow catalog form — Port is the only form they fill; the catalog link is for tracking the already-submitted request.

Approval callbacks, fan-out to multiple onboarding items, and fulfilment automation are **not** part of this slice.

## Flow

```
Port form (S/N Request)
  -> Create Pending Catalog Entity (serviceNowRequest, status pending)
  -> Create ServiceNow Request (webhook -> Lambda POST /servicenow/create-request)
       -> GET /api/now/table/sys_user           (resolve requester email to sys_id)
       -> POST /api/sn_sc/servicecatalog/items/<item>/order_now
       -> PATCH Port entity (ticketNumber, ticketUrl, ticketSysId, status submitted)
```

The Port node calls **our** API Gateway, not ServiceNow directly, because the flow needs two ServiceNow calls (user lookup, then create) and because the ticket number has to be written back to Port. `order_now` is the API equivalent of clicking Order in ServiceNow — it does not open a ServiceNow form.

## 1. Create a personal developer instance

1. Sign in at [developer.servicenow.com](https://developer.servicenow.com).
2. **Request an instance**, and record the instance URL plus the generated admin username and password.

PDIs hibernate after roughly 10 days idle and can be reclaimed entirely. Treat this instance as disposable, and never put real personal data in it -- onboarding data is personal data, so use fabricated test users only.

## 2. Create a minimal catalog item

Do not start from a complex out-of-the-box item. Create a small one so the variable mapping stays obvious.

1. In the instance, go to **Service Catalog > Catalog Definitions > Maintain Items** and click **New**.
2. Name it `Cloud Access Request`, and set **Catalog** to `Service Catalog` and **Category** to any existing category.
3. Save, then in the **Variables** related list add two variables:

| Type | Question | Name |
|---|---|---|
| Single Line Text | Service | `service` |
| Multi Line Text | Justification | `justification` |

4. Note the item's `sys_id` from the URL (or right-click the header and choose **Copy sys_id**).

The variable **Name** column is what the API uses. The question label is irrelevant to the integration.

## 3. Record the config values

| Value | Where it goes | Example |
|---|---|---|
| Instance URL | TFC variable `servicenow_instance_url` | `https://dev123456.service-now.com` |
| Catalog item `sys_id` | TFC variable `servicenow_catalog_item_sys_id` | `9c2d7a1e...` |
| Username | TFC variable `servicenow_username` (sensitive) | `admin` |
| Password | TFC variable `servicenow_password` (sensitive) | - |

Credentials belong in the `dev-portal-integration-dev` Terraform Cloud workspace as **sensitive** variables, exactly like `teams_webhook_url` and `port_client_secret`. Never commit them, and do not add them to `port/environments/config.env`.

## 4. Prove the API before deploying anything

```bash
export SERVICENOW_INSTANCE_URL=https://dev123456.service-now.com
export SERVICENOW_USERNAME=admin
export SERVICENOW_PASSWORD=...
export SERVICENOW_CATALOG_ITEM_SYS_ID=...

python scripts/servicenow_smoke.py --email abel.tuter@example.com --service "AWS dev account" --justification "smoke test"
```

The script resolves the user, orders the item, and prints the raw response. Do this **first** -- the response field names for the created request vary by release, and `handle_servicenow_create_request` parses them.

Add `--lookup-only` to check credentials and the user lookup without creating a ticket.

## 5. Deploy the Lambda route

This demo applies Lambda + API Gateway from workspace **`dev-portal-s3-dev`** (`terraform/environments/dev`). Put the four ServiceNow variables on that workspace, then plan and apply. Keep `bucket_name` as the value already in state so you do not create an extra bucket.

The apply creates `POST /servicenow/create-request` in **us-east-2**. Copy the `api_gateway_url` output into GitHub Environment `API_GATEWAY_URL` and `port/environments/config.env`, then run **Deploy Port Config**. Port must call the new URL; the old `fvoyz6jb9i` gateway does not have this route.

## 6. Apply the Port config

Push to `dev` or a `feature/**` branch, which triggers **Deploy Port Config** for the paths under `port/**`. That creates the `serviceNowRequest` blueprint and the **Request ServiceNow Ticket** workflow.

## Field mapping

| Port form input | Sent as | ServiceNow target |
|---|---|---|
| Requested For (email) | `sysparm_requested_for` (resolved to `sys_id`) | `Requested for` on the request |
| Service | `variables.service` | catalog item variable `service` |
| Justification | `variables.justification` | catalog item variable `justification` |

The submitting Port user's email is stored on the Port entity as `requestedBy` for traceability. It is not sent to ServiceNow in this slice.

## Verification

| Case | Expected |
|---|---|
| Valid requester email | Entity goes `pending` then `submitted`, with a clickable **Track in ServiceNow** link for viewing the already-created REQ (not a form); the REQ has the variable values and a populated `Requested for` |
| Email with no `sys_user` record | Entity `failed` with `No ServiceNow user found for ...`, and no ticket created |
| Same `entityId` submitted twice | Second call returns the existing ticket number, no duplicate ticket |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 User Not Authenticated` | Wrong instance URL, username, or password | Re-check the TFC variables; confirm with `scripts/servicenow_smoke.py --lookup-only` |
| Ticket created but `Requested for` is blank | `sysparm_requested_for` needs a `sys_id`, not an email or user name | The Lambda resolves it; if it still fails, check the `glide.sc.req_for.roles` and `glide.sc.req_for.roles.default` properties, which control whether one user may order on behalf of another |
| `No ServiceNow user found for <email>` | No `sys_user` row with that email in the instance | Use a real instance user, or create a test user. PDIs ship with users such as Abel Tuter |
| Request created but no approvals or tasks | Something inserted into `sc_req_item` directly instead of using `order_now` | Always order through `/api/sn_sc/servicecatalog/items/<item>/order_now`; a table insert bypasses the catalog workflow |
| Port node red with a `502` | ServiceNow returned an error; the entity carries the message in `errorMessage` | Read `errorMessage` on the entity, then the Lambda log group `/aws/lambda/devportal-teams-approval` |
| Instance URL suddenly 404s | PDI hibernated or was reclaimed | Wake it from developer.servicenow.com, or provision a new one and update the TFC variables and item `sys_id` |

## Known constraints for phase two

- **Bundling multiple items into one request** cannot use the out-of-the-box `add_to_cart` and `cart/submit_order` endpoints with a shared service account: the cart is scoped to the authenticating user's session, so concurrent submissions merge into one request and the second call fails with `Cart is empty`. It needs a Scripted REST API on the ServiceNow side that creates a uniquely named cart per submission.
- **Approval outcomes** need either a Business Rule and Outbound REST Message calling back to us, polling, or Port's native ServiceNow ingestion reacting to state changes. Our `/approval-decision` route is currently unauthenticated and should not be reused for real callbacks until that is fixed.
- **OAuth 2.0** should replace Basic auth for anything beyond a PDI.
