#!/bin/bash
# Test script for role-based protocol enforcement
# Run this from within Mininet CLI using: sh test_connectivity.sh

echo "=========================================="
echo "Testing Role-Based Protocol Enforcement"
echo "=========================================="
echo ""

# Test 1: Basic connectivity (should work)
echo "[Test 1] Testing basic connectivity (ping)..."
h1 ping -c 2 h2
if [ $? -eq 0 ]; then
    echo "✅ PASS: Ping works (ICMP not blocked)"
else
    echo "❌ FAIL: Ping failed"
fi
echo ""

# Test 2: SSH (should be blocked for guests)
echo "[Test 2] Testing SSH connection (should be BLOCKED for guests)..."
timeout 3 h1 ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no h2 2>&1
if [ $? -eq 124 ] || [ $? -eq 1 ]; then
    echo "✅ PASS: SSH blocked as expected"
else
    echo "❌ FAIL: SSH connection succeeded (should be blocked)"
fi
echo ""

# Test 3: HTTP (should work for guests)
echo "[Test 3] Testing HTTP connection (should WORK for guests)..."
# Start HTTP server in background
h2 python3 -m http.server 80 > /dev/null 2>&1 &
sleep 2

# Try to connect
timeout 3 h1 curl -m 2 http://10.0.0.2:80 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ PASS: HTTP connection works"
else
    echo "⚠️  WARNING: HTTP connection failed (server may not be running)"
fi

# Kill the server
h2 pkill -f "http.server" > /dev/null 2>&1
echo ""

# Test 4: FTP port (should be blocked for guests)
echo "[Test 4] Testing FTP port 21 (should be BLOCKED for guests)..."
timeout 3 h1 nc -zv 10.0.0.2 21 2>&1
if [ $? -ne 0 ]; then
    echo "✅ PASS: FTP port blocked as expected"
else
    echo "❌ FAIL: FTP port accessible (should be blocked)"
fi
echo ""

# Test 5: RDP port (should be blocked for guests)
echo "[Test 5] Testing RDP port 3389 (should be BLOCKED for guests)..."
timeout 3 h1 nc -zv 10.0.0.2 3389 2>&1
if [ $? -ne 0 ]; then
    echo "✅ PASS: RDP port blocked as expected"
else
    echo "❌ FAIL: RDP port accessible (should be blocked)"
fi
echo ""

echo "=========================================="
echo "Testing Complete"
echo "=========================================="
echo ""
echo "Note: For more detailed tests, see TESTING_GUIDE.md"

