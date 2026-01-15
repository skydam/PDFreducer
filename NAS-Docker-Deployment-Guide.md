# Synology NAS Docker Deployment Guide

A guide for deploying web applications to your Synology DS918+ NAS using Docker.

---

## Overview

**Workflow:** Develop locally on Mac → Create zip → Upload via File Station → Build & run Docker container

**NAS Details:**
- Model: DS918+
- IP: 192.168.178.58
- Docker path: `/volume1/docker/`

---

## Project Structure

Your web app should have this basic structure:

```
my-webapp/
├── app/                    # Application code
│   ├── __init__.py
│   ├── routes/
│   ├── services/
│   ├── static/
│   └── templates/
├── Dockerfile              # Required for Docker
├── requirements.txt        # Python dependencies
├── run.py                  # Entry point
└── .dockerignore           # Files to exclude from Docker build
```

---

## Essential Files

### Dockerfile (Python/Flask)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (add what you need)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (change as needed)
EXPOSE 5000

# Run the app
CMD ["python", "run.py"]
```

### .dockerignore

```
venv/
__pycache__/
*.pyc
*.pyo
.git/
.gitignore
.DS_Store
*.md
downloads/
*.zip
```

### requirements.txt

```
Flask>=3.0.0
# Add your dependencies here
```

### run.py

```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## Deployment Steps

### 1. Create Zip File (on Mac)

```bash
cd /path/to/your/project
zip -r ~/Desktop/my-webapp.zip . \
    -x "venv/*" \
    -x "downloads/*" \
    -x "__pycache__/*" \
    -x "*.pyc" \
    -x ".git/*" \
    -x ".DS_Store" \
    -x "app/__pycache__/*" \
    -x "app/*/__pycache__/*"
```

### 2. Upload to NAS

1. Open **File Station** on Synology DSM
2. Navigate to `/volume1/docker/`
3. Create a folder for your app: `my-webapp/`
4. Upload the zip file
5. Right-click → **Extract** → Extract here

### 3. Build & Run Docker Container

SSH into your NAS or use **Task Scheduler** to run:

```bash
cd /volume1/docker/my-webapp

# Build the image
sudo docker build -t my-webapp .

# Run the container
sudo docker run -d \
    --name my-webapp \
    -p 8080:5000 \
    --restart unless-stopped \
    my-webapp
```

Your app is now running at: `http://192.168.178.58:8080`

---

## Common Configurations

### With Persistent Data (volumes)

```bash
sudo docker run -d \
    --name my-webapp \
    -p 8080:5000 \
    -v /volume1/docker/my-webapp/data:/app/data \
    --restart unless-stopped \
    my-webapp
```

### With Environment Variables

```bash
sudo docker run -d \
    --name my-webapp \
    -p 8080:5000 \
    -e SECRET_KEY=your-secret-key \
    -e DATABASE_URL=sqlite:///data/app.db \
    --restart unless-stopped \
    my-webapp
```

### With External Config File

```bash
sudo docker run -d \
    --name my-webapp \
    -p 8080:5000 \
    -v /volume1/docker/my-webapp/config.json:/app/config.json \
    --restart unless-stopped \
    my-webapp
```

---

## Updating an Existing App

### Quick Update (code changes only)

```bash
cd /volume1/docker/my-webapp
sudo docker stop my-webapp && sudo docker rm my-webapp
sudo docker build -t my-webapp .
sudo docker run -d \
    --name my-webapp \
    -p 8080:5000 \
    --restart unless-stopped \
    my-webapp
```

### Full Rebuild (dependency changes)

```bash
cd /volume1/docker/my-webapp
sudo docker stop my-webapp && sudo docker rm my-webapp
sudo docker build --no-cache -t my-webapp .
sudo docker run -d \
    --name my-webapp \
    -p 8080:5000 \
    --restart unless-stopped \
    my-webapp
```

### Clean Update (fresh deploy)

1. Delete everything in `/volume1/docker/my-webapp/` except config files
2. Upload new zip
3. Extract and rebuild

---

## Port Reference

| App | Internal Port | External Port | URL |
|-----|---------------|---------------|-----|
| video-rip | 5000 | 5050 | http://192.168.178.58:5050 |
| docker-dashboard | 5051 | 5051 | http://192.168.178.58:5051 |
| pdfreducer | 8000 | 5052 | http://192.168.178.58:5052 |

**Note:** Each app needs a unique external port.

---

## Useful Docker Commands

```bash
# List running containers
sudo docker ps

# List all containers (including stopped)
sudo docker ps -a

# View container logs
sudo docker logs my-webapp

# Follow logs in real-time
sudo docker logs -f my-webapp

# Stop a container
sudo docker stop my-webapp

# Start a stopped container
sudo docker start my-webapp

# Remove a container
sudo docker rm my-webapp

# Remove an image
sudo docker rmi my-webapp

# Enter a running container
sudo docker exec -it my-webapp /bin/bash

# Check disk usage
sudo docker system df

# Clean up unused images/containers
sudo docker system prune
```

---

## Troubleshooting

### Container won't start
```bash
# Check logs for errors
sudo docker logs my-webapp
```

### Port already in use
```bash
# Find what's using the port
sudo netstat -tlnp | grep 8080
```

### Permission issues
```bash
# Make sure the docker folder is accessible
sudo chown -R 1000:1000 /volume1/docker/my-webapp
```

### Out of disk space
```bash
# Clean up Docker
sudo docker system prune -a
```

---

## Template: New App Checklist

- [ ] Create project with Dockerfile, requirements.txt, run.py
- [ ] Test locally: `python run.py`
- [ ] Create zip file (exclude venv, __pycache__, .git)
- [ ] Create folder on NAS: `/volume1/docker/app-name/`
- [ ] Upload and extract zip
- [ ] Choose unique external port
- [ ] Build and run Docker container
- [ ] Test at `http://192.168.178.58:PORT`
- [ ] Add to port reference table above
