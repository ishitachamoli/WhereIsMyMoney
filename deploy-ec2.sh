#!/bin/bash
# EC2 Setup Script for WIMM
# Run this on a fresh EC2 instance (Amazon Linux 2023 or Ubuntu 22.04)
# Usage: curl -sSL <raw-github-url>/deploy-ec2.sh | bash

set -e

echo "🚀 Setting up WIMM on EC2..."

# ============================================================================
# Docker Setup: Install engine + plugins (Compose + BuildX)
# ============================================================================
echo "📦 Setting up Docker and plugins..."

# Docker engine (only if not already installed)
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker engine..."
    sudo yum update -y 2>/dev/null || sudo apt-get update -y
    sudo yum install -y docker 2>/dev/null || sudo apt-get install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    echo "⚠️  Docker engine installed. You may need to log out and back in for group permissions."
    echo "   Then re-run this script."
    exit 0
fi

# Always ensure plugins directory exists
sudo mkdir -p /usr/local/lib/docker/cli-plugins

# Always install/update Docker Compose plugin
echo "📦 Installing/updating Docker Compose plugin..."
sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Always install/update Docker BuildX plugin
echo "📦 Installing/updating Docker BuildX plugin..."
BUILDX_VERSION=$(curl -s https://api.github.com/repos/docker/buildx/releases/latest | grep '"tag_name"' | sed 's/.*"tag_name": "//;s/".*//')
sudo curl -SL "https://github.com/docker/buildx/releases/download/${BUILDX_VERSION}/buildx-${BUILDX_VERSION}.linux-amd64" -o /usr/local/lib/docker/cli-plugins/docker-buildx
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx

# Verify installations
echo "✅ Docker $(docker --version)"
echo "✅ Compose $(docker compose version)"
echo "✅ BuildX $(docker buildx version)"

# Use modern docker compose command (plugin)
COMPOSE="docker compose"

# Clone repo (if not already cloned)
if [ -f "docker-compose.yml" ]; then
    echo "📂 Already in project directory, skipping clone..."
else
    echo "📥 Cloning repository..."
    git clone https://github.com/tchamoli/whereIsMyMoneyGoing.git
    cd whereIsMyMoneyGoing
fi

# Create .env file
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file..."
    PUBLIC_IP=$(curl -s --max-time 5 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
    cat > .env << EOF
DB_PASSWORD=$(openssl rand -hex 16)
CORS_ORIGINS=*
NEXT_PUBLIC_API_URL=http://${PUBLIC_IP}:8080
ENVIRONMENT=production
EOF
    echo "✅ .env created with random DB password"
fi

# Build and start
echo "🏗️  Building and starting services..."
$COMPOSE up -d --build

echo ""
echo "✅ WIMM is running!"
PUBLIC_IP=$(curl -s --max-time 5 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
echo "🌐 App: http://${PUBLIC_IP}"
echo "🔌 API: http://${PUBLIC_IP}:8080/health"
echo "📊 Health: http://${PUBLIC_IP}:8080/health"
