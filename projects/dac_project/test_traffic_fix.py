#!/usr/bin/env python3

import requests
import json
import os

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def compare_old_vs_new_measurement():
    """Compare the old (TX-based) vs new (RX-based) traffic measurement"""
    
    config = load_config()
    controller_url = config['floodlight_controller_url']
    
    print("=== TRAFFIC MEASUREMENT COMPARISON ===")
    print("Comparing OLD (TX-based) vs NEW (RX-based) measurements")
    print()
    
    # Get devices and their attachment points
    devices_response = requests.get(f'{controller_url}/wm/device/')
    if devices_response.status_code != 200:
        print("Failed to get devices")
        return
        
    devices_data = devices_response.json()
    devices = devices_data.get('devices', [])
    
    # Build device mapping: IP -> attachment points
    device_mapping = {}
    for device in devices:
        ipv4_addresses = device.get('ipv4', [])
        attachment_points = device.get('attachmentPoint', [])
        
        for ip in ipv4_addresses:
            if ip and ip != '0.0.0.0':
                device_mapping[ip] = attachment_points
    
    # Get switches  
    switches_response = requests.get(f'{controller_url}/wm/core/controller/switches/json')
    if switches_response.status_code != 200:
        print("Failed to get switches")
        return
        
    switches = switches_response.json()
    
    # Build port statistics lookup
    switch_port_stats = {}
    for switch in switches:
        switch_id = switch['switchDPID']
        port_url = f'{controller_url}/wm/core/switch/{switch_id}/port/json'
        port_response = requests.get(port_url)
        
        if port_response.status_code == 200:
            port_data = port_response.json()
            ports = port_data.get('port_reply', [{}])[0].get('port', [])
            
            for port in ports:
                port_number = port.get('port_number')
                if port_number != 'local' and port_number is not None:
                    rx_packets = int(port.get('receive_packets', 0))
                    tx_packets = int(port.get('transmit_packets', 0))
                    rx_bytes = int(port.get('receive_bytes', 0))
                    tx_bytes = int(port.get('transmit_bytes', 0))
                    
                    switch_port_key = f"{switch_id}:{port_number}"
                    switch_port_stats[switch_port_key] = {
                        'rx_packets': rx_packets,
                        'tx_packets': tx_packets,
                        'rx_bytes': rx_bytes,
                        'tx_bytes': tx_bytes
                    }
    
    # Compare measurements for each device
    print("Device Traffic Comparison:")
    print("=" * 80)
    print(f"{'IP Address':<12} {'OLD (TX)':<20} {'NEW (RX)':<20} {'Difference':<20}")
    print("-" * 80)
    
    for ip, attachment_points in sorted(device_mapping.items()):
        old_packets = 0  # TX-based (background traffic TO host)
        new_packets = 0  # RX-based (traffic FROM host)
        old_bytes = 0
        new_bytes = 0
        
        # Calculate both measurements
        for attachment in attachment_points:
            switch_dpid = attachment.get('switch', '') or attachment.get('switchDPID', '')
            port_num = str(attachment.get('port', ''))
            
            switch_port_key = f"{switch_dpid}:{port_num}"
            if switch_port_key in switch_port_stats:
                port_stats = switch_port_stats[switch_port_key]
                
                # Old method (TX - traffic TO host)
                old_packets += port_stats['tx_packets']
                old_bytes += port_stats['tx_bytes']
                
                # New method (RX - traffic FROM host)  
                new_packets += port_stats['rx_packets']
                new_bytes += port_stats['rx_bytes']
        
        # Calculate difference
        packet_diff = old_packets - new_packets
        byte_diff = old_bytes - new_bytes
        
        print(f"{ip:<12} {old_packets:>8} pkt, {old_bytes:>8} B   {new_packets:>8} pkt, {new_bytes:>8} B   {packet_diff:>+8} pkt, {byte_diff:>+8} B")
    
    print("-" * 80)
    print()
    print("EXPLANATION:")
    print("• OLD (TX): Measures traffic sent TO hosts (includes background network traffic)")
    print("• NEW (RX): Measures traffic sent FROM hosts (actual host-generated traffic)")
    print("• Difference: Shows how much background traffic was being incorrectly attributed to hosts")
    print()
    print("The NEW measurement is more accurate for detecting suspicious host activity!")

if __name__ == "__main__":
    try:
        compare_old_vs_new_measurement()
    except Exception as e:
        print(f"Error: {e}")
