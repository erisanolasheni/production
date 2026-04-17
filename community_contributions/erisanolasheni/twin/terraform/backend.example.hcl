# Copy to backend.hcl and set bucket (and optional lock table).
# First-time migrate from local state:
#   terraform init -backend-config=backend.hcl -migrate-state
#
# Create the bucket first, e.g.:
#   aws s3api create-bucket --bucket YOUR_ACCOUNT-tfstate-twin --region us-east-1
# Optional DynamoDB table for state locking (string partition key "LockID").

bucket       = "YOUR_ACCOUNT_OR_ORG_TFSTATE_BUCKET"
key          = "twin/terraform.tfstate"
region       = "us-east-1"
encrypt      = true
# dynamodb_table = "twin-terraform-locks"
