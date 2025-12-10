🎯 CareerLens – Final Project (IS218)
🔗 Live Application: https://finalproject.danielkinatukara.me/
🚀 Overview

CareerLens is an AI-powered career assistant built with FastAPI, Docker, and PostgreSQL.
It helps users:

📝 Upload and analyze resumes

🔍 Match with job opportunities

🤖 Prepare with AI-driven interview practice

🔐 Manage accounts with secure authentication

This project was built as the Final Project for IS218 – Building Web Applications.

📁 Repository Structure
/app
  ├── api/                # API route handlers
  ├── auth/               # Authentication, JWT, email utils
  ├── core/               # App config
  ├── models/             # SQLAlchemy models
  ├── schemas/            # Pydantic schemas
  ├── services/           # Resume + job search logic
  ├── templates/          # HTML templates (Jinja2)
  └── static/             # CSS, assets
/docker-compose.yml       # App + PostgreSQL services
/Dockerfile               # Backend container

🛠️ Tech Stack

Backend: FastAPI (Python 3.12)

Database: PostgreSQL 15 (via Docker)

Authentication: JWT + secure password hashing

CI/CD: GitHub Actions → Docker Hub → DigitalOcean VPS

Reverse Proxy: Caddy (Automatic HTTPS)

AI Features: OpenAI API + JSearch API

🌐 Deployment Architecture
GitHub → GitHub Actions (CI/CD)
        → Docker Hub (image)
        → DigitalOcean VPS
            → Docker Compose (app + db)
            → Caddy (HTTPS reverse proxy)

🧪 Running Tests
pytest --cov=app --cov-report=xml

🐳 Running Locally with Docker
1️⃣ Clone the repository
git clone https://github.com/dek2024/finalprojectis218
cd finalprojectis218

2️⃣ Create an .env file

⚠️ Use placeholders — do NOT include real secrets.

DATABASE_URL=postgresql://postgres:<your_password_here>@db:5432/careerlens
OPENAI_API_KEY=<your_api_key>
JSEARCH_API_KEY=<your_api_key>
JWT_SECRET_KEY=<jwt_secret>
SECRET_KEY=<secret>
SMTP_PASSWORD=<email_app_password>
BACKEND_BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=http://localhost:8000

3️⃣ Run Docker Compose
docker compose up --build


Your app will be available at ▶ http://localhost:8000

🔐 Important Security Notes

Never commit real secrets to GitHub

Always store secrets in GitHub Actions Secrets

Use placeholder database URLs in documentation like:

postgresql://postgres:<password>@db:5432/careerlens

🚀 CI/CD Pipeline

Your pipeline:
✔ Automatically runs tests
✔ Builds & pushes a Docker image
✔ SSHs into your VPS
✔ Pulls the new image
✔ Restarts only the CareerLens stack

This ensures zero-downtime deployment and avoids breaking your Project 3 app.

👨‍🏫 Final Project Requirements

This README meets:
✔ Link to live hosted application
✔ Clear explanation of project functionality
✔ Tech stack overview
✔ Deployment process description
✔ Instructions to run locally

🙌 Acknowledgments

Built by Daniel Kinatukara
NJIT – IS218 – Fall 2025
Instructor: Prof. Williams
