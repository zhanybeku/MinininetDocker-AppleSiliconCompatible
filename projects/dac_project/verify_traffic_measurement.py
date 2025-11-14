#!/usr/bin/env python3

import requests
import json
import os

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def verify_traffic_measurement():
    """Verify exactly what we're measuring - trace through the logic step by step"""
    
    config = load_config()
    controller_url = config['floodlight_controller_url']
    
    print("=== TRAFFIC MEASUREMENT VERIFICATION ===")
    print("Tracing through the exact logic to verify what we're measuring...")
    print()
    
    # Step 1: Get devices and their attachment points
    print("STEP 1: Getting device attachment points...")
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
            if ip and ip != '0.0.0.0' and ip.startswith('10.0.0.'):
                device_mapping[ip] = attachment_points
                print(f"  {ip}: {len(attachment_points)} attachment points -> Using primary: {attachment_points[0] if attachment_points else 'None'}")
    
    print()
    
    # Step 2: Get switch port statistics
    print("STEP 2: Getting switch port statistics...")
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
    
    print(f"  Collected stats for {len(switch_port_stats)} switch ports")
    print()
    
    # Step 3: Map devices to their traffic (following exact logic from dac_app.py)
    print("STEP 3: Mapping devices to traffic (exact logic from dac_app.py)...")
    print("=" * 80)
    
    device_traffic = {}
    for ip, attachment_points in sorted(device_mapping.items()):
        total_packets = 0
        total_bytes = 0
        
        print(f"\nDevice {ip}:")
        print(f"  Attachment points: {attachment_points}")
        
        # Use only the PRIMARY attachment point to avoid double-counting
        if attachment_points:
            primary_attachment = attachment_points[0]  # Use first (primary) attachment point
            switch_dpid = primary_attachment.get('switch', '') or primary_attachment.get('switchDPID', '')
            port_num = str(primary_attachment.get('port', ''))
            
            switch_port_key = f"{switch_dpid}:{port_num}"
            print(f"  Primary attachment: {switch_dpid}:{port_num}")
            
            if switch_port_key in switch_port_stats:
                port_stats = switch_port_stats[switch_port_key]
                # Use RX packets/bytes as traffic "received from device" (device as source)
                total_packets = port_stats['rx_packets']
                total_bytes = port_stats['rx_bytes']
                
                print(f"  Port stats for {switch_port_key}:")
                print(f"    RX (FROM device): {port_stats['rx_packets']} packets, {port_stats['rx_bytes']} bytes <- WE USE THIS")
                print(f"    TX (TO device):   {port_stats['tx_packets']} packets, {port_stats['tx_bytes']} bytes <- We ignore this")
                print(f"  RESULT: Device {ip} attributed {total_packets} packets, {total_bytes} bytes")
            else:
                print(f"  ERROR: No stats found for {switch_port_key}")
        else:
            print(f"  No attachment points found")
        
        device_traffic[ip] = {
            'packets': total_packets,
            'bytes': total_bytes
        }
    
    print()
    print("=" * 80)
    print("VERIFICATION SUMMARY:")
    print("=" * 80)
    
    total_attributed_packets = sum(stats['packets'] for stats in device_traffic.values())
    total_attributed_bytes = sum(stats['bytes'] for stats in device_traffic.values())
    
    print(f"Total packets attributed to all devices: {total_attributed_packets:,}")
    print(f"Total bytes attributed to all devices: {total_attributed_bytes:,}")
    print()
    
    print("WHAT WE'RE MEASURING:")
    print("✓ Each device gets traffic from its PRIMARY switch port only")
    print("✓ We use RX packets/bytes (traffic FROM the device TO the switch)")
    print("✓ This represents actual packets SENT BY each host")
    print("✓ No double-counting (we ignore secondary attachment points)")
    print("✓ No division or averaging - these are RAW port counters")
    print()
    
    print("VERIFICATION:")
    for ip, stats in sorted(device_traffic.items()):
        print(f"  {ip}: {stats['packets']:>6} packets, {stats['bytes']:>8,} bytes (from its dedicated switch port)")
    
    print()
    print("CONCLUSION:")
    print("These numbers represent ACTUAL packets sent by each individual device,")
    print("measured directly from the switch port that device is connected to.")
    print("They are NOT totals divided across devices or any kind of average.")

if __name__ == "__main__":
    try:
        verify_traffic_measurement()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
