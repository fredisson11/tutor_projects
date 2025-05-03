# Backend CI/CD Workflows

This folder contains the CI/CD pipeline for the backend project.

## Workflows

- **Backend CI/CD** (`backend-ci.yml`):
  - Runs on every push to the `main` branch.
  - Steps:
    - Checkout code
    - Lint (flake8) and security checks (bandit)
    - Build Docker image
    - Push Docker image to DockerHub
    - Trigger centralized deployment workflow in the infrastructure repository

## Secrets and Variables

- **Repository Variables**:
  - `IMAGE_REPO`: Docker image repository name (e.g., `tp154-backend`)
- **Repository Secrets**:
  - `DOCKERHUB_USERNAME`: DockerHub username
  - `DOCKERHUB_TOKEN`: DockerHub token
  - `INFRASTRUCTURE_REPO_TOKEN`: Personal access token with `repo` and `workflow` permissions for triggering deployments

## Triggered Workflow

- Triggers the `backend-cd-main.yml` workflow in the infrastructure repository (`tp154-infrastructure`) via GitHub API (`workflow_dispatch`).
