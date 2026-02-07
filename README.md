TS part was written 100% with claude code so idk how accuratei t is 😹

# Inventory Health Monitor

Restaurant inventory dashboard with deep learning forecasting and natural language SQL querying.

## Prerequisites

- Node.js 22+
- Python 3.11+
- PostgreSQL (local or [Neon](https://neon.tech))

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL if needed

# Run migrations
python ../scripts/migrate.py

# Start the server
python run.py
```

The API runs at `http://localhost:5000`. Check `http://localhost:5000/api/health`.

### Frontend

```bash
cd frontend
npm install

# Configure environment
cp .env.local.example .env.local

npm run dev
```

The app runs at `http://localhost:3000`.

## Database

### Local PostgreSQL

Create the database and use the default `DATABASE_URL`:

```bash
createdb inventory_health
```

### Neon (cloud PostgreSQL)

Set `DATABASE_URL` in your `backend/.env` to your Neon connection string:

```
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/inventory_health?sslmode=require
```

Everything else works the same — migrations, the backend, all of it.

## Migrations

Migrations are plain SQL files in `migrations/` using the naming convention `001_name.sql`, `002_name.sql`, etc. Run them with:

```bash
python scripts/migrate.py
```

Applied migrations are tracked in a `_migrations` table in the database.

## WSL Setup (Windows)

If you're on Windows, run everything inside WSL (Ubuntu). Do NOT run the backend or database from PowerShell.

### 1. Install WSL + Ubuntu

Open PowerShell as admin:

```powershell
wsl --install -d Ubuntu
```

Restart your machine, then open Ubuntu from the Start menu. It'll prompt you to create a Unix username and password.

### 2. Install dependencies

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Python
sudo apt install -y python3 python3-pip python3-venv

# Node.js 22 (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Git
sudo apt install -y git
```

### 3. Install and configure PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib

# Start the service
sudo service postgresql start

# Switch to the postgres user and create the database + your role
sudo -u postgres psql
```

Inside the `psql` shell:

```sql
CREATE USER your_username WITH PASSWORD 'your_password';
CREATE DATABASE inventory_health OWNER your_username;
\q
```

Then set your `DATABASE_URL` in `backend/.env`:

```
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/inventory_health
```

> **Tip:** PostgreSQL doesn't auto-start in WSL. Run `sudo service postgresql start` each time you open a new WSL terminal, or add it to your `~/.bashrc`:
> ```bash
> echo 'sudo service postgresql start' >> ~/.bashrc
> ```

### 4. Clone and run

```bash
git clone <repo-url>
cd inventory-health-monitor

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DATABASE_URL from step 3
python ../scripts/migrate.py
python run.py

# Frontend (new terminal)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Both `localhost:3000` (frontend) and `localhost:5000` (backend) are accessible from your Windows browser — WSL forwards the ports automatically.

## Deployment Notes

- **Frontend**: Deploy to [Vercel](https://vercel.com). Set `NEXT_PUBLIC_API_URL` to your backend URL.
- **Backend**: Deploy to AWS (EC2, ECS, or Lambda). Set `DATABASE_URL` and `FLASK_ENV=production`.

Details TBD.
