# AWS ECS Terraform Pipeline — DevOps Engineer Assignment

End-to-end infrastructure, CI/CD pipeline, and monitoring setup for a containerized Flask application on AWS, built as part of the 8Byte.ai DevOps Engineer technical assignment.

## Architecture Overview

A VPC with public and private subnets spans two availability zones in ap-south-1 (Mumbai). The Flask application runs on ECS Fargate in the private subnets, behind an Application Load Balancer in the public subnets. The app connects to a PostgreSQL database on RDS, also in the private subnets, reachable only from the ECS service's security group. A NAT Gateway allows the private subnets outbound internet access (e.g. for pulling container images and OS packages) without exposing them directly to inbound traffic.

Traffic flow: Internet -> ALB (public subnet) -> ECS Fargate task (private subnet) -> RDS PostgreSQL (private subnet).

## Tech Stack

Infrastructure: Terraform, AWS (VPC, ECS Fargate, RDS PostgreSQL, ALB, ECR, CloudWatch, IAM)
Application: Python, Flask, Gunicorn, psycopg2
CI/CD: GitHub Actions
Monitoring: CloudWatch Dashboards, CloudWatch Logs, Container Insights

## Repository Structure

- app/ : Flask application, Dockerfile, tests
- terraform/ : All infrastructure as code
- .github/workflows/ : CI and CD pipeline definitions
- README.md : This file
- CHALLENGES.md : Issues encountered and resolutions

## How to Set Up and Run the Infrastructure

### Prerequisites

- AWS account with an IAM user that has programmatic access
- Terraform >= 1.5
- AWS CLI v2, configured via aws configure
- Docker (for local testing)

### Steps

1. Clone this repository.
2. cd terraform
3. terraform init
4. terraform plan (will prompt for a db_password)
5. terraform apply and confirm with yes
6. Note the alb_dns_name output, this is the public URL of the application.
7. Test with: curl http://ALB_DNS_NAME/health

To tear down all resources and stop billing: terraform destroy.

## CI/CD Pipeline

On every pull request, the CI workflow runs unit tests (pytest) and a dependency vulnerability scan (safety).

On every merge to main, CI additionally builds a Docker image, pushes it to Amazon ECR (which automatically scans the image for vulnerabilities on push), and tags it with both the commit SHA and latest.

Once CI succeeds, the CD workflow deploys to a staging environment by registering a new ECS task definition revision pointing at the freshly built image, then waits for the service to stabilize. After staging succeeds, deployment to production requires manual approval from a reviewer in GitHub's environment protection rules, satisfying the manual approval requirement for production. Both staging and production currently point at the same ECS service/cluster to minimize AWS costs during this assignment; in a production setup these would be fully separate clusters or task definitions per environment.

Slack notifications fire automatically on deployment failure in either stage, via a webhook configured in GitHub Secrets.

## Architecture Decisions

ECS Fargate was chosen over EKS to keep operational complexity proportional to the assignment's scope and timeline. Fargate removes the need to manage worker nodes while still demonstrating container orchestration, IAM task roles, and service-level scaling concepts. EKS would be the natural next step for a team running many heterogeneous services needing the broader Kubernetes ecosystem.

A single NAT Gateway is used rather than one per AZ, trading some availability for lower cost, acceptable for a private subnet whose main job is outbound package/image pulls, not for latency-sensitive production traffic.

The database is intentionally placed in private subnets with publicly_accessible set to false, reachable only from the ECS security group, never exposed to the internet directly.

## Security Considerations

The RDS instance is not publicly accessible and is locked down via security group rules that only permit inbound PostgreSQL traffic from the ECS service's security group, not from arbitrary IPs.

IAM follows a basic separation of duties: a dedicated terraform-deploy IAM user provisions infrastructure, while a separate, narrower github-actions-deploy IAM user, scoped to ECR push and ECS deploy permissions only, is used by the CI/CD pipeline. Neither uses root credentials.

Container images are scanned automatically on push to ECR, and dependencies are scanned in CI via safety.

The current setup passes the database password to the ECS task as a plain environment variable for simplicity within the assignment timeline. In a production environment, this should be stored in AWS Secrets Manager or SSM Parameter Store and injected at runtime, removing it from the task definition entirely. This is the most important security improvement to make next.

## Cost Optimization Measures

All resources use free-tier-eligible sizing where possible (db.t3.micro for RDS, minimal Fargate CPU/memory allocations). A single NAT Gateway is used instead of one per AZ. The infrastructure is destroyed (terraform destroy) between work sessions rather than left running continuously, since this is a demo/assignment environment rather than a live production workload.

## Secret Management

Database credentials are passed via a Terraform variable marked sensitive = true, never hardcoded into version control. GitHub Actions secrets store AWS credentials and the Slack webhook URL, never exposed in workflow logs. As noted above, moving the database password specifically into AWS Secrets Manager is the recommended next step beyond this assignment's scope.

## Backup Strategy

RDS automated backups are enabled with a 1-day retention period (backup_retention_period = 1), suitable for a short-lived demo environment. In production, this would be increased (commonly 7 to 35 days) along with enabling Multi-AZ for high availability.

## Monitoring and Logging

Two CloudWatch dashboards are provisioned via Terraform: one covering infrastructure metrics (ECS CPU/memory utilization, ALB request count and latency, RDS CPU/connections/storage), and one covering application health (ALB 4xx/5xx error rates, healthy vs unhealthy target counts, and a live application log stream). Application logs are centralized in CloudWatch Logs under /ecs/PROJECT_NAME. ECS Container Insights is enabled on the cluster for deeper container-level metrics.
