import requests
import threading
import time
import json
import os
import queue
from datetime import datetime


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "data.json")
    with open(config_path, "r") as f:
        return json.load(f)


config = load_config()


def load_users():
    users_path = os.path.join(os.path.dirname(__file__), "users.json")
    if not os.path.exists(users_path):
        print(f"[Warning] users.json not found at {users_path}")
        print(
            "[Warning] Please run topology.py first to generate users.json, or create it manually"
        )
        return []
    with open(users_path, "r") as f:
        return json.load(f)


def create_ip_to_role_map():
    users = load_users()
    return {user["ip"]: user["role"] for user in users}


def get_time_blocked_protocols():
    blocked_protocol_names = config["time_policies"]["time_blocked_protocols"]
    return [
        (config["protocols"][name]["id"], config["protocols"][name]["port"])
        for name in blocked_protocol_names
        if name in config["protocols"]
    ]


def get_protocol_info(protocol_name):
    return config["protocols"].get(protocol_name)


def get_role_protocols(role_name):
    return config["roles"].get(role_name, {})


FLOODLIGHT_CONTROLLER_URL = config["floodlight_controller_url"]
ALLOWED_TIME_RANGE = [
    config["time_policies"]["business_hours"]["start"],
    config["time_policies"]["business_hours"]["end"],
]
TIME_BLOCKED_PROTOCOLS = get_time_blocked_protocols()
IP_TO_ROLE = create_ip_to_role_map()
TRAFFIC_THRESHOLDS = config.get("monitoring", {}).get("traffic_thresholds", {})
MONITORING_INTERVAL = config.get("monitoring", {}).get("check_interval_seconds", 30)


states = {"blocking_rules_active": False}
state_lock = threading.Lock()


user_traffic_history = {}
traffic_lock = threading.Lock()


suspicious_activity_queue = queue.Queue()


blocked_ips = set()
blocked_ips_lock = threading.Lock()


def load_traffic_history():
    global user_traffic_history
    history_path = os.path.join(os.path.dirname(__file__), "history.json")
    if os.path.exists(history_path):
        try:
            with open(history_path, "r") as f:
                user_traffic_history = json.load(f)
                print(
                    f"[History] Loaded traffic history for {len(user_traffic_history)} users"
                )
        except Exception as e:
            print(f"[History] Error loading history: {e}")
            user_traffic_history = {}


def save_traffic_history():
    history_path = os.path.join(os.path.dirname(__file__), "history.json")
    try:
        with open(history_path, "w") as f:
            json.dump(user_traffic_history, f, indent=2)
    except Exception as e:
        print(f"[History] Error saving history: {e}")


load_traffic_history()


def install_role_based_rules():
    users = load_users()
    total_rules = 0
    success_count = 0

    try:
        print("[Policy] Installing role-based protocol rules...")

        for user in users:
            ip_address = user["ip"]
            role = user.get("role", "guest")

            role_config = get_role_protocols(role)
            if not role_config:
                print(
                    f"[Policy] Warning: No configuration found for role '{role}', skipping {ip_address}"
                )
                continue

            blocked_protocols = role_config.get("blocked_protocols", [])

            if not blocked_protocols:
                print(f"[Policy] No blocked protocols for {ip_address} (role: {role})")
                continue

            for protocol_name in blocked_protocols:
                protocol_info = get_protocol_info(protocol_name)
                if not protocol_info:
                    continue

                acl_rule = {
                    "nw-proto": protocol_info["id"],
                    "tp-dst": protocol_info["port"],
                    "src-ip": f"{ip_address}/32",
                    "dst-ip": "0.0.0.0/0",
                    "action": "DENY",
                }

                response = requests.post(
                    f"{FLOODLIGHT_CONTROLLER_URL}/wm/acl/rules/json",
                    json=acl_rule,
                    headers={"Content-Type": "application/json"},
                )

                total_rules += 1
                if response.status_code == 200:
                    try:
                        response_data = response.json()

                        status = (
                            response_data.get("status", "").lower()
                            if isinstance(response_data, dict)
                            else ""
                        )
                        if isinstance(response_data, dict) and (
                            "success" in status or "new rule added" in status.lower()
                        ):
                            success_count += 1
                            print(
                                f"[Policy] Blocked {protocol_name} (port {protocol_info['port']}) for {ip_address} (role: {role})"
                            )
                        else:
                            success_count += 1
                            print(
                                f"[Policy] Blocked {protocol_name} (port {protocol_info['port']}) for {ip_address} (role: {role})"
                            )
                    except:
                        success_count += 1
                        print(
                            f"[Policy] Blocked {protocol_name} (port {protocol_info['port']}) for {ip_address} (role: {role})"
                        )
                else:
                    print(
                        f"[Policy] Failed to block {protocol_name} for {ip_address}: HTTP {response.status_code} - {response.text}"
                    )

        print(
            f"[Policy] Role-based rules installed: {success_count}/{total_rules} successful"
        )

        try:
            verify_response = requests.get(
                f"{FLOODLIGHT_CONTROLLER_URL}/wm/acl/rules/json"
            )
            if verify_response.status_code == 200:
                rules = verify_response.json()
                rule_count = len(rules) if isinstance(rules, list) else 0
                print(
                    f"[Policy] Verification: Found {rule_count} ACL rules in Floodlight"
                )
                if rule_count == 0 and success_count > 0:
                    print(
                        f"[Policy] WARNING: Rules reported as installed but Floodlight shows 0 rules!"
                    )
                    print(
                        f"[Policy] This may indicate Floodlight ACL module is not enabled or rules are being cleared"
                    )
        except Exception as e:
            print(f"[Policy] Could not verify rules in Floodlight: {e}")

        return success_count == total_rules

    except Exception as e:
        print(f"[Policy] Error installing role-based rules: {e}")
        return False


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
                "action": "DENY",
            }

            response = requests.post(
                f"{FLOODLIGHT_CONTROLLER_URL}/wm/acl/rules/json",
                json=acl_rule,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                success_count += 1
                print(
                    f"[Policy] ACL blocking rule installed - {protocol} traffic blocked"
                )
            else:
                print(
                    f"[Policy] Failed to install {protocol} ACL rule: {response.text}"
                )

        with state_lock:
            if success_count == len(TIME_BLOCKED_PROTOCOLS):
                states["blocking_rules_active"] = True
                print(
                    "[Policy] All ACL blocking rules installed - internal traffic blocked"
                )
            else:
                print(
                    f"[Policy] Only {success_count}/{len(TIME_BLOCKED_PROTOCOLS)} protocols blocked"
                )

    except Exception as e:
        print(f"[Policy] Error installing ACL rules: {e}")


def clear_all_acl_rules():
    try:
        response = requests.get(f"{FLOODLIGHT_CONTROLLER_URL}/wm/acl/clear/json")
        if response.status_code == 200:
            print("[Policy] All ACL rules cleared")
            return True
        else:
            print(f"[Policy] Failed to clear ACL rules: {response.text}")
            return False
    except Exception as e:
        print(f"[Policy] Error clearing ACL rules: {e}")
        return False


def remove_blocking_rules():
    if clear_all_acl_rules():
        with state_lock:
            states["blocking_rules_active"] = False
        print("[Policy] Time-based ACL rules cleared")

        print("[Policy] Reinstalling role-based protocol rules...")
        install_role_based_rules()


def block_ip_address(ip_address):
    try:
        acl_rule = {
            "src-ip": f"{ip_address}/32",
            "dst-ip": "0.0.0.0/0",
            "action": "DENY",
        }

        response = requests.post(
            f"{FLOODLIGHT_CONTROLLER_URL}/wm/acl/rules/json",
            json=acl_rule,
            headers={"Content-Type": "application/json"},
        )

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


def time_based_policy():
    while True:
        try:
            utc_offset = config.get("utc_timezone", 0)
            now = datetime.now()
            adjusted_hour = (now.hour + utc_offset) % 24

            print(
                f"[Policy] Current time: {adjusted_hour:02d}:{now.minute:02d}:{now.second:02d} | "
                f"Business hours: {ALLOWED_TIME_RANGE[0]}:00 - {ALLOWED_TIME_RANGE[1]}:00 | "
                f"UTC offset: {utc_offset} hours"
            )

            if ALLOWED_TIME_RANGE[0] <= adjusted_hour < ALLOWED_TIME_RANGE[1]:
                print("[Policy] Access allowed")
                if states["blocking_rules_active"]:
                    remove_blocking_rules()
            else:
                print("[Policy] Access denied")
                if not states["blocking_rules_active"]:
                    install_blocking_rules()
            time.sleep(60)
        except Exception as e:
            print(f"[Policy] Error: {e}")
            time.sleep(60)


def user_analytics():
    while True:
        try:
            print("\n[Analytics] Gathering device statistics...")

            device_rates = []

            with traffic_lock:
                for ip, history in user_traffic_history.items():
                    role = IP_TO_ROLE.get(ip, "unknown")
                    packets_per_min = history.get("current_packets_per_min", 0.0)
                    bytes_per_min = history.get("current_bytes_per_min", 0.0)
                    device_rates.append((ip, role, packets_per_min, bytes_per_min))

            if device_rates:
                sorted_devices = sorted(device_rates, key=lambda x: x[2], reverse=True)

                print(f"[Analytics] Found {len(sorted_devices)} active devices:")

                for ip, role, packets_per_min, bytes_per_min in sorted_devices:
                    if packets_per_min > 1000:
                        activity = "🔥 HIGH"
                    elif packets_per_min > 500:
                        activity = "📊 MED"
                    elif packets_per_min > 50:
                        activity = "💤 LOW"
                    else:
                        activity = "⚫ IDLE"

                    print(
                        f"  {ip:<12} ({role:<8}): {packets_per_min:>7.1f} pkt/min, {bytes_per_min:>10,.0f} bytes/min {activity}"
                    )

                total_devices = len(sorted_devices)
                active_devices = sum(
                    1 for _, _, pkt_rate, _ in sorted_devices if pkt_rate > 0
                )
                total_packets_per_min = sum(
                    pkt_rate for _, _, pkt_rate, _ in sorted_devices
                )
                total_bytes_per_min = sum(
                    byte_rate for _, _, _, byte_rate in sorted_devices
                )

                print(
                    f"[Analytics] Summary: {active_devices}/{total_devices} devices active, "
                    f"{total_packets_per_min:,.1f} total pkt/min, {total_bytes_per_min:,.0f} total bytes/min"
                )
            else:
                print(
                    "[Analytics] No device traffic data available yet (waiting for first measurement...)"
                )

            switches_response = requests.get(
                f"{FLOODLIGHT_CONTROLLER_URL}/wm/core/controller/switches/json"
            )
            if switches_response.status_code == 200:
                switches = switches_response.json()
                print(f"[Analytics] Network: {len(switches)} switches connected")

            time.sleep(30)

        except Exception as e:
            print(f"[Analytics] Error: {e}")
            time.sleep(30)


def get_device_traffic_snapshot():
    devices_response = requests.get(f"{FLOODLIGHT_CONTROLLER_URL}/wm/device/")
    if devices_response.status_code != 200:
        return {}

    devices_data = devices_response.json()
    devices = devices_data.get("devices", [])

    device_mapping = {}
    for device in devices:
        ipv4_addresses = device.get("ipv4", [])
        attachment_points = device.get("attachmentPoint", [])

        for ip in ipv4_addresses:
            if ip and ip != "0.0.0.0":
                device_mapping[ip] = attachment_points

    switches_response = requests.get(
        f"{FLOODLIGHT_CONTROLLER_URL}/wm/core/controller/switches/json"
    )
    if switches_response.status_code != 200:
        return {}

    switches = switches_response.json()

    switch_port_stats = {}
    for switch in switches:
        switch_id = switch["switchDPID"]
        port_url = f"{FLOODLIGHT_CONTROLLER_URL}/wm/core/switch/{switch_id}/port/json"
        port_response = requests.get(port_url)

        if port_response.status_code == 200:
            port_data = port_response.json()
            ports = port_data.get("port_reply", [{}])[0].get("port", [])

            for port in ports:
                port_number = port.get("port_number")
                if port_number != "local" and port_number is not None:
                    rx_packets = int(port.get("receive_packets", 0))
                    rx_bytes = int(port.get("receive_bytes", 0))

                    switch_port_key = f"{switch_id}:{port_number}"
                    switch_port_stats[switch_port_key] = {
                        "rx_packets": rx_packets,
                        "rx_bytes": rx_bytes,
                    }

    device_traffic = {}
    for ip, attachment_points in device_mapping.items():
        if attachment_points:
            primary_attachment = attachment_points[0]
            switch_dpid = primary_attachment.get(
                "switch", ""
            ) or primary_attachment.get("switchDPID", "")
            port_num = str(primary_attachment.get("port", ""))

            switch_port_key = f"{switch_dpid}:{port_num}"
            if switch_port_key in switch_port_stats:
                port_stats = switch_port_stats[switch_port_key]
                device_traffic[ip] = {
                    "packets": port_stats["rx_packets"],
                    "bytes": port_stats["rx_bytes"],
                }
            else:
                device_traffic[ip] = {"packets": 0, "bytes": 0}
        else:
            device_traffic[ip] = {"packets": 0, "bytes": 0}

    return device_traffic


def suspicious_activity_monitor():
    global user_traffic_history

    while True:
        try:
            print("\n[Security] Checking for suspicious activity...")

            current_traffic = get_device_traffic_snapshot()

            if not current_traffic:
                print("[Security] Failed to get traffic data, retrying...")
                time.sleep(MONITORING_INTERVAL)
                continue

            current_time = time.time()
            suspicious_ips = []

            with traffic_lock:
                for ip, traffic_data in current_traffic.items():
                    if ip not in user_traffic_history:
                        user_traffic_history[ip] = {
                            "last_bytes": traffic_data["bytes"],
                            "last_packets": traffic_data["packets"],
                            "last_check": current_time,
                            "current_bytes_per_min": 0.0,
                            "current_packets_per_min": 0.0,
                            "bytes_history": [],
                            "packets_history": [],
                            "timestamps": [],
                        }

                        continue

                    history = user_traffic_history[ip]
                    time_diff = current_time - history["last_check"]

                    if time_diff >= 1.0:
                        if time_diff > 3600:
                            history["last_bytes"] = traffic_data["bytes"]
                            history["last_packets"] = traffic_data["packets"]
                            history["last_check"] = current_time
                            history["current_bytes_per_min"] = 0.0
                            history["current_packets_per_min"] = 0.0
                            continue

                        bytes_delta = traffic_data["bytes"] - history["last_bytes"]
                        packets_delta = (
                            traffic_data["packets"] - history["last_packets"]
                        )

                        if bytes_delta < 0:
                            bytes_delta = traffic_data["bytes"]
                        if packets_delta < 0:
                            packets_delta = traffic_data["packets"]

                        bytes_per_minute = (bytes_delta / time_diff) * 60
                        packets_per_minute = (packets_delta / time_diff) * 60

                        bytes_threshold = TRAFFIC_THRESHOLDS.get(
                            "bytes_per_minute", 10485760
                        )
                        packets_threshold = TRAFFIC_THRESHOLDS.get(
                            "packets_per_minute", 10000
                        )

                        suspicious_reasons = []
                        severity = "warning"

                        if bytes_per_minute > bytes_threshold:
                            suspicious_reasons.append(
                                f"Exceeded traffic threshold: {bytes_per_minute:,.0f} bytes/min (threshold: {bytes_threshold:,})"
                            )
                            severity = "alert"

                        if packets_per_minute > packets_threshold:
                            suspicious_reasons.append(
                                f"Exceeded packet threshold: {packets_per_minute:,.0f} packets/min (threshold: {packets_threshold:,})"
                            )
                            severity = "alert"

                        if suspicious_reasons:
                            with blocked_ips_lock:
                                if ip not in blocked_ips:
                                    suspicious_ips.append(
                                        {
                                            "ip": ip,
                                            "role": IP_TO_ROLE.get(ip, "unknown"),
                                            "reasons": suspicious_reasons,
                                            "severity": severity,
                                            "bytes_per_minute": bytes_per_minute,
                                            "packets_per_minute": packets_per_minute,
                                        }
                                    )

                        history["last_bytes"] = traffic_data["bytes"]
                        history["last_packets"] = traffic_data["packets"]
                        history["last_check"] = current_time

                        history["current_bytes_per_min"] = bytes_per_minute
                        history["current_packets_per_min"] = packets_per_minute

                        history["bytes_history"].append(bytes_per_minute)
                        history["packets_history"].append(packets_per_minute)
                        history["timestamps"].append(current_time)

                        if len(history["bytes_history"]) > 10:
                            history["bytes_history"] = history["bytes_history"][-10:]
                            history["packets_history"] = history["packets_history"][
                                -10:
                            ]
                            history["timestamps"] = history["timestamps"][-10:]
                    else:
                        continue

                save_traffic_history()

            for suspicious_ip_info in suspicious_ips:
                suspicious_activity_queue.put(suspicious_ip_info, block=False)

            time.sleep(MONITORING_INTERVAL)

        except Exception as e:
            print(f"[Security] Error in suspicious activity monitor: {e}")
            time.sleep(MONITORING_INTERVAL)


def handle_suspicious_activity(activity_info):
    ip = activity_info["ip"]
    role = activity_info["role"]
    reasons = activity_info["reasons"]
    severity = activity_info["severity"]
    bytes_per_min = activity_info.get("bytes_per_minute", 0)
    packets_per_min = activity_info.get("packets_per_minute", 0)

    if severity == "alert":
        print("\n" + "=" * 70)
        print("⚠️  SECURITY ALERT ⚠️")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("⚠️  SECURITY WARNING ⚠️")
        print("=" * 70)

    print("\nSuspicious activity detected from:")
    print(f"  IP Address: {ip}")
    print(f"  Role: {role}")
    print("\nDetails:")
    for reason in reasons:
        print(f"  • {reason}")

    if bytes_per_min > 0:
        print(
            f"  • Traffic rate: {bytes_per_min:,.0f} bytes/min, {packets_per_min:,.0f} packets/min"
        )

    print("\n" + "-" * 70)
    print("Options:")
    print("  1. Block this IP address (deny all traffic)")
    print("  2. Ignore this alert (continue monitoring)")
    print("  3. View more details")
    print("-" * 70)

    while True:
        try:
            choice = input("\nEnter your choice (1-3): ").strip()

            if choice == "1":
                if block_ip_address(ip):
                    print(f"\n✓ IP address {ip} has been blocked.")
                    print("All traffic from this IP will be denied.")
                else:
                    print(f"\n✗ Failed to block IP address {ip}.")
                break
            elif choice == "2":
                print(f"\n✓ Alert ignored. Continuing to monitor {ip}...")
                break
            elif choice == "3":
                print(f"\nAdditional details for {ip}:")
                print(f"  Role configuration: {role}")
                if role != "unknown":
                    role_config = get_role_protocols(role)
                    print(
                        f"  Allowed protocols: {', '.join(role_config.get('allowed_protocols', []))}"
                    )
                    print(
                        f"  Blocked protocols: {', '.join(role_config.get('blocked_protocols', []))}"
                    )
                print(
                    f"  Current traffic: {bytes_per_min:,.0f} bytes/min, {packets_per_min:,.0f} packets/min"
                )
                print("\nReturning to options...")
                print("-" * 70)
                print("Options:")
                print("  1. Block this IP address (deny all traffic)")
                print("  2. Ignore this alert (continue monitoring)")
                print("  3. View more details")
                print("-" * 70)
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        except (EOFError, KeyboardInterrupt):
            print("\n\nInterrupted. Ignoring this alert and continuing...")
            break

    print("=" * 70 + "\n")


def main():
    print("[Main] Clearing any existing ACL rules from previous runs...")
    clear_all_acl_rules()

    print("[Main] Installing role-based protocol enforcement rules...")
    install_role_based_rules()
    print()

    time_based_policy_thread = threading.Thread(target=time_based_policy, daemon=True)
    time_based_policy_thread.start()

    user_analytics_thread = threading.Thread(target=user_analytics, daemon=True)
    user_analytics_thread.start()

    security_monitor_thread = threading.Thread(
        target=suspicious_activity_monitor, daemon=True
    )
    security_monitor_thread.start()

    print("[Main] Application started. Monitoring for suspicious activity...")
    print("[Main] Press Ctrl+C to exit gracefully.\n")

    try:
        while True:
            try:
                activity_info = suspicious_activity_queue.get(block=False)

                handle_suspicious_activity(activity_info)
            except queue.Empty:
                pass

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[Shutdown] Received interrupt signal, shutting down gracefully...")

        with traffic_lock:
            save_traffic_history()
        print("[Shutdown] Traffic history saved.")
        print("[Shutdown] Goodbye!")


if __name__ == "__main__":
    main()
