#!/bin/bash
# UFW firewall rules for bottradingcrypto production VPS.
# Only SSH/HTTP/HTTPS are public; Postgres (5432) and backend (8000) stay
# internal (they bind to 127.0.0.1 in docker-compose.prod.yml). Run as a
# sudo-capable user on the VPS. Review before running — `ufw enable` can drop
# your SSH session if port 22 isn't allowed first (it is, below).
set -euo pipefail

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (Nginx / Certbot)
sudo ufw allow 443/tcp   # HTTPS (Nginx)
sudo ufw --force enable
sudo ufw status verbose
