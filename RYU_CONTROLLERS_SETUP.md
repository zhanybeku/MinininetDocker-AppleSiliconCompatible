# Ryu Controllers Docker Setup Guide

This guide will help you install Docker and run multiple Ryu SDN controllers in Docker containers for your multi-block topology.

## Prerequisites

You need 5 Ryu controllers running on ports 6653, 6654, 6655, 6656, and 6657 (one for each block).

## Step 1: Install Docker

### On Linux (GCP VM / Ubuntu/Debian):

```bash
# Update package index
sudo apt-get update

# Install prerequisites
sudo apt-get install -y ca-certificates curlzhanybek_bekbolat@mininet-wifi:~$ sudo apt install apt-transport-https ca-certificates curl software-properties-common -y
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)      
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)... 10Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)       
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)... 11Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)       
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 15931 (apt)... 12Waiting for cache lock:  gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Verify installation
docker --version
docker compose version
```

### On macOS:

```bash
# Install using Homebrew
brew install --cask docker

# Or download from: https://www.docker.com/products/docker-desktop/

# Start Docker Desktop application

# Verify installation
docker --version
docker compose version
```

### Quick Install (Alternative - All Platforms):

```bash
# Using Docker's convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## Step 2: Start All Ryu Controllers

### Option A: Using Docker Compose (Recommended)

```bash
# Navigate to project directory
cd /path/to/MinininetDocker-AppleSiliconCompatible

# Start all 5 controllers
docker compose -f ryu-controllers-docker-compose.yml up -d

# Check if they're running
docker compose -f ryu-controllers-docker-compose.yml ps

# View logs
docker compose -f ryu-controllers-docker-compose.yml logs -f

# Stop all controllers
docker compose -f ryu-controllers-docker-compose.yml down

# Restart a specific controller
docker compose -f ryu-controllers-docker-compose.yml restart ryu-controller-1
```

### Option B: Using Docker Run Commands

```bash
# Controller 1 (Port 6653)
docker run -d --name ryu-controller-1 \
  -p 6653:6653 -p 8080:8080 \
  -v $(pwd)/examples:/ryu/app/examples \
  -v $(pwd)/projects:/ryu/app/projects \
  osrg/ryu:latest \
  ryu-manager --ofp-tcp-listen-port 6653 --verbose ryu/app/examples/simple_controller.py

# Controller 2 (Port 6654)
docker run -d --name ryu-controller-2 \
  -p 6654:6654 -p 8081:8080 \
  -v $(pwd)/examples:/ryu/app/examples \
  -v $(pwd)/projects:/ryu/app/projects \
  osrg/ryu:latest \
  ryu-manager --ofp-tcp-listen-port 6654 --verbose ryu/app/examples/simple_controller.py

# Controller 3 (Port 6655)
docker run -d --name ryu-controller-3 \
  -p 6655:6655 -p 8082:8080 \
  -v $(pwd)/examples:/ryu/app/examples \
  -v $(pwd)/projects:/ryu/app/projects \
  osrg/ryu:latest \
  ryu-manager --ofp-tcp-listen-port 6655 --verbose ryu/app/examples/simple_controller.py

# Controller 4 (Port 6656)
docker run -d --name ryu-controller-4 \
  -p 6656:6656 -p 8083:8080 \
  -v $(pwd)/examples:/ryu/app/examples \
  -v $(pwd)/projects:/ryu/app/projects \
  osrg/ryu:latest \
  ryu-manager --ofp-tcp-listen-port 6656 --verbose ryu/app/examples/simple_controller.py

# Controller 5 (Port 6657)
docker run -d --name ryu-controller-5 \
  -p 6657:6657 -p 8084:8080 \
  -v $(pwd)/examples:/ryu/app/examples \
  -v $(pwd)/projects:/ryu/app/projects \
  osrg/ryu:latest \
  ryu-manager --ofp-tcp-listen-port 6657 --verbose ryu/app/examples/simple_controller.py
```

## Step 3: Verify Controllers Are Running

```bash
# Check running containers
docker ps

# Check if ports are listening
sudo netstat -tlnp | grep -E "6653|6654|6655|6656|6657"

# Or using ss
sudo ss -tlnp | grep -E "6653|6654|6655|6656|6657"

# Test controller connectivity
curl http://localhost:8080/stats/switches  # Controller 1
curl http://localhost:8081/stats/switches  # Controller 2
```

## Step 4: Run Your Mininet-WiFi Topology

Now that controllers are running, start your topology:

```bash
# In your GCP VM (where mininet-wifi is installed)
cd ~/mininet-wifi
sudo python3 /path/to/projects/pa2/Zhanybek_Bekbolat.py
```

The topology will connect to:
- Block 3: `127.0.0.1:6653`
- Block 4: `127.0.0.1:6654`
- Block 5: `127.0.0.1:6655`
- Block 6: `127.0.0.1:6656`
- Block 7: `127.0.0.1:6657`

## Managing Controllers

### View Logs

```bash
# All controllers
docker compose -f ryu-controllers-docker-compose.yml logs -f

# Specific controller
docker logs -f ryu-controller-1
```

### Restart Controllers

```bash
# Restart all
docker compose -f ryu-controllers-docker-compose.yml restart

# Restart specific one
docker restart ryu-controller-1
```

### Stop Controllers

```bash
# Stop all
docker compose -f ryu-controllers-docker-compose.yml down

# Stop specific one
docker stop ryu-controller-1
```

### Remove Containers

```bash
# Remove all
docker compose -f ryu-controllers-docker-compose.yml down -v

# Remove specific one
docker rm -f ryu-controller-1
```

## Custom Controller Scripts

If you have custom controller files in `projects/pa2/`, you can modify the compose file:

```yaml
command: ryu-manager --ofp-tcp-listen-port 6653 ryu/app/projects/pa2/my_controller.py
```

## Troubleshooting

### Docker Permission Denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :6653

# Kill the process
sudo kill -9 <PID>
```

### Container Won't Start

```bash
# Check logs
docker logs ryu-controller-1

# Check if image exists
docker images | grep ryu

# Pull image if missing
docker pull osrg/ryu:latest
```

### Network Issues

```bash
# Ensure controllers can reach host
docker network inspect bridge

# Test from container
docker exec -it ryu-controller-1 ping 127.0.0.1
```

## Quick Reference

```bash
# Start all controllers
docker compose -f ryu-controllers-docker-compose.yml up -d

# Check status
docker compose -f ryu-controllers-docker-compose.yml ps

# View logs
docker compose -f ryu-controllers-docker-compose.yml logs -f

# Stop all
docker compose -f ryu-controllers-docker-compose.yml down
```

