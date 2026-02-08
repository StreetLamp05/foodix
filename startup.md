# Foodix — Local Setup Guide

This guide walks you through running the entire Foodix stack on your local machine.

## Prerequisites

| Dependency | Version | Why |
|---|---|---|
| **Node.js** | 22+ | Frontend (Next.js 16) |
| **Python** | 3.11+ | Backend (Flask) + ML (FastAPI) |
| **PostgreSQL** | 15+ | Database |
| **Ollama** | latest | Local LLM for NL2SQL (Qwen-2.5-Coder 32B) |
| **Git** | any | Clone the repo |

---

## 1. Clone the Repository

```bash
git clone https://github.com/<your-org>/foodix.git
cd foodix
```

---

## 2. Set Up PostgreSQL

### Option A: Local PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
createdb inventory_health
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER youruser WITH PASSWORD 'yourpassword';"
sudo -u postgres psql -c "CREATE DATABASE inventory_health OWNER youruser;"
```

**Windows (WSL):**
Run everything inside WSL (Ubuntu). Do NOT use PowerShell for the backend or database.
```powershell
# In PowerShell as admin:
wsl --install -d Ubuntu
```
Then inside your WSL terminal, follow the Ubuntu instructions above.

### Option B: Neon (Cloud PostgreSQL)

1. Sign up at [neon.tech](https://neon.tech)
2. Create a project and database named `inventory_health`
3. Copy your connection string — you'll use it in the next step

---

## 3. Start the Backend (Flask API)

```bash
cd backend

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate    # On Windows WSL: same command

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `backend/.env` with your database connection:
```env
DATABASE_URL=postgresql://youruser:yourpassword@localhost:5432/inventory_health
FLASK_ENV=development
FLASK_PORT=5000
AUTO_MIGRATE=false
```

If using Neon, replace `DATABASE_URL` with your Neon connection string (append `?sslmode=require`).

Run migrations and start the server:
```bash
# Run database migrations
python ../scripts/migrate.py

# Start the backend
python run.py
```

The API will be running at **http://localhost:5000**. Verify with:
```bash
curl http://localhost:5000/api/health
```

---

## 4. Start the ML API (FastAPI + XGBoost)

Open a **new terminal**.

```bash
cd ml

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Train the XGBoost model and start the API:
```bash
# Option A: Use the setup script (installs, trains, starts everything)
./setup.sh

# Option B: Manual steps
python train_simple_xgboost.py          # Train the model
python restaurant_api.py                 # Start the API
```

The ML API will be running at **http://localhost:8001**. Test it:
```bash
curl http://localhost:8001/health
```

---

## 5. Set Up Ollama (for NL2SQL)

Ollama runs the local LLM that powers natural language querying.

**Install Ollama:**
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

**Pull the model and start serving:**
```bash
# Start the Ollama server (runs in background)
ollama serve &

# Pull the Qwen model (this is a large download, ~18GB)
ollama pull qwen2.5-coder:32b
```

Ollama will be available at **http://localhost:11434**.

> **Note:** The 32B model requires ~20GB of RAM. If your machine has less, you can use a smaller variant: `ollama pull qwen2.5-coder:7b` — it will still work but with slightly less accurate SQL generation. If you skip Ollama entirely, the dashboard and forecasting still work; only the NL2SQL chat feature will be unavailable.

---

## 6. Start the Frontend (Next.js)

Open a **new terminal**.

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
```

Edit `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

Start the dev server:
```bash
npm run dev
```

The app will be running at **http://localhost:3000**.

---

## 7. Verify Everything Is Running

You should have **4 processes** running:

| Service | URL | Terminal |
|---|---|---|
| Frontend (Next.js) | http://localhost:3000 | Terminal 1 |
| Backend (Flask) | http://localhost:5000 | Terminal 2 |
| ML API (FastAPI) | http://localhost:8001 | Terminal 3 |
| Ollama | http://localhost:11434 | Background |

Open **http://localhost:3000** in your browser (Chrome or Edge recommended for voice input support).

---

## Quick Troubleshooting

| Problem | Fix |
|---|---|
| `psycopg2` install fails | Install `libpq-dev`: `sudo apt install libpq-dev` (Linux) or use `psycopg2-binary` (already in requirements) |
| PostgreSQL won't start (WSL) | Run `sudo service postgresql start` — it doesn't auto-start in WSL |
| Port 5000 already in use | macOS Monterey+ uses 5000 for AirPlay. Disable AirPlay Receiver in System Settings, or change `FLASK_PORT` in `.env` |
| Ollama model too large | Use `qwen2.5-coder:7b` instead of `32b`. Less accurate but functional |
| Voice input not working | Use Chrome or Edge. Firefox and Safari have limited Web Speech API support |
| Frontend can't reach backend | Check that `NEXT_PUBLIC_API_URL` in `.env.local` matches your backend URL and port |
| ML API returns errors | Make sure the model is trained first (`python train_simple_xgboost.py`) before starting the API |

---

## Environment Variable Reference

### `backend/.env`
| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://localhost:5432/inventory_health` |
| `FLASK_ENV` | `development` or `production` | `development` |
| `FLASK_PORT` | Backend port | `5000` |
| `AUTO_MIGRATE` | Run migrations on startup | `false` |

### `frontend/.env.local`
| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:5000` |
