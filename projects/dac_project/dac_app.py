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
            f'{FLOODLIGHT_CONTROLLER_URL}/wm/acl/clear/json') # I NEED TO SPECIFY WHICH RULES TO CLEAR HERE!

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
            now = datetime.now()
            if ALLOWED_TIME_RANGE[0] <= now.hour < ALLOWED_TIME_RANGE[1]:
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


# Main function:
def main():
    # Start the time-based policy thread:
    time_thread = threading.Thread(target=time_based_policy, daemon=True)
    time_thread.start()

    while True:
        print("Main app running...")
        time.sleep(10)


if __name__ == "__main__":
    main()
