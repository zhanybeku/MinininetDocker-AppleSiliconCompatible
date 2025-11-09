import requests
import threading
import time
import json
import os
from datetime import datetime

# Load configuration from JSON file:
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(config_path, 'r') as f:
        return json.load(f)


# Load configuration:
config = load_config()


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


# States:
states = {
    "blocking_rules_active": False
}
state_lock = threading.Lock()


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

    while True:
        print("Main app running...")
        time.sleep(10)


if __name__ == "__main__":
    main()
