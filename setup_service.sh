#!/bin/bash
# Script to setup systemd service for auto-start

echo "Setting up systemd service..."

# Copy service file
sudo cp ghaza_una_fact_checker_api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable ghaza_una_fact_checker_api

# Start service
sudo systemctl start ghaza_una_fact_checker_api

# Check status
echo ""
echo "Service status:"
sudo systemctl status ghaza_una_fact_checker_api

echo ""
echo "To view logs: sudo journalctl -u ghaza_una_fact_checker_api -f"
echo "To restart: sudo systemctl restart ghaza_una_fact_checker_api"

