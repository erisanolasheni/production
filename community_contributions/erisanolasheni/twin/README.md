# Digital Twin — Week 2 (AI in Production)

Full-stack twin: **Next.js (App Router)** + **FastAPI** + **conversation memory** (local JSON or **S3**) + **OpenAI-compatible (OpenRouter) locally** or **AWS Bedrock** in production.

## What’s implemented in this folder

| Phase | Status |
|--------|--------|
| **Day 1** — Local chat + file memory | Done (superseded by Day 2 context) |
| **Day 2** — Rich context (`data/`, PDF, `context.py`), S3-ready API, Lambda package | **Done** — see `backend/` |
| **Day 3** — Bedrock via `LLM_PROVIDER=bedrock` | **Done** in `server.py` |
| **Day 4** — Terraform, `scripts/deploy.sh` | **Scripts + `terraform/README.md`** — paste HCL from course `day4.md` into `terraform/` |
| **Day 5** — GitHub Actions, OIDC | **In-repo:** [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) — see **GitHub Actions** below; also [`../production/week2/day5.md`](../production/week2/day5.md) |
| **Capstone (optional)** — Tools, extra S3 for “unknown” questions | Not implemented; extend after core deploy works |

## Local development

**Backend** (`backend/.env` — copy from `backend/.env.example`):

- `LLM_PROVIDER=openai` + OpenAI or **OpenRouter** (`LLM_BASE_URL`, `LLM_MODEL`, API key).
- `USE_S3=false` — sessions stored under `memory/`.

```bash
cd backend
uv sync
uv run uvicorn server:app --reload
```

**Frontend**:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). API defaults to `http://localhost:8000` or set `NEXT_PUBLIC_API_URL` in `frontend/.env.local`.

**Static export** (for S3 / CloudFront):

```bash
cd frontend && npm run build   # writes to frontend/out
```

## AWS path (summary)

1. **Build Lambda zip:** `cd backend && uv run deploy.py` (Docker required).
2. **Manual console deploy** — [`../production/week2/day2.md`](../production/week2/day2.md) (Lambda, S3, API Gateway, CloudFront), **or** **Terraform** — [`../production/week2/day4.md`](../production/week2/day4.md) + [`terraform/README.md`](terraform/README.md).
3. **Production LLM:** set `LLM_PROVIDER=bedrock` on Lambda; attach Bedrock + S3 policies to the execution role (see course).
4. **CI/CD:** GitHub Actions (below) or [`../production/week2/day5.md`](../production/week2/day5.md).

## GitHub Actions

Workflow: [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) (push to `main` or **Run workflow**). It builds the Lambda zip (Docker), runs **Terraform** with **S3 remote state**, builds the Next static site, syncs to the frontend bucket, and invalidates CloudFront.

**One-time setup**

1. **S3 bucket for Terraform state** (versioning recommended). Put the name in repo secret **`TF_STATE_BUCKET`**.
2. **Migrate existing local state** (if you already deployed from your laptop):

   ```bash
   cd terraform
   cp backend.example.hcl backend.hcl   # edit bucket name
   terraform init -backend-config=backend.hcl -migrate-state
   ```

3. **GitHub OIDC → AWS:** create an IAM role that trusts `token.actions.githubusercontent.com` for your repository (see [AWS docs](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)). Attach policies that allow the same operations you use for deploy (Terraform apply, S3 sync, CloudFront invalidation, etc.). Set secret **`AWS_DEPLOY_ROLE_ARN`** to that role’s ARN.
4. Optional: secret **`TF_LOCK_TABLE`** (DynamoDB table for state locking), repository variable **`TF_STATE_KEY`** (default `twin/terraform.tfstate`), **`DEPLOY_ENVIRONMENT`** (default `dev`).

**Note:** With `backend "s3"` in [`terraform/versions.tf`](terraform/versions.tf), `terraform init` requires a backend config file (`backend.hcl` locally, or CI-generated `backend.ci.hcl`).

## Data files

Edit **`backend/data/facts.json`**, **`summary.txt`**, **`style.txt`**, and replace **`backend/data/linkedin.pdf`** with your export. The twin’s system prompt is built in **`backend/context.py`** (no separate `me.txt`).

## Course PDFs

Lesson markdown lives under [`../production/week2/`](../production/week2/). Slides: [Ed’s resources page](https://edwarddonner.com/2025/09/15/ai-in-production-gen-ai-and-agentic-ai-on-aws-at-scale/).
