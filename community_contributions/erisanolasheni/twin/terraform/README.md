# Terraform (Week 2 Day 4)

Infrastructure definitions are **maintained in the course repo** as markdown excerpts. Add the files here by following:

- [`../../production/week2/day4.md`](../../production/week2/day4.md) — **Part 3** (`versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`, `terraform.tfvars`, optional `prod.tfvars`)

After copying:

1. **Lambda ↔ CloudFront ordering:** If `aws_lambda_function` includes `depends_on = [aws_cloudfront_distribution.main]`, remove it. Set Lambda env `CORS_ORIGINS` to `*` until you wire a fixed CloudFront domain, then tighten CORS if desired.
2. **Bedrock model ID:** Prefer `global.amazon.nova-2-lite-v1:0` (see [day3.md](../../production/week2/day3.md) / FAQ Q42).
3. **Lambda env for this codebase:** Include at least:
   - `USE_S3=true`
   - `S3_BUCKET=<memory bucket from Terraform>`
   - `LLM_PROVIDER=bedrock`
   - `BEDROCK_MODEL_ID=<same as tf var>`
   - `DEFAULT_AWS_REGION=us-east-1` (or your region)
4. Run `terraform init`, then `./scripts/deploy.sh dev` from the `twin/` root (requires AWS CLI, Docker for `deploy.py`, and `lambda-deployment.zip` from `backend/`).

**Remote state (required for CI):** `versions.tf` uses `backend "s3" {}`. Copy `backend.example.hcl` → `backend.hcl`, create the bucket, then `terraform init -backend-config=backend.hcl` (add `-migrate-state` if moving from local state).

Day 5 detail + OIDC trust examples: [`../../production/week2/day5.md`](../../production/week2/day5.md). Deploy workflow: [`../.github/workflows/deploy.yml`](../.github/workflows/deploy.yml).
