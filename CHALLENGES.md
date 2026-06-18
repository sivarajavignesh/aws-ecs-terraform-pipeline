# Challenges Faced and Resolutions

## 1. Region mismatch between local AWS CLI config and Terraform defaults

The Terraform configuration originally defaulted to us-east-1, while the AWS CLI was configured for ap-south-1 (Mumbai), matching where the AWS account is actually based. This would have caused resources to be created in the wrong region, or attempted lookups against availability zones that do not exist in the configured region. Resolved by updating the aws_region and availability_zones variables in variables.tf to ap-south-1 and ap-south-1a/ap-south-1b respectively.

## 2. RDS identifier naming constraint

terraform apply initially failed with: first character of "identifier" must be a letter. The project name used as a prefix for resource naming started with a digit (8byte-assignment), which AWS RDS does not allow for DB instance identifiers. Resolved by renaming the project prefix to byte8-assignment, satisfying AWS naming rules while keeping the name recognizable.

## 3. Unavailable RDS engine version

terraform apply failed with: Cannot find version 16.3 for postgres in the target region. The specific minor version pinned in rds.tf was not available in ap-south-1 at the time of provisioning. Resolved by relaxing the engine_version to the major version only (16), which is allowed since AWS will select an available minor version automatically.

## 4. ECS service never reaching a stable state after first apply

After the initial Terraform apply, the ALB consistently returned 503 Service Temporarily Unavailable, and aws ecs describe-services showed failedTasks incrementing. Root cause: the ECS task definition was still pointing at a placeholder nginx image (used to validate infrastructure provisioning before the real application image existed), which has no /health endpoint matching the ALB target group's health check path. ECS kept cycling new tasks that immediately failed health checks. Resolved by updating the container_image variable to point at the application's real ECR image once it was built and pushed, then re-applying.

## 5. CD pipeline deploying the old image despite a successful CI build

The initial CD workflow called aws ecs update-service --force-new-deployment, which redeploys the current task definition rather than picking up a newly pushed image tag. As a result, new commits were built and pushed to ECR correctly, but ECS kept running the old image. Resolved by rewriting the staging deploy step to explicitly fetch the current task definition, replace its container image with the freshly built tag (keyed off the commit SHA), register a new task definition revision, and update the service to use that specific revision rather than relying on force-new-deployment alone.

## 6. GitHub Actions "wait services-stable" step timing out

When two CD workflow runs were triggered close together (from two pushes within a short window), the aws ecs wait services-stable step exceeded its default polling attempts and the job reported failure, even though the ECS service had, in fact, stabilized shortly afterward (confirmed independently via aws ecs describe-services showing runningCount equal to desiredCount and failedTasks at zero). This was a pipeline timing/race condition between overlapping deployments rather than a genuine application or infrastructure fault. With more time, this would be addressed by adding concurrency controls to the GitHub Actions workflow (concurrency group per environment) so overlapping CD runs queue rather than race.

## 7. Terraform state and AWS credentials hygiene

Care was taken from the start to keep terraform.tfstate, .terraform/, and *.tfvars out of version control via .gitignore, since Terraform state can contain sensitive values (including the database password) in plain text. AWS credentials for both the Terraform deployer and the GitHub Actions CI/CD pipeline were created as dedicated, non-root IAM users, with the CI/CD user scoped to only the ECR and ECS permissions it needs rather than full administrative access.

## What Would Be Improved With More Time

Move the database password out of the ECS task definition environment variables and into AWS Secrets Manager, injected at container runtime.
Separate the staging and production ECS clusters or task definitions fully, rather than sharing one service to reduce AWS costs during this assignment.
Add a concurrency group to the CD workflow to prevent overlapping deployments from racing each other.
Add integration tests that exercise the /db-health endpoint against a real test database in CI, rather than only unit tests against the Flask app in isolation.
