#!/bin/bash

# Script to simulate suspicious activity for testing the security monitoring system
# Usage: ./simulate_suspicious_activity.sh <scenario>
# Scenarios: traffic_flood, blocked_protocol, unauthorized_protocol

SCENARIO=${1:-"help"}

case $SCENARIO in
    "traffic_flood")
        echo "=== Simulating High Traffic (Exceeding Threshold) ==="
        echo "This will generate high traffic to trigger traffic threshold alerts"
        echo "Target IP: 10.0.0.2 (you can change this)"
        echo ""
        echo "Running ping flood (high packet rate)..."
        # Ping flood - generates high packet rate
        ping -f -i 0.01 10.0.0.2 2>/dev/null || echo "Note: ping -f requires root. Try: sudo ping -f -i 0.01 10.0.0.2"
        ;;
    
    "blocked_protocol")
        echo "=== Simulating Blocked Protocol Usage ==="
        echo "Attempting to use SSH (blocked for guest role)..."
        echo "This should trigger a CRITICAL alert"
        echo ""
        echo "Trying SSH connection to 10.0.0.2:22..."
        # Try SSH connection (will fail but generate traffic)
        timeout 5 ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no user@10.0.0.2 2>&1 || true
        echo ""
        echo "Note: You can also try other blocked protocols:"
        echo "  - FTP: ftp 10.0.0.2"
        echo "  - RDP: rdesktop 10.0.0.2 (if installed)"
        ;;
    
    "unauthorized_protocol")
        echo "=== Simulating Unauthorized Protocol ==="
        echo "This scenario would require a protocol not in the allowed list"
        echo "Note: This is harder to simulate without actual services running"
        ;;
    
    "help"|*)
        echo "Usage: ./simulate_suspicious_activity.sh <scenario>"
        echo ""
        echo "Available scenarios:"
        echo "  traffic_flood      - Generate high traffic to exceed thresholds"
        echo "  blocked_protocol    - Attempt to use blocked protocols (SSH, FTP, etc.)"
        echo "  unauthorized_protocol - Use protocols not in allowed list"
        echo ""
        echo "Examples:"
        echo "  ./simulate_suspicious_activity.sh traffic_flood"
        echo "  ./simulate_suspicious_activity.sh blocked_protocol"
        ;;
esac

