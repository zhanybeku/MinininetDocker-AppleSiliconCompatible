import requests
import threading
import time
import json
import os
import queue
from datetime import datetime

# Load configuration from JSON file:
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(config_path, 'r') as f:
        return json.load(f)


# Load configuration:
config = load_config()


# Load users from JSON file:
def load_users():
    users_path = os.path.join(os.path.dirname(__file__), 'users.json')
    with open(users_path, 'r') as f:
        return json.load(f)


# Create IP to role mapping:
def create_ip_to_role_map():
    users = load_users()
    return {user['ip']: user['role'] for user in users}


# Get protocol name from port number:
def get_protocol_by_port(port):
    for protocol_name, protocol_info in config['protocols'].items():
        if str(protocol_info['port']) == str(port):
            return protocol_name
    return None


# Get time-blocked protocols from config
def get_time_blocked_protocols():
    blocked_protocol_names = config['time_policies']['time_blocked_protocols']
    return [(config['protocols'][name]['id'], config['protocols'][name]['port'])
            for name in blocked_protocol_names if name in config['protocols']]


# Utility functions for working with config:
def get_protocol_info(protocol_name):
    return config['protocols'].get(protocol_name)


def get_role_protocols(role_name):
    return config['roles'].get(role_name, {})


def get_protocols_by_names(protocol_names):
    return [(config['protocols'][name]['id'], config['protocols'][name]['port'])
            for name in protocol_names if name in config['protocols']]


# Constants:
FLOODLIGHT_CONTROLLER_URL = config['floodlight_controller_url']
ALLOWED_TIME_RANGE = [config['time_policies']['business_hours']['start'],
                      config['time_policies']['business_hours']['end']]
TIME_BLOCKED_PROTOCOLS = get_time_blocked_protocols()
IP_TO_ROLE = create_ip_to_role_map()
TRAFFIC_THRESHOLDS = config.get('monitoring', {}).get('traffic_thresholds', {})
MONITORING_INTERVAL = config.get('monitoring', {}).get('check_interval_seconds', 30)


# States:
states = {
    "blocking_rules_active": False
}
state_lock = threading.Lock()

# Traffic tracking for suspicious activity detection:
user_traffic_history = {}  # {ip: {'bytes': [], 'packets': [], 'timestamps': [], 'last_check': timestamp}}
traffic_lock = threading.Lock()

# Queue for suspicious activity alerts (thread-safe communication):
suspicious_activity_queue = queue.Queue()

# Track blocked IPs to avoid duplicate blocking:
blocked_ips = set()
blocked_ips_lock = threading.Lock()


# Load traffic history from JSON file:
def load_traffic_history():
    global user_traffic_history
    history_path = os.path.join(os.path.dirname(__file__), 'history.json')
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r') as f:
                user_traffic_history = json.load(f)
                print(f"[History] Loaded traffic history for {len(user_traffic_history)} users")
        except Exception as e:
            print(f"[History] Error loading history: {e}")
            user_traffic_history = {}


# Save traffic history to JSON file:
# Note: Should be called from within traffic_lock context to ensure thread safety
def save_traffic_history():
    history_path = os.path.join(os.path.dirname(__file__), 'history.json')
    try:
        # Note: Assumes traffic_lock is already held by caller
        with open(history_path, 'w') as f:
            json.dump(user_traffic_history, f, indent=2)
    except Exception as e:
        print(f"[History] Error saving history: {e}")


# Load history on startup:
load_traffic_history()


# Install blocking rules:
def install_blocking_rules():
    global states
    success_count = 0
    try:
        for protocol in TIME_BLOCKED_PROTOCOLS:
            acl_rule = {
                "nw-proto": protocol[0],
                "tp-dst": protocol[1],
                "src-ip": "0.0.0.0/0",
                "dst-ip": "0.0.0.0/0",
                "action": "DENY"
            }

            response = requests.post(f'{FLOODLIGHT_CONTROLLER_URL}/wm/acl/rules/json',
                                     json=acl_rule,
                                     headers={'Content-Type': 'application/json'})

            if response.status_code == 200:
                success_count += 1
                print(
                    f"[Policy] ACL blocking rule installed - {protocol} traffic blocked")
            else:
                print(
                    f"[Policy] Failed to install {protocol} ACL rule: {response.text}")

        with state_lock:
            if success_count == len(TIME_BLOCKED_PROTOCOLS):
                states["blocking_rules_active"] = True
                print(
                    "[Policy] All ACL blocking rules installed - internal traffic blocked")
            else:
                print(
                    f"[Policy] Only {success_count}/{len(TIME_BLOCKED_PROTOCOLS)} protocols blocked")

    except Exception as e:
        print(f"[Policy] Error installing ACL rules: {e}")


def remove_blocking_rules():
    try:
        response = requests.get(
            # I NEED TO SPECIFY WHICH RULES TO CLEAR HERE!
            f'{FLOODLIGHT_CONTROLLER_URL}/wm/acl/clear/json')

        if response.status_code == 200:
            with state_lock:
                states["blocking_rules_active"] = False
                print("[Policy] ACL rules cleared - internal traffic allowed")
        else:
            print(f"[Policy] Failed to clear ACL rules: {response.text}")

    except Exception as e:
        print(f"[Policy] Error clearing ACL rules: {e}")


# Block a specific IP address:
def block_ip_address(ip_address):
    """Block all traffic from a specific IP address using ACL rules."""
    try:
        # Block all traffic from this IP
        acl_rule = {
            "src-ip": f"{ip_address}/32",
            "dst-ip": "0.0.0.0/0",
            "action": "DENY"
        }

        response = requests.post(f'{FLOODLIGHT_CONTROLLER_URL}/wm/acl/rules/json',
                                 json=acl_rule,
                                 headers={'Content-Type': 'application/json'})

        if response.status_code == 200:
            with blocked_ips_lock:
                blocked_ips.add(ip_address)
            print(f"[Security] Successfully blocked IP address: {ip_address}")
            return True
        else:
            print(f"[Security] Failed to block IP {ip_address}: {response.text}")
            return False

    except Exception as e:
        print(f"[Security] Error blocking IP {ip_address}: {e}")
        return False


# Unblock a specific IP address:
def unblock_ip_address(ip_address):
    """Unblock a previously blocked IP address by clearing relevant ACL rules."""
    try:
        # Note: This clears all ACL rules, which may affect other rules
        # A more sophisticated implementation would track and remove specific rules
        response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/acl/clear/json')

        if response.status_code == 200:
            with blocked_ips_lock:
                if ip_address in blocked_ips:
                    blocked_ips.remove(ip_address)
            print(f"[Security] Unblocked IP address: {ip_address}")
            # Reinstall time-based blocking rules if they were active
            with state_lock:
                if states["blocking_rules_active"]:
                    install_blocking_rules()
            return True
        else:
            print(f"[Security] Failed to unblock IP {ip_address}: {response.text}")
            return False

    except Exception as e:
        print(f"[Security] Error unblocking IP {ip_address}: {e}")
        return False


# Time-based policy thread function:
def time_based_policy():
    while True:
        try:
            # Adjust for timezone offset from config
            utc_offset = config.get('utc_timezone', 0)
            now = datetime.now()
            adjusted_hour = (now.hour + utc_offset) % 24

            print(
                f"[Policy] Current time: {adjusted_hour:02d}:{now.minute:02d}:{now.second:02d}")
            print(
                f"[Policy] Business hours: {ALLOWED_TIME_RANGE[0]}:00 - {ALLOWED_TIME_RANGE[1]}:00")
            print(f"[Policy] UTC offset: {utc_offset} hours")

            if ALLOWED_TIME_RANGE[0] <= adjusted_hour < ALLOWED_TIME_RANGE[1]:
                print("[Policy] Access allowed")
                if (states["blocking_rules_active"]):
                    remove_blocking_rules()
            else:
                print("[Policy] Access denied")
                if (not states["blocking_rules_active"]):
                    install_blocking_rules()
            time.sleep(60)
        except Exception as e:
            print(f"[Policy] Error: {e}")
            time.sleep(60)


# User analytics thread function:
def user_analytics():
    while True:
        try:
            print("\n[Analytics] Gathering switch statistics...")

            switches_response = requests.get(
                f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/controller/switches/json')

            if switches_response.status_code == 200:
                switches = switches_response.json()
                print(f"[Analytics] Found {len(switches)} connected switches:")

                for switch in switches:
                    switch_id = switch['switchDPID']
                    print(f"  Switch: {switch_id}")

                    # Get port statistics for this switch:
                    port_url = f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/switch/{switch_id}/port/json'
                    port_response = requests.get(port_url)

                    if port_response.status_code == 200:
                        port_data = port_response.json()
                        ports = port_data.get('port_reply', [{}])[
                            0].get('port', [])

                        total_packets = 0
                        total_bytes = 0
                        active_ports = 0

                        for port in ports:
                            if port.get('port_number') != 'local':
                                rx_packets = int(
                                    port.get('receive_packets', 0))
                                tx_packets = int(
                                    port.get('transmit_packets', 0))
                                rx_bytes = int(port.get('receive_bytes', 0))
                                tx_bytes = int(port.get('transmit_bytes', 0))

                                if rx_packets > 0 or tx_packets > 0:
                                    active_ports += 1
                                    total_packets += rx_packets + tx_packets
                                    total_bytes += rx_bytes + tx_bytes

                        print(f"    Active ports: {active_ports}")
                        print(f"    Total packets: {total_packets}")
                        print(f"    Total bytes: {total_bytes:,}")

                    flow_response = requests.get(
                        f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/switch/{switch_id}/flow/json')

                    if flow_response.status_code == 200:
                        flow_data = flow_response.json()
                        flows = flow_data.get('flows', [])
                        print(f"    Active flows: {len(flows)}")
                    else:
                        print("    Flow stats: Not available")

            devices_response = requests.get(
                f'{FLOODLIGHT_CONTROLLER_URL}/wm/device/')
            if devices_response.status_code == 200:
                devices_data = devices_response.json()
                devices = devices_data.get('devices', [])
                print(f"[Analytics] Active devices: {len(devices)}")

            time.sleep(30)

        except Exception as e:
            print(f"[Analytics] Error: {e}")
            time.sleep(30)


# Suspicious activity monitoring function:
def suspicious_activity_monitor():
    global user_traffic_history
    
    while True:
        try:
            print("\n[Security] Checking for suspicious activity...")
            
            # Get all switches to analyze flows
            switches_response = requests.get(
                f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/controller/switches/json')
            
            if switches_response.status_code != 200:
                time.sleep(MONITORING_INTERVAL)
                continue
                
            switches = switches_response.json()
            
            # Track current traffic per user
            current_traffic = {}  # {ip: {'bytes': 0, 'packets': 0, 'protocols': set()}}
            
            # Analyze flows from all switches
            for switch in switches:
                switch_id = switch['switchDPID']
                flow_response = requests.get(
                    f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/switch/{switch_id}/flow/json')
                
                if flow_response.status_code == 200:
                    flow_data = flow_response.json()
                    flows = flow_data.get('flows', [])
                    
                    for flow in flows:
                        match = flow.get('match', {})
                        src_ip = match.get('nw-src', '')
                        dst_port = match.get('tp-dst', '')
                        byte_count = int(flow.get('byteCount', 0))
                        packet_count = int(flow.get('packetCount', 0))
                        
                        # Skip if no source IP
                        if not src_ip or src_ip == '0.0.0.0/0':
                            continue
                            
                        # Extract IP from CIDR if needed
                        if '/' in src_ip:
                            src_ip = src_ip.split('/')[0]
                        
                        # Initialize tracking for this IP
                        if src_ip not in current_traffic:
                            current_traffic[src_ip] = {'bytes': 0, 'packets': 0, 'protocols': set()}
                        
                        # Add traffic
                        current_traffic[src_ip]['bytes'] += byte_count
                        current_traffic[src_ip]['packets'] += packet_count
                        
                        # Detect protocol from destination port
                        if dst_port:
                            protocol = get_protocol_by_port(dst_port)
                            if protocol:
                                current_traffic[src_ip]['protocols'].add(protocol)
            
            # Check each user for suspicious activity
            current_time = time.time()
            suspicious_ips = []  # Collect all suspicious IPs in this check cycle
            
            with traffic_lock:
                for ip, traffic_data in current_traffic.items():
                    user_role = IP_TO_ROLE.get(ip, 'unknown')
                    
                    # Initialize history if needed
                    if ip not in user_traffic_history:
                        user_traffic_history[ip] = {
                            'bytes': [],
                            'packets': [],
                            'timestamps': [],
                            'last_check': current_time
                        }
                    
                    history = user_traffic_history[ip]
                    time_diff = current_time - history['last_check']
                    
                    # Calculate per-minute rates
                    if time_diff > 0:
                        bytes_per_minute = (traffic_data['bytes'] / time_diff) * 60
                        packets_per_minute = (traffic_data['packets'] / time_diff) * 60
                        
                        # Check traffic thresholds
                        bytes_threshold = TRAFFIC_THRESHOLDS.get('bytes_per_minute', 10485760)  # 10MB default
                        packets_threshold = TRAFFIC_THRESHOLDS.get('packets_per_minute', 10000)
                        
                        # Collect suspicious activity details
                        suspicious_reasons = []
                        severity = "warning"
                        
                        if bytes_per_minute > bytes_threshold:
                            suspicious_reasons.append(f"Exceeded traffic threshold: {bytes_per_minute:,.0f} bytes/min (threshold: {bytes_threshold:,})")
                            severity = "alert"
                        
                        if packets_per_minute > packets_threshold:
                            suspicious_reasons.append(f"Exceeded packet threshold: {packets_per_minute:,.0f} packets/min (threshold: {packets_threshold:,})")
                            severity = "alert"
                        
                        # Check protocol violations
                        if user_role != 'unknown':
                            role_config = get_role_protocols(user_role)
                            allowed_protocols = set(role_config.get('allowed_protocols', []))
                            blocked_protocols = set(role_config.get('blocked_protocols', []))
                            
                            used_protocols = traffic_data['protocols']
                            
                            # Check for blocked protocols
                            blocked_used = used_protocols.intersection(blocked_protocols)
                            if blocked_used:
                                suspicious_reasons.append(f"Using BLOCKED protocols: {', '.join(blocked_used)}")
                                severity = "critical"
                            
                            # Check for unauthorized protocols (not in allowed list)
                            unauthorized = used_protocols - allowed_protocols - blocked_protocols
                            # Filter out common system protocols that might not be in config
                            common_system = {'DNS', 'NTP', 'DHCP', 'ARP'}
                            unauthorized = unauthorized - common_system
                            
                            if unauthorized:
                                suspicious_reasons.append(f"Using unauthorized protocols: {', '.join(unauthorized)}")
                                if severity != "critical":
                                    severity = "warning"
                        
                        # If suspicious activity detected, queue it for user interaction
                        if suspicious_reasons:
                            # Check if IP is already blocked to avoid duplicate alerts
                            with blocked_ips_lock:
                                if ip not in blocked_ips:
                                    suspicious_ips.append({
                                        'ip': ip,
                                        'role': user_role,
                                        'reasons': suspicious_reasons,
                                        'severity': severity,
                                        'bytes_per_minute': bytes_per_minute,
                                        'packets_per_minute': packets_per_minute,
                                        'protocols': list(used_protocols) if user_role != 'unknown' else []
                                    })
                        
                        # Update history
                        history['bytes'].append(bytes_per_minute)
                        history['packets'].append(packets_per_minute)
                        history['timestamps'].append(current_time)
                        history['last_check'] = current_time
                        
                        # Keep only last 10 measurements
                        if len(history['bytes']) > 10:
                            history['bytes'] = history['bytes'][-10:]
                            history['packets'] = history['packets'][-10:]
                            history['timestamps'] = history['timestamps'][-10:]
                
                # Save history to file after processing all users
                save_traffic_history()
            
            # Queue suspicious IPs for user interaction (outside the lock to avoid blocking)
            for suspicious_ip_info in suspicious_ips:
                try:
                    suspicious_activity_queue.put(suspicious_ip_info, block=False)
                except queue.Full:
                    # Queue is full, skip this alert (shouldn't happen with unbounded queue)
                    pass
            
            time.sleep(MONITORING_INTERVAL)
            
        except Exception as e:
            print(f"[Security] Error in suspicious activity monitor: {e}")
            time.sleep(MONITORING_INTERVAL)


# Handle suspicious activity interactively:
def handle_suspicious_activity(activity_info):
    """Present user with options to handle suspicious activity."""
    ip = activity_info['ip']
    role = activity_info['role']
    reasons = activity_info['reasons']
    severity = activity_info['severity']
    bytes_per_min = activity_info.get('bytes_per_minute', 0)
    packets_per_min = activity_info.get('packets_per_minute', 0)
    protocols = activity_info.get('protocols', [])
    
    # Display alert based on severity
    if severity == "critical":
        print("\n" + "="*70)
        print("🚨 CRITICAL SECURITY ALERT 🚨")
        print("="*70)
    elif severity == "alert":
        print("\n" + "="*70)
        print("⚠️  SECURITY ALERT ⚠️")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("⚠️  SECURITY WARNING ⚠️")
        print("="*70)
    
    print("\nSuspicious activity detected from:")
    print(f"  IP Address: {ip}")
    print(f"  Role: {role}")
    print("\nDetails:")
    for reason in reasons:
        print(f"  • {reason}")
    
    if bytes_per_min > 0:
        print(f"  • Traffic rate: {bytes_per_min:,.0f} bytes/min, {packets_per_min:,.0f} packets/min")
    if protocols:
        print(f"  • Protocols used: {', '.join(protocols)}")
    
    print("\n" + "-"*70)
    print("Options:")
    print("  1. Block this IP address (deny all traffic)")
    print("  2. Ignore this alert (continue monitoring)")
    print("  3. View more details")
    print("-"*70)
    
    while True:
        try:
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == '1':
                if block_ip_address(ip):
                    print(f"\n✓ IP address {ip} has been blocked.")
                    print("All traffic from this IP will be denied.")
                else:
                    print(f"\n✗ Failed to block IP address {ip}.")
                break
            elif choice == '2':
                print(f"\n✓ Alert ignored. Continuing to monitor {ip}...")
                break
            elif choice == '3':
                print(f"\nAdditional details for {ip}:")
                print(f"  Role configuration: {role}")
                if role != 'unknown':
                    role_config = get_role_protocols(role)
                    print(f"  Allowed protocols: {', '.join(role_config.get('allowed_protocols', []))}")
                    print(f"  Blocked protocols: {', '.join(role_config.get('blocked_protocols', []))}")
                print(f"  Current traffic: {bytes_per_min:,.0f} bytes/min, {packets_per_min:,.0f} packets/min")
                print("\nReturning to options...")
                print("-"*70)
                print("Options:")
                print("  1. Block this IP address (deny all traffic)")
                print("  2. Ignore this alert (continue monitoring)")
                print("  3. View more details")
                print("-"*70)
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        except (EOFError, KeyboardInterrupt):
            print("\n\nInterrupted. Ignoring this alert and continuing...")
            break
    
    print("="*70 + "\n")


# Main function:
def main():
    # Start the time-based policy thread:
    time_based_policy_thread = threading.Thread(
        target=time_based_policy, daemon=True)
    time_based_policy_thread.start()

    # Start the user analytics thread:
    user_analytics_thread = threading.Thread(
        target=user_analytics, daemon=True)
    user_analytics_thread.start()

    # Start the suspicious activity monitoring thread:
    security_monitor_thread = threading.Thread(
        target=suspicious_activity_monitor, daemon=True)
    security_monitor_thread.start()

    print("[Main] Application started. Monitoring for suspicious activity...")
    print("[Main] Press Ctrl+C to exit gracefully.\n")

    try:
        while True:
            # Check for suspicious activity alerts (non-blocking)
            try:
                activity_info = suspicious_activity_queue.get(block=False)
                # Pause monitoring and handle the alert interactively
                handle_suspicious_activity(activity_info)
            except queue.Empty:
                # No alerts, continue normal operation
                pass
            
            # Small sleep to prevent busy-waiting
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[Shutdown] Received interrupt signal, shutting down gracefully...")
        # Save traffic history one last time before exit
        with traffic_lock:
            save_traffic_history()
        print("[Shutdown] Traffic history saved.")
        print("[Shutdown] Goodbye!")
        # Daemon threads will automatically terminate when main thread exits


if __name__ == "__main__":
    main()
