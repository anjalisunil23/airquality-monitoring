"""
==============================================================================
Smart Classroom Environmental Monitoring System
ESP32 + DHT22 Simulator & Telemetry Generator
==============================================================================
This utility simulates an active ESP32 microcontroller with a DHT22 sensor,
transmitting realistic temperature and humidity telemetry to the FastAPI backend.

Usage:
  # 1. Seed initial historical data (e.g. 15 readings):
  python simulate_esp32.py --seed 15

  # 2. Continuous real-time streaming (transmits every 4 seconds):
  python simulate_esp32.py --stream

  # 3. Demonstration Walkthrough (cycles through Cool -> Comfortable -> Warm -> Hot):
  python simulate_esp32.py --demo

  # 4. Transmit a single custom reading:
  python simulate_esp32.py --temp 25.4 --hum 58.0
==============================================================================
"""

import argparse
import time
import random
import requests
import sys

DEFAULT_URL = "http://localhost:8000/api/readings"
DEFAULT_DEVICE = "esp32-classroom-01"


def send_reading(url: str, temp: float, hum: float, device_id: str = DEFAULT_DEVICE):
    """Posts a single sensor reading to the backend"""
    payload = {
        "temperature": round(temp, 2),
        "humidity": round(hum, 2),
        "device_id": device_id
    }
    try:
        response = requests.post(url, json=payload, timeout=4)
        if response.status_code == 201:
            data = response.json()
            print(f"[SUCCESS] Telemetry Posted: {temp:.1f}°C ({data['temp_status']}) | {hum:.1f}% ({data['humidity_status']}) | ID: {data['id']}")
            return True
        else:
            print(f"[ERROR] HTTP {response.status_code}: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Could not connect to {url}. Is the FastAPI server running?")
        return False
    except Exception as e:
        print(f"[ERROR] Exception during POST: {e}")
        return False


def seed_data(url: str, count: int = 15):
    """Seeds historical readings progressing realistically"""
    print(f"\n[SEED] Generating {count} historical readings...")
    base_temp = 21.0
    base_hum = 48.0

    for i in range(count):
        # Gradual slight drift
        temp = base_temp + (i * 0.3) + random.uniform(-0.4, 0.4)
        hum = base_hum + (i * 0.8) + random.uniform(-1.0, 1.0)
        send_reading(url, temp, hum)
        time.sleep(0.3)
    print("[SEED] Finished seeding data!\n")


def demo_cycle(url: str):
    """
    Cycles sequentially through all 4 temperature thresholds:
    1. Cool (< 18°C)
    2. Comfortable (18°C - 24°C)
    3. Warm (24°C - 30°C)
    4. Hot (> 30°C)
    """
    scenarios = [
        {"name": "Phase 1: Cool State (< 18°C)", "temp": 16.4, "hum": 42.0},
        {"name": "Phase 2: Comfortable State (18°C - 24°C)", "temp": 22.0, "hum": 50.5},
        {"name": "Phase 3: Warm State (24°C - 30°C)", "temp": 27.2, "hum": 64.0},
        {"name": "Phase 4: Hot State (> 30°C)", "temp": 32.8, "hum": 76.5},
    ]

    print("\n=======================================================")
    print(" Running Threshold Walkthrough for MCA Demonstration    ")
    print(" Watch the dashboard dynamically transition its colors!")
    print("=======================================================\n")

    for s in scenarios:
        print(f"\n>>> Simulating {s['name']}...")
        send_reading(url, s["temp"], s["hum"])
        print("Waiting 5 seconds for faculty observation on dashboard...")
        time.sleep(5)

    print("\n[DEMO COMPLETE] All threshold states demonstrated successfully.\n")


def continuous_stream(url: str, interval: float = 4.0):
    """Streams readings continuously like a live ESP32"""
    print(f"\n[STREAM] Streaming live ESP32 telemetry every {interval}s to {url}...")
    print("Press Ctrl+C to stop streaming.\n")

    current_temp = 23.5
    current_hum = 52.0

    try:
        while True:
            # Simulate natural classroom thermal drift
            temp_change = random.uniform(-0.35, 0.35)
            hum_change = random.uniform(-0.7, 0.7)

            current_temp = max(15.0, min(36.0, current_temp + temp_change))
            current_hum = max(20.0, min(85.0, current_hum + hum_change))

            send_reading(url, current_temp, current_hum)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[STREAM] Simulator stopped by user.")


def main():
    parser = argparse.ArgumentParser(description="Smart Classroom ESP32 + DHT22 Simulator")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Backend URL (default: {DEFAULT_URL})")
    parser.add_argument("--seed", type=int, nargs="?", const=15, help="Seed N historical readings (default: 15)")
    parser.add_argument("--stream", action="store_true", help="Continuously stream live sensor readings")
    parser.add_argument("--demo", action="store_true", help="Run full threshold color walkthrough")
    parser.add_argument("--temp", type=float, help="Send a single reading with specific temperature (°C)")
    parser.add_argument("--hum", type=float, help="Send a single reading with specific humidity (%)")

    args = parser.parse_args()

    if args.seed:
        seed_data(args.url, args.seed)
    elif args.demo:
        demo_cycle(args.url)
    elif args.stream:
        continuous_stream(args.url)
    elif args.temp is not None or args.hum is not None:
        t = args.temp if args.temp is not None else 24.0
        h = args.hum if args.hum is not None else 50.0
        send_reading(args.url, t, h)
    else:
        # Default behavior if run without args: seed 10 items then prompt
        seed_data(args.url, 10)
        demo_cycle(args.url)


if __name__ == "__main__":
    main()
