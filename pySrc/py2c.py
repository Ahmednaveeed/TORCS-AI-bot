import sys
import argparse
import socket
import time
import csv
from pynput import keyboard
import re
import os
import logging

# Suppress TensorFlow logs before any TensorFlow imports
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress INFO, WARNING, ERROR
logging.getLogger('tensorflow').setLevel(logging.FATAL)  # Only FATAL logs
logging.getLogger('absl').setLevel(logging.FATAL)  # Suppress absl warnings

# Now import driver (which imports TensorFlow)
import driver

# Argument parser setup
parser = argparse.ArgumentParser(description='Python client to connect to the TORCS SCRC server.')
parser.add_argument('--host', dest='host_ip', default='localhost', help='Host IP address')
parser.add_argument('--port', type=int, dest='host_port', default=3001, help='Host port number')
parser.add_argument('--id', dest='id', default='SCR', help='Bot ID')
parser.add_argument('--maxEpisodes', type=int, dest='max_episodes', default=1, help='Max learning episodes')
parser.add_argument('--maxSteps', type=int, dest='max_steps', default=0, help='Max steps')
parser.add_argument('--track', dest='track', default=None, help='Track name')
parser.add_argument('--stage', type=int, dest='stage', default=3, help='Stage')
parser.add_argument('--manual', action='store_true', dest='manual', help='Enable manual control mode')
arguments = parser.parse_args()

print(f'Connecting to {arguments.host_ip} on port {arguments.host_port}')

# Socket setup
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
except socket.error:
    print('Socket creation failed')
    sys.exit(-1)

shutdownClient = False
curEpisode = 0
verbose = True

# Driver init
d = driver.Driver(arguments.stage)
manual_mode = arguments.manual

manual_state = {
    "accel": 0.0, "brake": 0.0, "gear": 1, "steer": 0.0, "clutch": 0.0, "focus": 0, "meta": 0
}

# CSV setup
csv_file = open('DirtTrack.csv', mode='a', newline='')
csv_writer = csv.writer(csv_file)

# Write header matching dataset format
csv_writer.writerow([
    'Angle', 'CurrentLapTime', 'Damage', 'DistanceFromStart', 'DistanceCovered', 'FuelLevel', 'Gear',
    'LastLapTime', 'RacePosition', 'RPM', 'SpeedX', 'SpeedY', 'SpeedZ', 'TrackPosition', 'Z'
] + [f'Opponent_{i+1}' for i in range(36)] + [f'Track_{i+1}' for i in range(19)] + [
    'WheelSpinVelocity_1', 'WheelSpinVelocity_2', 'WheelSpinVelocity_3', 'WheelSpinVelocity_4',
    'Acceleration', 'Braking', 'Clutch', 'Steering'
])

def build_send_string(state):
    return "".join(f"({key} {value})" for key, value in state.items())

def parse_received_data(buf):
    buf = buf.strip().strip('()\x00')
    data = re.findall(r'\(([^)]+)\)', buf)
    parsed_data = {}
    for item in data:
        parts = item.split()
        key = parts[0]
        values = parts[1:]
        try:
            if len(values) == 1:
                parsed_data[key] = float(values[0]) if '.' in values[0] else int(values[0])
            else:
                parsed_data[key] = [float(v) if '.' in v else int(v) for v in values]
        except ValueError:
            parsed_data[key] = values
    return parsed_data

# Manual control
def on_press(key):
    try:
        if key.char == 'w': manual_state["accel"] = 0.5
        elif key.char == 's': manual_state["brake"] = 0.5
        elif key.char == 'a': manual_state["steer"] = 0.1
        elif key.char == 'd': manual_state["steer"] = -0.1
        elif key.char == 'q': manual_state["gear"] -= 1
        elif key.char == 'e': manual_state["gear"] += 1
        elif key.char == 'r':
            if manual_state["gear"] == 1:
                manual_state["gear"] = -1
    except AttributeError:
        pass

def on_release(key):
    if key in [keyboard.Key.esc]: return False
    try:
        if key.char in ['w', 's']: manual_state["accel"] = manual_state["brake"] = 0.0
        elif key.char in ['a', 'd']: manual_state["steer"] = 0.0
    except AttributeError:
        pass

if manual_mode:
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

# Main loop
while not shutdownClient:
    while True:
        try:
            sock.sendto((arguments.id + d.init()).encode(), (arguments.host_ip, arguments.host_port))
            buf, _ = sock.recvfrom(1000)
            if '***identified***' in buf.decode(): break
        except socket.error:
            continue

    while True:
        try:
            buf, _ = sock.recvfrom(1000)
            buf = buf.decode()
        except socket.error:
            continue

        if '***shutdown***' in buf:
            d.onShutDown()
            shutdownClient = True
            break
        elif '***restart***' in buf:
            d.onRestart()
            break

        parsed_data = parse_received_data(buf)

        # Actuator values
        if manual_mode:
            actuator_data = [
                manual_state["steer"], manual_state["accel"],
                manual_state["brake"], manual_state["clutch"]
            ]
        else:
            response = d.drive(buf)
            actuator_data = [
                d.control.steer, d.control.accel,
                d.control.brake, d.control.clutch
            ]

        # Opponents and track edge sensors
        opponents = parsed_data.get("opponents", [1.0] * 36)
        track_edges = parsed_data.get("track", [0.0] * 19)
        wheel_spin = parsed_data.get("wheelSpinVel", [0.0] * 4)
        if len(opponents) != 36:
            opponents = [1.0] * 36
        if len(track_edges) != 19:
            track_edges = [0.0] * 19
        if len(wheel_spin) != 4:
            wheel_spin = [0.0] * 4

        # Final row = sensors + opponents + track + wheel spin + actuators
        row = [
            parsed_data.get("angle", 0.0),
            parsed_data.get("curLapTime", 0.0),
            parsed_data.get("damage", 0.0),
            parsed_data.get("distFromStart", 0.0),
            parsed_data.get("distRaced", 0.0),
            parsed_data.get("fuel", 0.0),
            parsed_data.get("gear", 0),
            parsed_data.get("lastLapTime", 0.0),
            parsed_data.get("racePos", 0),
            parsed_data.get("rpm", 0.0),
            parsed_data.get("speedX", 0.0),
            parsed_data.get("speedY", 0.0),
            parsed_data.get("speedZ", 0.0),
            parsed_data.get("trackPos", 0.0),
            parsed_data.get("z", 0.0)
        ] + opponents + track_edges + wheel_spin + actuator_data

        csv_writer.writerow(row)

        response = build_send_string(manual_state) if manual_mode else response
        print(f"Sending to TORCS: {response}")  # Log the response
        sock.sendto(response.encode(), (arguments.host_ip, arguments.host_port))

    curEpisode += 1
    if curEpisode == arguments.max_episodes:
        shutdownClient = True

# Cleanup
sock.close()
csv_file.close()
if manual_mode:
    listener.stop()