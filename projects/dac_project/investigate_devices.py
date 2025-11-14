#!/usr/bin/env python3

import requests
import json
import os

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def investigate_devices():
    """Investigate what devices are being detected by Floodlight"""
    
    config = load_config()
    controller_url = config['floodlight_controller_url']
    
    print("=== DEVICE INVESTIGATION ===")
    print(f"Controller: {controller_url}")
    print()
    
    # Get devices from Floodlight
    try:
        devices_response = requests.get(f'{controller_url}/wm/device/')
        if devices_response.status_code != 200:
            print(f"Failed to get devices: {devices_response.status_code}")
            return
            
        devices_data = devices_response.json()
        devices = devices_data.get('devices', [])
        
        print(f"Total devices detected: {len(devices)}")
        print()
        
        # Analyze each device
        valid_hosts = []
        switches_as_devices = []
        unknown_devices = []
        
        for i, device in enumerate(devices):
            print(f"Device {i+1}:")
            print(f"  MAC: {device.get('mac', ['N/A'])}")
            print(f"  IPv4: {device.get('ipv4', ['N/A'])}")
            print(f"  IPv6: {device.get('ipv6', ['N/A'])}")
            print(f"  VLAN: {device.get('vlan', ['N/A'])}")
            print(f"  Attachment Points: {device.get('attachmentPoint', [])}")
            print(f"  Last Seen: {device.get('lastSeen', 'N/A')}")
            
            # Categorize device
            ipv4_addresses = device.get('ipv4', [])
            mac_addresses = device.get('mac', [])
            
            # Check if it's a valid host (10.0.0.x)
            valid_host_ips = [ip for ip in ipv4_addresses if ip and ip.startswith('10.0.0.') and ip != '10.0.0.0']
            
            if valid_host_ips:
                valid_hosts.append({
                    'ips': valid_host_ips,
                    'macs': mac_addresses,
                    'device': device
                })
                print(f"  → VALID HOST: {valid_host_ips}")
            elif any(mac.startswith('00:00:00:00:00:00:00:') for mac in mac_addresses):
                switches_as_devices.append({
                    'macs': mac_addresses,
                    'device': device
                })
                print(f"  → SWITCH DETECTED AS DEVICE: {mac_addresses}")
            else:
                unknown_devices.append({
                    'ips': ipv4_addresses,
                    'macs': mac_addresses,
                    'device': device
                })
                print(f"  → UNKNOWN DEVICE: IPs={ipv4_addresses}, MACs={mac_addresses}")
            
            print()
        
        # Summary
        print("=== SUMMARY ===")
        print(f"Valid hosts (10.0.0.x): {len(valid_hosts)}")
        print(f"Switches detected as devices: {len(switches_as_devices)}")
        print(f"Unknown devices: {len(unknown_devices)}")
        print(f"Total: {len(valid_hosts) + len(switches_as_devices) + len(unknown_devices)}")
        
        # Expected vs Actual
        print()
        print("=== EXPECTED vs ACTUAL ===")
        print("Expected hosts from topology:")
        for i in range(1, 10):  # h1 to h9
            print(f"  h{i}: 10.0.0.{i}")
        
        print()
        print("Actual valid hosts detected:")
        for host in valid_hosts:
            print(f"  IPs: {host['ips']}, MACs: {host['macs']}")
        
        if switches_as_devices:
            print()
            print("Switches being detected as devices (this is normal):")
            for switch in switches_as_devices:
                print(f"  MACs: {switch['macs']}")
        
        if unknown_devices:
            print()
            print("Unknown devices (investigate these):")
            for unknown in unknown_devices:
                print(f"  IPs: {unknown['ips']}, MACs: {unknown['macs']}")
                
    except Exception as e:
        print(f"Error investigating devices: {e}")

def check_switches():
    """Check switch information"""
    
    config = load_config()
    controller_url = config['floodlight_controller_url']
    
    print("\n=== SWITCH INFORMATION ===")
    
    try:
        switches_response = requests.get(f'{controller_url}/wm/core/controller/switches/json')
        if switches_response.status_code == 200:
            switches = switches_response.json()
            print(f"Connected switches: {len(switches)}")
            
            for switch in switches:
                switch_id = switch['switchDPID']
                print(f"  Switch: {switch_id}")
                
                # Get more details about this switch
                switch_desc_response = requests.get(f'{controller_url}/wm/core/switch/{switch_id}/desc/json')
                if switch_desc_response.status_code == 200:
                    desc_data = switch_desc_response.json()
                    desc = desc_data.get(switch_id, {})
                    print(f"    Description: {desc.get('description', 'N/A')}")
                    print(f"    Hardware: {desc.get('hardware', 'N/A')}")
                    print(f"    Software: {desc.get('software', 'N/A')}")
                
    except Exception as e:
        print(f"Error checking switches: {e}")

if __name__ == "__main__":
    investigate_devices()
    check_switches()
