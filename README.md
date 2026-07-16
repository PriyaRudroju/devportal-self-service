# devportal-self-service

Self-service action to provision AWS S3 buckets via Port.io, GitHub Actions, and Terraform Cloud.

## Architecture

```
Port.io Self-Service Action
  → GitHub Actions (workflow_dispatch)
    → Terraform Cloud (remote state + apply)
      → AWS S3 bucket
        → Port.io catalog updated (UPSERT on success, LOG on failure)
```

## Repository Structure

```
.github/workflows/provision-s3-bucket.yml   # GitHub Actions workflow
terraform/
  modules/s3-bucket/                         # Reusable S3 module
  environments/dev/                          # Dev environment config
port/
  blueprints/s3-bucket.json                  # Port.io catalog blueprint
  actions/provision-s3-bucket.json           # Port.io action reference
```

## Setup Checklist

### 1. Terraform Cloud

1. Create an organization at [app.terraform.io](https://app.terraform.io)
2. Create an **API-driven** workspace named `dev-portal-s3-dev`
3. Add workspace environment variables:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
4. Generate an API token (User Settings → Tokens)
5. Store the token as a GitHub secret: `TF_API_TOKEN`
6. Store the org name as a GitHub secret: `TF_CLOUD_ORGANIZATION`

### 2. GitHub

1. Push this repo to `main` (Port reads from the default branch)
2. Add repository secrets:

| Secret | Purpose |
|---|---|
| `TF_API_TOKEN` | Terraform Cloud API token |
| `TF_CLOUD_ORGANIZATION` | Terraform Cloud organization name |
| `PORT_CLIENT_ID` | Port.io API client ID |
| `PORT_CLIENT_SECRET` | Port.io API client secret |

3. Confirm the Port GitHub App has **Actions Read/Write** permission on this repo

### 3. Port.io

1. Sign up or log in at [app.getport.io](https://app.getport.io)
2. Install the GitHub app: **Builder → Sources → GitHub**
3. Import the S3 blueprint:
   - **Builder → Blueprints → + Blueprint → JSON**
   - Paste contents of [`port/blueprints/s3-bucket.json`](port/blueprints/s3-bucket.json)
4. Create API credentials: **Builder → Credentials → + Credential**
   - Add `PORT_CLIENT_ID` and `PORT_CLIENT_SECRET` to GitHub secrets
5. Create the self-service action:
   - **Self-service → + Action**
   - Use [`port/actions/provision-s3-bucket.json`](port/actions/provision-s3-bucket.json) as reference
   - Backend: GitHub workflow `provision-s3-bucket.yml`
   - Map inputs in the invocation payload

### 4. Verify

1. Run the action from the Port Self-service page with a unique bucket name
2. Check the **GitHub Actions** tab for a successful workflow run
3. Check **Terraform Cloud** workspace `dev-portal-s3-dev` for a successful apply
4. Confirm the bucket exists in AWS `us-east-1`
5. Confirm the Port catalog shows a new `s3Bucket` entity with `status: provisioned`

## Local Development

```bash
cd terraform/environments/dev
export TF_CLOUD_ORGANIZATION="your-org-name"
terraform init
terraform plan -var="bucket_name=my-test-bucket-12345"
```

## Extending

- Add `terraform/environments/qa/` with workspace `dev-portal-s3-qa`
- Add `region` as a Port form dropdown input
- Add S3 hardening (versioning, encryption, public access block)
- Add a destroy/deprovision self-service action
