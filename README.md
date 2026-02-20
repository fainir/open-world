# Open World Studio

A web app that wraps the Open World 3D game with an AI-powered chat interface. Users describe changes in natural language, and Claude modifies the game code in real time.

**Live:** https://open-world-studio-production.up.railway.app

## Features

- **AI Game Editor** — Describe changes in chat, Claude modifies the game code via SEARCH/REPLACE patches
- **Instant Preview** — See your modified game version immediately in the iframe
- **Version History** — Browse and switch between all versions created in a session
- **Save & Share** — Sign in to save versions and generate public share links
- **Auth System** — Email/username signup and login with JWT
- **Bring Your Own Key** — Users provide their own Anthropic API key

## Tech Stack

- **Frontend:** Vanilla JS SPA with dark theme UI
- **Backend:** Python / FastAPI
- **AI Agent:** Anthropic Claude API (claude-sonnet-4-20250514)
- **Database:** SQLite (persistent volume on Railway)
- **Auth:** JWT + bcrypt
- **Hosting:** Railway

## Project Structure

```
open-world/
├── index.html              # Original game (Three.js, ~4800 lines)
├── zones/                  # Game zone modules
├── app/
│   ├── backend/
│   │   ├── main.py         # FastAPI routes
│   │   ├── agent.py        # Claude API agent
│   │   ├── auth.py         # JWT auth
│   │   ├── models.py       # SQLAlchemy models
│   │   └── database.py     # SQLite setup
│   ├── static/
│   │   ├── index.html      # SPA entry point
│   │   ├── css/styles.css  # UI styles
│   │   └── js/             # auth.js, chat.js, app.js
│   ├── requirements.txt    # Python dependencies
│   └── run.py              # Local dev startup
├── railway.toml            # Railway deploy config
├── nixpacks.toml           # Build config
└── Procfile                # Process definition
```

## Local Development

```bash
# Create venv and install deps
python3 -m venv app/venv
app/venv/bin/pip install -r app/requirements.txt

# Optionally copy and edit .env
cp app/.env.example app/.env

# Run the server
app/venv/bin/python app/run.py
```

Open http://localhost:8000

## Deploy to Railway

### Prerequisites

- [Railway CLI](https://docs.railway.com/guides/cli) installed (`brew install railway`)
- Railway account — sign up at https://railway.com

### Steps

1. **Login to Railway**
   ```bash
   railway login
   ```

2. **Create a new project**
   ```bash
   railway init --name open-world-studio
   ```

3. **Link the project and create a service**
   ```bash
   railway link --project <PROJECT_ID>
   railway up --detach
   ```
   The first `railway up` creates the service and triggers the initial build.

4. **Link the service**
   ```bash
   railway service link open-world-studio
   ```

5. **Set environment variables**
   ```bash
   railway variables set \
     JWT_SECRET=$(openssl rand -hex 32) \
     DATA_DIR=/data/db \
     VERSIONS_DIR=/data/versions
   ```

6. **Add a persistent volume** (for SQLite DB + game version files)
   ```bash
   railway volume add --mount-path /data
   ```

7. **Generate a public domain**
   ```bash
   railway domain
   ```

8. **Redeploy** (picks up the new env vars and volume)
   ```bash
   railway up --detach
   ```

Your app will be live at the domain Railway generated.

### Subsequent deploys

After pushing changes to GitHub:
```bash
railway up --detach
```

Or connect your GitHub repo in the Railway dashboard for automatic deploys on push.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET` | Yes | Secret key for JWT tokens. Generate with `openssl rand -hex 32` |
| `DATA_DIR` | No | Directory for SQLite database. Default: `app/data/` |
| `VERSIONS_DIR` | No | Directory for saved game versions. Default: `app/versions/` |
| `PORT` | No | Server port. Railway sets this automatically |
