#!/usr/bin/env bash
# Week 2 Day 4 — deploy Lambda + Terraform + static frontend (see production/week2/day4.md)
set -euo pipefail

ENVIRONMENT="${1:-dev}"
PROJECT_NAME="${2:-twin}"

echo "Deploying ${PROJECT_NAME} to ${ENVIRONMENT}..."

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Building Lambda package..."
(cd backend && uv run deploy.py)

cd terraform
# Remote state: copy backend.example.hcl → backend.hcl (gitignored), then: terraform init -backend-config=backend.hcl (-migrate-state from local state once).
if [ ! -f backend.hcl ]; then
  echo "Missing terraform/backend.hcl. Copy terraform/backend.example.hcl to terraform/backend.hcl, set the bucket, then run terraform init -backend-config=backend.hcl"
  exit 1
fi
terraform init -input=false -backend-config=backend.hcl

if ! terraform workspace list | grep -q "$ENVIRONMENT"; then
  terraform workspace new "$ENVIRONMENT"
else
  terraform workspace select "$ENVIRONMENT"
fi

if [ "$ENVIRONMENT" = "prod" ]; then
  terraform apply -var-file=prod.tfvars -var="project_name=$PROJECT_NAME" -var="environment=$ENVIRONMENT" -auto-approve
else
  terraform apply -var="project_name=$PROJECT_NAME" -var="environment=$ENVIRONMENT" -auto-approve
fi

API_URL="$(terraform output -raw api_gateway_url)"
FRONTEND_BUCKET="$(terraform output -raw s3_frontend_bucket)"
CUSTOM_URL="$(terraform output -raw custom_domain_url 2>/dev/null || true)"

cd ../frontend
echo "NEXT_PUBLIC_API_URL=$API_URL" > .env.production
npm install
npm run build
aws s3 sync ./out "s3://${FRONTEND_BUCKET}/" --delete
cd ..

echo ""
echo "Deployment complete."
echo "CloudFront URL: $(terraform -chdir=terraform output -raw cloudfront_url)"
echo "API Gateway   : $API_URL"
if [ -n "${CUSTOM_URL:-}" ]; then
  echo "Custom domain : $CUSTOM_URL"
fi
