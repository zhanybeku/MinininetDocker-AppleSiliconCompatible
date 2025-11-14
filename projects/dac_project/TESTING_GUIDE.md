# Testing Guide: Simulating Suspicious Activity

This guide explains how to test the interactive suspicious activity detection system using your 3 terminals.

## Setup Overview

You have:
- **Terminal 1**: Running the main application (`dac_app.py`)
- **Terminal 2**: Mininet network topology (with hosts h1-h15, IPs 10.0.0.1 to 10.0.0.15)
- **Terminal 3**: Available for running test commands

## Test Scenarios

### Scenario 1: High Traffic Threshold Alert

**Goal**: Trigger an alert by exceeding the traffic threshold (10MB/min or 10,000 packets/min)

**Steps**:
1. In **Terminal 3**, navigate to the project directory:
   ```bash
   cd /Users/zhanybek.bekbolat/Desktop/Code/SDN/MinininetDocker-AppleSiliconCompatible/projects/dac_project
   ```

2. Generate high traffic from one host to another:
   ```bash
   # Option A: Using the Python traffic generator
   python3 generate_traffic.py 10.0.0.2 60
   
   # Option B: Using ping flood (requires root/sudo)
   sudo ping -f -i 0.01 10.0.0.2
   
   # Option C: Using iperf if available
   # On one host: iperf -s
   # On another: iperf -c <target_ip> -t 60 -b 20M
   ```

3. **Expected Result**: Within 30 seconds (monitoring interval), you should see:
   - An alert in Terminal 1 (where `dac_app.py` is running)
   - The app will pause and prompt you with options
   - Choose option 1 to block the IP, or 2 to ignore

### Scenario 2: Blocked Protocol Usage (CRITICAL Alert)

**Goal**: Trigger a CRITICAL alert by using protocols blocked for the "guest" role

**Blocked protocols for guest role**: SSH, RDP, FTP, SMTP, SNMP, Telnet

**Steps**:
1. In **Terminal 2** (Mininet), access a host:
   ```bash
   mininet> h1 ping -c 1 h2  # First establish connectivity
   ```

2. Try to use a blocked protocol. In **Terminal 3** or from within Mininet:
   ```bash
   # From Mininet CLI:
   mininet> h1 ssh user@10.0.0.2
   
   # Or from Terminal 3 (if you can access the network):
   ssh user@10.0.0.2
   ```

3. **Alternative**: Generate traffic to blocked protocol ports:
   ```bash
   # In Terminal 3, use the traffic generator targeting SSH port:
   python3 generate_traffic.py 10.0.0.2 60 tcp
   # This will try to connect to ports 22, 21, 3389, etc.
   ```

4. **Expected Result**: A CRITICAL SECURITY ALERT should appear in Terminal 1

### Scenario 3: Unauthorized Protocol Usage

**Goal**: Use protocols not in the allowed list for a role

**Steps**:
1. First, you might want to change a user's role in `users.json` to "employee" or "admin" to see different allowed protocols

2. Then try using a protocol that's not in their allowed list

3. **Expected Result**: A SECURITY WARNING should appear

## Quick Test Commands

### From Mininet CLI (Terminal 2):
```bash
# Generate traffic between hosts
mininet> h1 ping -c 1000 h2

# Try SSH (blocked for guest)
mininet> h1 ssh user@10.0.0.2

# Generate continuous ping
mininet> h1 ping h2
```

### From Terminal 3 (outside Mininet):
```bash
cd /Users/zhanybek.bekbolat/Desktop/Code/SDN/MinininetDocker-AppleSiliconCompatible/projects/dac_project

# Generate UDP traffic
python3 generate_traffic.py 10.0.0.2 60

# Generate TCP connection attempts
python3 generate_traffic.py 10.0.0.2 60 tcp

# Use the helper script
./simulate_suspicious_activity.sh traffic_flood
./simulate_suspicious_activity.sh blocked_protocol
```

## Lowering Thresholds for Easier Testing

If you want to trigger alerts more easily, you can temporarily lower the thresholds in `data.json`:

```json
"monitoring": {
  "traffic_thresholds": {
    "bytes_per_minute": 1048576,    // 1MB instead of 10MB
    "packets_per_minute": 1000,      // 1000 instead of 10000
    "alert_on_exceed": true
  },
  "check_interval_seconds": 10        // Check every 10 seconds instead of 30
}
```

**Note**: Remember to restart `dac_app.py` after changing the config!

## Testing Checklist

- [ ] High traffic threshold alert (bytes/min exceeded)
- [ ] High traffic threshold alert (packets/min exceeded)
- [ ] Blocked protocol usage (CRITICAL alert)
- [ ] Unauthorized protocol usage (WARNING alert)
- [ ] Interactive prompt appears and pauses execution
- [ ] Block IP option works correctly
- [ ] Ignore option continues monitoring
- [ ] View details option shows additional information

## Troubleshooting

**No alerts appearing?**
- Check that the monitoring thread is running (you should see "[Security] Checking for suspicious activity..." messages)
- Verify traffic is actually being generated (check Mininet or use `tcpdump`)
- Lower the thresholds temporarily for testing
- Make sure the IP you're testing is in `users.json`

**Can't generate enough traffic?**
- Use multiple hosts simultaneously
- Increase packet size in `generate_traffic.py`
- Use `iperf` if available for more realistic traffic

**Protocol detection not working?**
- Make sure flows are being created in the network
- Check that the Floodlight controller is receiving flow information
- Verify the protocol port mappings in `data.json` are correct

