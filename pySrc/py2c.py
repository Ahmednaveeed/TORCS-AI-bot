import sys
import argparse
import socket
import driver
import time
import csv
from pynput import keyboard

parser = argparse.ArgumentParser(description='Python client to connect to the TORCS SCRC server.')
parser.add_argument('--host', action='store', dest='host_ip', default='localhost', help='Host IP address')
parser.add_argument('--port', action='store', type=int, dest='host_port', default=3001, help='Host port number')
parser.add_argument('--id', action='store', dest='id', default='SCR', help='Bot ID')
parser.add_argument('--maxEpisodes', action='store', dest='max_episodes', type=int, default=1, help='Max learning episodes')
parser.add_argument('--maxSteps', action='store', dest='max_steps', type=int, default=0, help='Max steps')
parser.add_argument('--track', action='store', dest='track', default=None, help='Track name')
parser.add_argument('--stage', action='store', dest='stage', type=int, default=3, help='Stage')
parser.add_argument('--manual', action='store_true', dest='manual', help='Enable manual control mode')
arguments = parser.parse_args()

print(f'Connecting to {arguments.host_ip} on port {arguments.host_port}')

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
except socket.error:
    print('Socket creation failed')
    sys.exit(-1)

shutdownClient = False
curEpisode = 0
verbose = True

d = driver.Driver(arguments.stage)
manual_mode = arguments.manual

manual_state = {"accel": 0.0, "brake": 0.0, "gear": 1, "steer": 0.0, "clutch": 0.0, "focus": 0, "meta": 0}

def build_send_string(state):
    return "".join(f"({key} {value})" for key, value in state.items())

import re

def parse_received_data(buf):
    buf = buf.strip()  # Trim whitespace
    buf = buf.strip('()\x00')  # Remove outer parentheses and null character
    data = re.findall(r'\(([^)]+)\)', buf)  # Extract key-value pairs

    parsed_data = {}
    for item in data:
        parts = item.split(' ')  # Split key and values
        key = parts[0]  # First part is the key
        values = parts[1:]  # Remaining parts are values

        # Convert to appropriate types
        try:
            if len(values) == 1:
                parsed_data[key] = float(values[0]) if '.' in values[0] else int(values[0])
            else:
                parsed_data[key] = [float(v) if '.' in v else int(v) for v in values]
        except ValueError:
            parsed_data[key] = values  # Keep as list of strings if conversion fails

    return parsed_data


csv_file = open('torcs_data.csv', mode='a', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["angle", "curLapTime", "damage", "distFromStart", "distRaced", "fuel", "gear", "lastLapTime", "racePos", "rpm", "speedX", "speedY", "speedZ", "trackPos", "z"])

csv_file_2 = open('torcs_actuator_data.csv', mode='a', newline = '')
csv_writer_2 = csv.writer(csv_file_2)
csv_writer_2.writerow(["accel", "brake", "gear", "steer"])

def on_press(key):
    try:
        if key.char == 'w': manual_state["accel"] = 0.5
        elif key.char == 's': manual_state["brake"] = 0.5
        elif key.char == 'a': manual_state["steer"] = -0.1
        elif key.char == 'd': manual_state["steer"] = 0.1
        elif key.char == 'q': manual_state["gear"] -= 1  # Allow gear to go to -1
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
        csv_writer.writerow([parsed_data.get(k, "0") for k in ["angle", "curLapTime", "damage", "distFromStart", "distRaced", "fuel", "gear", "lastLapTime", "racePos", "rpm", "speedX", "speedY", "speedZ", "trackPos", "z", "opponents"]])
        
        # csv_writer_2.writerow([parsed_data.get(k, "0") for k in ["accel", "brake", "gear", "steer"]])
        if manual_mode:
            actuator_data = [
                manual_state["accel"], manual_state["brake"], manual_state["gear"],
                manual_state["steer"]
            ]
        else:
            actuator_data = [d.control.getAccel(), d.control.getBrake(), d.control.getGear(),
                     d.control.getSteer()]

        # Write actuator data to torcs_actuators.csv
        csv_writer_2.writerow(actuator_data)


        response = build_send_string(manual_state) if manual_mode else d.drive(buf)
        sock.sendto(response.encode(), (arguments.host_ip, arguments.host_port))
    
    curEpisode += 1
    if curEpisode == arguments.max_episodes:
        shutdownClient = True

sock.close()
csv_file.close()
csv_file_2.close
if manual_mode: listener.stop()