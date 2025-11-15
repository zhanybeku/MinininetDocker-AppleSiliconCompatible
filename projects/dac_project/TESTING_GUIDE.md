# Testing Role-Based Protocol Enforcement

This guide explains how to test the role-based protocol enforcement in Mininet.

## Setup Steps

### 1. Start Floodlight Controller
Make sure Floodlight is running and accessible at `http://localhost:8080`

### 2. Start the DAC Application
In a terminal, run:
```bash
cd projects/dac_project
python3 dac_app.py
```

You should see output like:
```
[Main] Installing role-based protocol enforcement rules...
[Policy] Installing role-based protocol rules...
[Policy] Blocked SSH (port 22) for 10.0.0.1 (role: guest)
[Policy] Blocked RDP (port 3389) for 10.0.0.1 (role: guest)
[Policy] Blocked FTP (port 21) for 10.0.0.1 (role: guest)
...
[Policy] Role-based rules installed: X/Y successful
```

### 3. Start Mininet Topology
In another terminal, run:
```bash
cd projects/dac_project
sudo python3 topology.py
```

Wait for the network to initialize (you'll see a countdown).

## Testing Guest Role (Current Configuration)

All hosts (10.0.0.1 - 10.0.0.9) are currently configured as **guest** role.

**Guest permissions:**
- ✅ **Allowed**: HTTP (80), HTTPS (443), DNS (53), NTP (123)
- ❌ **Blocked**: SSH (22), RDP (3389), FTP (21), SMTP (25), SNMP (161), Telnet (23)

## Test Commands in Mininet CLI

Once in the Mininet CLI, run these tests:

### Test 1: Basic Connectivity (Should Work)
```bash
# Ping should work (ICMP is not blocked)
h1 ping -c 3 h2
```
**Expected Result**: ✅ Success - packets should be received

### Test 2: SSH Port Connectivity (Testing ACL Rules)
**Note**: Use bash's built-in TCP redirection to test port connectivity.

```bash
# Test SSH port (22) connectivity using bash /dev/tcp
# From admin (h1) to admin (h4) - should connect quickly (not blocked)
h1 timeout 3 bash -c 'echo > /dev/tcp/10.0.0.4/22' && echo "REACHABLE" || echo "BLOCKED/TIMEOUT"

# From guest (h3) to employee (h2) - should timeout (blocked by ACL)
h3 timeout 3 bash -c 'echo > /dev/tcp/10.0.0.2/22' && echo "REACHABLE" || echo "BLOCKED/TIMEOUT"

# Test from guest to admin - should timeout (blocked)
h3 timeout 3 bash -c 'echo > /dev/tcp/10.0.0.1/22' && echo "REACHABLE" || echo "BLOCKED/TIMEOUT"

# Alternative: Test with connection attempt (shows connection refused if reachable)
h1 timeout 3 bash -c '</dev/tcp/10.0.0.4/22' 2>&1 && echo "CONNECTED" || echo "FAILED"
```
**Expected Results**: 
- ✅ Admin to Admin: "REACHABLE" or connection succeeds (port not blocked by ACL)
- ❌ Guest/Employee: "BLOCKED/TIMEOUT" (blocked by ACL rules)

**Understanding the Different Responses**:

| Response | What It Means | ACL Status | Server Status |
|----------|---------------|------------|----------------|
| **"Connection refused"** | Port is reachable, but no server listening | ✅ **ALLOWED** | ❌ No server |
| **"BLOCKED/TIMEOUT"** | Connection times out (waits 3 seconds) | ❌ **BLOCKED** | N/A |
| **"REACHABLE"** | Connection succeeds quickly | ✅ **ALLOWED** | ✅ Server responding |

**Examples**:

1. **Admin → Admin (ACL allows, no server)**:
   ```bash
   h1 timeout 3 bash -c 'echo > /dev/tcp/10.0.0.4/22' && echo "REACHABLE" || echo "BLOCKED/TIMEOUT"
   ```
   **Output**: `bash: connect: Connection refused` → `BLOCKED/TIMEOUT`
   - The connection attempt **succeeds immediately** (ACL allows it)
   - But gets "Connection refused" because no server is listening
   - The `timeout` command sees the error and prints "BLOCKED/TIMEOUT"
   - **This means ACL is working correctly!**

2. **Guest → Admin (ACL blocks)**:
   ```bash
   h3 timeout 3 bash -c 'echo > /dev/tcp/10.0.0.1/22' && echo "REACHABLE" || echo "BLOCKED/TIMEOUT"
   ```
   **Output**: (waits 3 seconds) → `BLOCKED/TIMEOUT`
   - The connection **hangs/times out** (ACL blocks it at the switch)
   - No immediate response, just waits until timeout
   - **This means ACL is blocking correctly!**

3. **Admin → Admin (ACL allows, server running)**:
   ```bash
   # After starting SSH servers
   h1 timeout 3 bash -c 'echo > /dev/tcp/10.0.0.4/22' && echo "REACHABLE" || echo "BLOCKED/TIMEOUT"
   ```
   **Output**: `REACHABLE`
   - Connection succeeds immediately
   - Server responds
   - **Perfect! Everything working!**

**Key Point**: "Connection refused" = **GOOD** (ACL allows, just no server). "Timeout" = **GOOD** (ACL blocks as expected).

#### Quick SSH Status Check
To check SSH port status on all hosts, use the provided script:
```bash
# From Mininet CLI - use full path
sh /Users/zhanybek.bekbolat/Desktop/Code/SDN/MinininetDocker-AppleSiliconCompatible/projects/dac_project/check_ssh_status.sh

# Or if you started Mininet from the dac_project directory:
sh check_ssh_status.sh
```

This will show:
- ✅ **REACHABLE**: ACL allows connection, server is responding
- ⚠️ **CONNECTION REFUSED**: ACL allows connection, but no server listening (this is expected if SSH servers aren't started)
- ⏱️ **TIMEOUT**: Connection blocked by ACL (expected for guests/employees)

#### Starting SSH Servers for Testing
By default, Mininet hosts don't have SSH servers running. To test SSH connectivity properly, you can start simple TCP listeners on port 22:

```bash
# From Mininet CLI - use full path
sh /Users/zhanybek.bekbolat/Desktop/Code/SDN/MinininetDocker-AppleSiliconCompatible/projects/dac_project/start_ssh_servers.sh

# Or if you started Mininet from the dac_project directory:
sh start_ssh_servers.sh
```

This starts simple TCP listeners on port 22 for all hosts. After starting them, you can test SSH connectivity:
```bash
# Admin to Admin - should now show "REACHABLE" or get a response
h1 timeout 3 bash -c 'echo > /dev/tcp/10.0.0.4/22' && echo "REACHABLE" || echo "BLOCKED/TIMEOUT"

# Guest to Admin - should still timeout (blocked by ACL)
h3 timeout 3 bash -c 'echo > /dev/tcp/10.0.0.1/22' && echo "REACHABLE" || echo "BLOCKED/TIMEOUT"
```

To stop all SSH listeners:
```bash
for i in {1..9}; do h$i pkill -f 'python3 -c'; done
```

**Important**: The "Connection refused" error you're seeing is actually **correct behavior** - it means:
1. ✅ The ACL rule is working (port 22 is reachable for admin roles)
2. ⚠️ No SSH server is listening (which is normal for Mininet hosts)

If you want to verify SSH connectivity works end-to-end, use `start_ssh_servers.sh` to start listeners.

### Test 3: HTTP Connection (Should Work)
```bash
# Start a simple HTTP server on h2
h2 python3 -m http.server 80 &

# Try to connect from h1
h1 curl -m 5 http://10.0.0.2:80
```
**Expected Result**: ✅ Success - HTTP connection works (or gets HTTP response)

### Test 4: FTP Connection (Should Be Blocked)
```bash
# Try to connect via FTP (port 21)
h1 ftp 10.0.0.2
# Or use telnet to test port 21
h1 telnet 10.0.0.2 21
```
**Expected Result**: ❌ Connection timeout - FTP is blocked for guests

### Test 5: HTTPS Connection (Should Work)
```bash
# If you have an HTTPS server running, test it
h1 curl -m 5 -k https://10.0.0.2:443
```
**Expected Result**: ✅ Success (if server is running) - HTTPS is allowed

### Test 6: RDP Connection (Should Be Blocked)
```bash
# Test RDP port 3389
h1 telnet 10.0.0.2 3389
# Or use nc (netcat)
h1 nc -zv 10.0.0.2 3389
```
**Expected Result**: ❌ Connection timeout - RDP is blocked for guests

### Test 7: DNS Query (Should Work)
```bash
# Test DNS (port 53)
h1 dig @10.0.0.2 google.com
# Or simpler
h1 nslookup google.com 10.0.0.2
```
**Expected Result**: ✅ Success - DNS is allowed (if DNS server is running)

## Advanced Testing: Test Different Roles

To test different roles, you can modify `users.json`:

### Test Employee Role
Edit `users.json` and change one host to employee:
```json
{
  "ip": "10.0.0.1",
  "role": "employee",
  ...
}
```

Then restart `dac_app.py` to reload the rules.

**Employee permissions:**
- ✅ **Allowed**: HTTP, HTTPS, DNS, SMTP, NTP
- ⚠️ **Restricted**: FTP
- ❌ **Blocked**: SSH, RDP, SNMP, Telnet

### Test Admin Role
Change a host to admin:
```json
{
  "ip": "10.0.0.1",
  "role": "admin",
  ...
}
```

**Admin permissions:**
- ✅ **Allowed**: All protocols (SSH, RDP, FTP, HTTP, HTTPS, DNS, SMTP, SNMP, NTP)
- ❌ **Blocked**: None

## Verification Commands

### Check ACL Rules in Floodlight
You can verify rules are installed by checking Floodlight's REST API:
```bash
curl http://localhost:8080/wm/acl/rules/json
```

### Monitor DAC App Output
Watch the `dac_app.py` terminal for:
- Policy installation messages
- Security alerts if violations are detected
- Analytics showing traffic rates

## Expected Behavior Summary

| Protocol | Port | Guest | Employee | Admin |
|----------|------|-------|----------|-------|
| HTTP     | 80   | ✅     | ✅        | ✅     |
| HTTPS    | 443  | ✅     | ✅        | ✅     |
| DNS      | 53   | ✅     | ✅        | ✅     |
| SSH      | 22   | ❌     | ❌        | ✅     |
| RDP      | 3389 | ❌     | ❌        | ✅     |
| FTP      | 21   | ❌     | ⚠️        | ✅     |
| SMTP     | 25   | ❌     | ✅        | ✅     |

## Troubleshooting

1. **Rules not installing**: Check that Floodlight is running and accessible
2. **Connections still working when blocked**: 
   - Verify rules were installed (check dac_app.py output)
   - Check Floodlight ACL rules via REST API
   - Ensure you're testing the correct ports
3. **Can't connect to allowed protocols**: 
   - Make sure a server is running on the target host
   - Check firewall settings on the host
   - Verify network connectivity with ping first
4. **SSH shows "Connection refused"**: 
   - This is **expected behavior** if SSH servers aren't running
   - "Connection refused" means the ACL allows the connection (port is reachable), but no server is listening
   - To test SSH connectivity, run `sh /full/path/to/start_ssh_servers.sh` to start TCP listeners on port 22
   - Use `sh /full/path/to/check_ssh_status.sh` to verify SSH port status across all hosts
5. **How to verify SSH is enabled on hosts**:
   - Run `sh /full/path/to/check_ssh_status.sh` to see current status
   - If you see "CONNECTION REFUSED" for admin→admin connections, ACL is working but servers need to be started
   - Run `sh /full/path/to/start_ssh_servers.sh` to start listeners
   - Re-run `sh /full/path/to/check_ssh_status.sh` to verify servers are responding

