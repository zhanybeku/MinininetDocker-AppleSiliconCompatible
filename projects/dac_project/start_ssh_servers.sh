#!/bin/bash
# Script to start simple TCP listeners on port 22 (SSH) for testing
# Run this from within Mininet CLI using one of these methods:
#   1. sh /full/path/to/start_ssh_servers.sh
#   2. Or from the dac_project directory: sh start_ssh_servers.sh
#   3. Or use: sh /Users/zhanybek.bekbolat/Desktop/Code/SDN/MinininetDocker-AppleSiliconCompatible/projects/dac_project/start_ssh_servers.sh

echo "=========================================="
echo "Starting SSH Port Listeners (Port 22)"
echo "=========================================="
echo ""
echo "This script starts simple TCP listeners on port 22"
echo "to test SSH connectivity and ACL rules."
echo ""
echo "Note: These are simple TCP listeners, not full SSH servers."
echo "They will accept connections to verify ACL rules are working."
echo ""

# Function to start a listener on a host
start_listener() {
    host=$1
    echo "[$host] Starting TCP listener on port 22..."
    $host python3 -c "
import socket
import sys

# Create a TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 22))
sock.listen(1)
print(f'[$host] Listening on port 22...', flush=True)

while True:
    try:
        conn, addr = sock.accept()
        print(f'[$host] Connection from {addr[0]}:{addr[1]}', flush=True)
        conn.send(b'SSH-2.0-MockSSH\r\n')
        conn.close()
    except Exception as e:
        print(f'[$host] Error: {e}', flush=True)
        break
" > /tmp/${host}_ssh.log 2>&1 &
    
    if [ $? -eq 0 ]; then
        echo "  ✅ Started listener on $host (PID: $!)"
    else
        echo "  ❌ Failed to start listener on $host"
    fi
}

# Start listeners on all hosts
echo "Starting listeners on all hosts..."
for i in {1..9}; do
    start_listener "h$i"
    sleep 0.1
done

echo ""
echo "=========================================="
echo "All listeners started!"
echo "=========================================="
echo ""
echo "To verify a listener is running, check from another host:"
echo "  h1 timeout 3 bash -c 'echo > /dev/tcp/10.0.0.4/22' && echo 'REACHABLE' || echo 'BLOCKED'"
echo ""
echo "To stop all listeners, run:"
echo "  for i in {1..9}; do h\$i pkill -f 'python3 -c'; done"
echo ""
echo "Logs are available at: /tmp/h*_ssh.log"
echo ""

