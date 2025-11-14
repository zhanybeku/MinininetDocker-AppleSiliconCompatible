#!/usr/bin/env python3
"""
Test script to verify the fixed rate calculation works correctly.
This simulates the rate calculation logic to show expected vs actual results.
"""

import time

def simulate_rate_calculation():
    """Simulate the fixed rate calculation logic"""
    
    print("=== Rate Calculation Test ===")
    print("Simulating ping at 10 packets/second (600 packets/minute expected)")
    print()
    
    # Simulate traffic history
    history = {
        'last_raw_bytes': 0,
        'last_raw_packets': 0,
        'last_check': time.time()
    }
    
    # Simulate measurements over time
    measurements = [
        {'time': 30, 'total_packets': 300, 'total_bytes': 30000},   # 30 seconds: 300 packets
        {'time': 60, 'total_packets': 600, 'total_bytes': 60000},   # 60 seconds: 600 packets  
        {'time': 90, 'total_packets': 900, 'total_bytes': 90000},   # 90 seconds: 900 packets
    ]
    
    for i, measurement in enumerate(measurements):
        current_time = history['last_check'] + measurement['time']
        time_diff = current_time - history['last_check']
        
        current_raw_bytes = measurement['total_bytes']
        current_raw_packets = measurement['total_packets']
        
        # Calculate deltas (the fix)
        bytes_delta = current_raw_bytes - history['last_raw_bytes']
        packets_delta = current_raw_packets - history['last_raw_packets']
        
        # Handle first measurement
        if history['last_raw_bytes'] == 0 and history['last_raw_packets'] == 0:
            bytes_delta = current_raw_bytes
            packets_delta = current_raw_packets
        
        # Calculate per-minute rates from deltas
        bytes_per_minute = (bytes_delta / time_diff) * 60 if time_diff > 0 else 0
        packets_per_minute = (packets_delta / time_diff) * 60 if time_diff > 0 else 0
        
        print(f"Measurement {i+1}:")
        print(f"  Time elapsed: {time_diff:.0f} seconds")
        print(f"  Total packets: {current_raw_packets}")
        print(f"  Packet delta: {packets_delta}")
        print(f"  Calculated rate: {packets_per_minute:.0f} packets/minute")
        print(f"  Expected rate: ~600 packets/minute")
        print(f"  ✅ Correct!" if abs(packets_per_minute - 600) < 50 else f"  ❌ Wrong!")
        print()
        
        # Update history for next calculation
        history['last_raw_bytes'] = current_raw_bytes
        history['last_raw_packets'] = current_raw_packets
        history['last_check'] = current_time

def show_old_vs_new():
    """Show the difference between old (broken) and new (fixed) calculation"""
    
    print("=== Old vs New Calculation Comparison ===")
    print()
    
    # Example: After 2 minutes of pinging, switch shows 1200 total packets
    total_packets = 1200
    time_interval = 30  # 30 second monitoring interval
    
    print(f"Scenario: Switch shows {total_packets} total packets after 2 minutes of pinging")
    print(f"Monitoring interval: {time_interval} seconds")
    print()
    
    # Old (broken) calculation
    old_rate = (total_packets / time_interval) * 60
    print(f"OLD (broken) calculation:")
    print(f"  Rate = (total_packets / time_interval) × 60")
    print(f"  Rate = ({total_packets} / {time_interval}) × 60 = {old_rate:.0f} packets/minute")
    print(f"  ❌ WRONG - This treats cumulative count as interval count!")
    print()
    
    # New (fixed) calculation  
    previous_packets = 900  # Previous measurement was 900 packets
    packet_delta = total_packets - previous_packets
    new_rate = (packet_delta / time_interval) * 60
    print(f"NEW (fixed) calculation:")
    print(f"  Delta = current_packets - previous_packets")
    print(f"  Delta = {total_packets} - {previous_packets} = {packet_delta} packets")
    print(f"  Rate = (delta / time_interval) × 60")
    print(f"  Rate = ({packet_delta} / {time_interval}) × 60 = {new_rate:.0f} packets/minute")
    print(f"  ✅ CORRECT - This shows actual traffic rate!")

if __name__ == "__main__":
    simulate_rate_calculation()
    print()
    show_old_vs_new()
