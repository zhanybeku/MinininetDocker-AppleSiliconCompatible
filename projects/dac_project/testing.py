import requests
import time

FLOODLIGHT_CONTROLLER_URL = "http://localhost:8080"

while True:
    switches_response = requests.get(
                f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/controller/switches/json')
    if switches_response.status_code == 200:
        switches = switches_response.json()
        print(switches)
    else:
        print(f"Failed to get switches: {switches_response.status_code}")
    time.sleep(10)