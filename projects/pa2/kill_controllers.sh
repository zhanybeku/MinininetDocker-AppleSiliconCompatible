#!/bin/bash

# Helper script to kill leftover Mininet controllers from previous runs
# This fixes the "Please shut down the controller which is running on port 6653" error

echo "Checking for running controllers..."
echo "Port 6653 status:"
if sudo lsof -i :6653 2>/dev/null; then
    echo "  ⚠️  Port 6653 is in use!"
else
    echo "  ✓ Port 6653 is free"
fi
echo ""

echo "Cleaning up leftover Mininet controllers..."

# Clean up Mininet state
sudo mn -c 2>/dev/null || true

# Kill any ovs-controller processes
sudo pkill -9 ovs-controller 2>/dev/null || true

# Kill any ovs-testcontroller processes
sudo pkill -9 ovs-testcontroller 2>/dev/null || true

# Kill any processes using port 6653 (standard OpenFlow controller port)
sudo lsof -ti:6653 2>/dev/null | xargs sudo kill -9 2>/dev/null || true

echo ""
echo "Verifying cleanup..."
if sudo lsof -i :6653 2>/dev/null; then
    echo "  ⚠️  Warning: Port 6653 is still in use!"
else
    echo "  ✓ Port 6653 is now free"
fi
echo "Cleanup complete!"
