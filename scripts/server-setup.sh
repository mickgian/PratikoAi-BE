#!/bin/bash
# =============================================================================
# PratikoAI Server Setup Script
# =============================================================================
# Run on a fresh Hetzner server (Ubuntu 22.04/24.04) as root.
# Usage: ssh root@<server-ip> 'bash -s' < scripts/server-setup.sh
# =============================================================================

set -euo pipefail

DEPLOY_USER="deploy"
APP_DIR="/opt/pratikoai"

echo "=== PratikoAI Server Provisioning ==="
echo "Date: $(date -u)"
echo ""

# --- 1. System Update ---
echo "[1/8] Updating system packages..."
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git ufw fail2ban htop

# --- 2. Install Docker + Compose Plugin ---
echo "[2/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
fi

# Verify Docker Compose plugin
if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose plugin not found."
    exit 1
fi
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker compose version)"

# --- 3. Create Deploy User ---
echo "[3/8] Creating deploy user..."
if ! id "$DEPLOY_USER" &> /dev/null; then
    useradd -m -s /bin/bash "$DEPLOY_USER"
    usermod -aG docker "$DEPLOY_USER"
    echo "User '$DEPLOY_USER' created and added to docker group."
else
    echo "User '$DEPLOY_USER' already exists."
    usermod -aG docker "$DEPLOY_USER"
fi

# Set up SSH key for deploy user (copy from root)
mkdir -p /home/$DEPLOY_USER/.ssh
if [ -f /root/.ssh/authorized_keys ]; then
    cp /root/.ssh/authorized_keys /home/$DEPLOY_USER/.ssh/authorized_keys
fi
chown -R $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER/.ssh
chmod 700 /home/$DEPLOY_USER/.ssh
chmod 600 /home/$DEPLOY_USER/.ssh/authorized_keys 2>/dev/null || true

# --- 4. SSH Hardening ---
echo "[4/8] Hardening SSH..."
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh

# --- 5. Firewall (iptables-persistent) ---
# NOTE: UFW does NOT protect Docker-published ports. Docker inserts its own
# iptables rules in the nat/PREROUTING chain that bypass UFW entirely.
# We use iptables-persistent instead and explicitly block internal service ports.
echo "[5/8] Configuring firewall..."
apt-get install -y iptables-persistent

# Block internal service ports from external access (Docker bypasses UFW)
# Redis - internal only, app connects via Docker network
iptables -C INPUT -p tcp --dport 6379 ! -s 127.0.0.1 -j DROP 2>/dev/null || \
    iptables -I INPUT -p tcp --dport 6379 ! -s 127.0.0.1 -j DROP
iptables -C FORWARD -i eth0 -p tcp --dport 6379 -j DROP 2>/dev/null || \
    iptables -I FORWARD -i eth0 -p tcp --dport 6379 -j DROP

# Redis exporter - internal only
iptables -C INPUT -p tcp --dport 9121 ! -s 127.0.0.1 -j DROP 2>/dev/null || \
    iptables -I INPUT -p tcp --dport 9121 ! -s 127.0.0.1 -j DROP
iptables -C FORWARD -i eth0 -p tcp --dport 9121 -j DROP 2>/dev/null || \
    iptables -I FORWARD -i eth0 -p tcp --dport 9121 -j DROP

# PostgreSQL - internal only
iptables -C INPUT -p tcp --dport 5432 ! -s 127.0.0.1 -j DROP 2>/dev/null || \
    iptables -I INPUT -p tcp --dport 5432 ! -s 127.0.0.1 -j DROP
iptables -C INPUT -p tcp --dport 5433 ! -s 127.0.0.1 -j DROP 2>/dev/null || \
    iptables -I INPUT -p tcp --dport 5433 ! -s 127.0.0.1 -j DROP

# Monitoring stack - internal only
for port in 9090 9187 9100 9093 8081; do
    iptables -C INPUT -p tcp --dport $port ! -s 127.0.0.1 -j DROP 2>/dev/null || \
        iptables -I INPUT -p tcp --dport $port ! -s 127.0.0.1 -j DROP
done

# Persist rules across reboots
netfilter-persistent save
echo "Firewall configured. Blocked internal service ports from external access."

# --- 6. fail2ban ---
echo "[6/8] Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600
findtime = 600
EOF
systemctl enable fail2ban
systemctl restart fail2ban

# --- 7. Swap File ---
echo "[7/8] Setting up swap..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "2GB swap file created."
else
    echo "Swap already exists."
fi

# --- 8. Application Directory ---
echo "[8/8] Creating application directory..."
mkdir -p $APP_DIR/backups
chown -R $DEPLOY_USER:$DEPLOY_USER $APP_DIR

# --- Set up daily backup cron ---
cat > /etc/cron.d/pratikoai-backup << EOF
# Daily database backup at 2:00 AM
0 2 * * * $DEPLOY_USER cd $APP_DIR && docker compose exec -T db pg_dump -U aifinance aifinance | gzip > $APP_DIR/backups/db-backup-\$(date +\%Y\%m\%d).sql.gz 2>/dev/null
# Cleanup backups older than 30 days
0 3 * * * $DEPLOY_USER find $APP_DIR/backups -name "db-backup-*.sql.gz" -mtime +30 -delete 2>/dev/null
EOF
chmod 644 /etc/cron.d/pratikoai-backup

echo ""
echo "=== Server Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Add your SSH public key to /home/$DEPLOY_USER/.ssh/authorized_keys"
echo "  2. Copy docker-compose.yml + docker-compose.qa.yml to $APP_DIR/"
echo "  3. Copy caddy/Caddyfile to $APP_DIR/caddy/"
echo "  4. Create $APP_DIR/.env.qa with real secrets"
echo "  5. Run: docker compose -f docker-compose.yml -f docker-compose.qa.yml up -d"
echo ""
echo "Server IP: $(curl -s ifconfig.me)"
