# HealthAI Labs

A full-stack AI-powered health analysis platform built with FastAPI, React, PostgreSQL, and MinIO.

---

# ✅ Prerequisites

You only need **Docker** and **Docker Compose** — no Python, Node.js, or any other runtime required.

### 🐧 Linux

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add your user to the docker group (no sudo needed after this)
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

> Docker Compose v2 is bundled with Docker. No separate install needed.

---

### 🪟 Windows

1. Download and install **Docker Desktop** from https://www.docker.com/products/docker-desktop
2. Enable **WSL 2** when prompted during setup (recommended)
3. Once Docker Desktop is running, open a terminal and verify:

```cmd
docker --version
docker compose version
```

---

### 🍎 macOS

1. Download and install **Docker Desktop** from https://www.docker.com/products/docker-desktop
2. Open Docker Desktop and wait for it to start
3. Verify in a terminal:

```bash
docker --version
docker compose version
```

---

# 📁 Clone the Project

```bash
git clone https://github.com/co-op-projects-to-boost-my-experience/HealthAI-Labs.git
cd HealthAI-Labs
```

---

# 🚀 Run the App

Docker Compose will build the backend and frontend images from source automatically — no manual build steps needed.

```bash
docker compose up -d --build
```

Then open your browser:

- **Frontend** → http://localhost
- **Backend API** → http://localhost:8000
- **MinIO Console** → http://localhost:9001 (user: `minio-admin123`, pass: `minio-admin123`)

Check running containers:

```bash
docker ps
```

Stream logs:

```bash
docker compose logs -f
```

Stream logs for a specific service:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

---

# 🏗️ Project Structure

```
HealthAI-Labs/
├── docker-compose.yml        ← run this from here
├── Backend/
│   ├── Dockerfile.Backend
│   └── ...
└── Frontend/
    ├── Dockerfile.Frontend
    └── ...
```

> All `docker compose` commands must be run from the **root of the repo** where `docker-compose.yml` lives.

---

# 🛑 Stop the App

```bash
docker compose down
```

Remove containers and all data volumes (resets the database):

```bash
docker compose down -v
```

---

# 🔄 Rebuild After Code Changes

If you modify any source files, rebuild the affected service:

```bash
# Rebuild everything
docker compose up -d --build

# Rebuild only the backend
docker compose up -d --build backend

# Rebuild only the frontend
docker compose up -d --build frontend
```

---

# 🧪 Test the Backend

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/news
curl http://localhost:8000/api/analysis
```

---

# ❗ Troubleshooting

### Backend fails to start — database not ready
The backend retries the database connection up to 10 times with a 3-second delay between attempts. If it still fails, check the database logs:

```bash
docker compose logs db
```

### "Port already in use"
Another process is using port 80, 8000, 5432, or 9000. Either stop that process or edit the `ports` mapping in `docker-compose.yml`, for example change `"80:80"` to `"8080:80"` and access the frontend at http://localhost:8080.

### Permission denied running docker (Linux)
Make sure you ran `sudo usermod -aG docker $USER` then opened a **new** terminal session or ran `newgrp docker`.

### Frontend shows blank page or old version
Force a clean rebuild with no cache:

```bash
docker compose down
docker compose build --no-cache frontend
docker compose up -d
```

---

# 🤝 Contributing

Pull requests and issues are welcome!
