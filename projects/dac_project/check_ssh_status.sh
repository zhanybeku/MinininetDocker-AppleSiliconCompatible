#!/bin/bash
# Script to check SSH port status on all hosts
# Run this from within Mininet CLI using one of these methods:
#   1. sh /full/path/to/check_ssh_status.sh
#   2. Or from the dac_project directory: sh check_ssh_status.sh
#   3. Or use: sh /Users/zhanybek.bekbolat/Desktop/Code/SDN/MinininetDocker-AppleSiliconCompatible/projects/dac_project/check_ssh_status.sh

echo "=========================================="
echo "Checking SSH Port (22) Status on All Hosts"
echo "=========================================="
echo ""

# Function to check port status
check_port() {
    source_host=$1
    target_ip=$2
    target_host=$3
    
    # Try to connect to port 22 with a short timeout
    timeout 2 bash -c "echo > /dev/tcp/$target_ip/22" 2>/dev/null
    result=$?
    
    if [ $result -eq 0 ]; then
        # Port is reachable, check if something is listening
        # Try to get a response
        response=$(timeout 1 bash -c "exec 3<>/dev/tcp/$target_ip/22; cat <&3" 2>/dev/null | head -c 20)
        if [ -n "$response" ]; then
            echo "  ✅ $source_host → $target_host ($target_ip:22): REACHABLE (server responding)"
        else
            echo "  ✅ $source_host → $target_host ($target_ip:22): REACHABLE (port open, no response)"
        fi
    elif [ $result -eq 124 ]; then
        echo "  ⏱️  $source_host → $target_host ($target_ip:22): TIMEOUT (likely blocked by ACL)"
    elif [ $result -eq 1 ]; then
        # Connection refused means port is reachable but nothing listening
        echo "  ⚠️  $source_host → $target_host ($target_ip:22): CONNECTION REFUSED (ACL allows, no server)"
    else
        echo "  ❌ $source_host → $target_host ($target_ip:22): UNKNOWN ERROR (code: $result)"
    fi
}

# Get role for each host
get_role() {
    ip=$1
    # Extract host number from IP (10.0.0.X)
    host_num=$(echo $ip | cut -d. -f4)
    # Map to role based on users.json pattern
    case $host_num in
        1|4|7) echo "admin" ;;
        2|5|8) echo "employee" ;;
        3|6|9) echo "guest" ;;
        *) echo "unknown" ;;
    esac
}

echo "Testing connectivity from each host to all other hosts..."
echo ""

# Test from admin hosts (should be able to reach other admins)
echo "[Admin → Admin] Should be REACHABLE (SSH allowed for admin):"
check_port "h1" "10.0.0.4" "h4 (admin)"
check_port "h1" "10.0.0.7" "h7 (admin)"
check_port "h4" "10.0.0.1" "h1 (admin)"
check_port "h4" "10.0.0.7" "h7 (admin)"
echo ""

# Test from guest hosts (should be BLOCKED)
echo "[Guest → Admin] Should be BLOCKED (SSH blocked for guest):"
check_port "h3" "10.0.0.1" "h1 (admin)"
check_port "h3" "10.0.0.4" "h4 (admin)"
check_port "h6" "10.0.0.7" "h7 (admin)"
echo ""

# Test from employee hosts (should be BLOCKED - SSH is in blocked_protocols)
echo "[Employee → Admin] Should be BLOCKED (SSH blocked for employee):"
check_port "h2" "10.0.0.1" "h1 (admin)"
check_port "h2" "10.0.0.4" "h4 (admin)"
check_port "h5" "10.0.0.7" "h7 (admin)"
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "Interpretation:"
echo "  ✅ REACHABLE: ACL allows connection, server is responding"
echo "  ⚠️  CONNECTION REFUSED: ACL allows connection, but no server listening"
echo "  ⏱️  TIMEOUT: Connection blocked by ACL (expected for guests/employees)"
echo ""
echo "If you see 'CONNECTION REFUSED' for admin→admin connections,"
echo "that means ACL is working correctly, but SSH servers need to be started."
echo ""
echo "To start SSH listeners, run: sh start_ssh_servers.sh"
echo ""

