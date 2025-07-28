from email import message
import serial
import threading
import time
import requests
import json
import ast
import paho.mqtt.client as mqtt

USERNAME = "nicodalla99"  # Adafruit IO username
AIO_KEY = "aio_Nmgf31z2Sd530yAMLfe6o8Xs31gm"  # Adafruit IO API Key 
FEED_WARNING = "bridge.warning"  # Warning Feed
FEED_COMMAND = "bridge.command"  # Command Feed

serial_port='COM3'

bridge_name = "casa_tua"
room_name = "simB"

# Dictionary that associates messages to characters for alarms
alarm_mapping = {
    "High temperature": "O",
    "Fire alarm": "O",
    "High CO2": "O",
    "stop": "F"
}

light_mapping = {
    "Low light": "H",
    "Light off": "L"
}

prealert_mapping = {
    "activate_ventilation" : "P",
    "deactivate_notifications" : "S",
    "activate_fire_alarm" : "O",
    "invite_occupancy" : "P"
}

stop_timer = None  # Stop timer for alarms

def message_to_signal(message):
    
    # Returns the matching character or a question mark if not found
    for keyword, symbol in alarm_mapping.items():
        if keyword in message:
            return symbol
        
    return "?"

def send_data_to_server(sensor_data):
    url = "http://smartrooms.ddns.net:8000/api/receive_sensor_data/"  # Django Server API URL
    headers = {'Content-Type': 'application/json'}
    payload = json.dumps(sensor_data)
    print(f"Send to server: {sensor_data}")

    try:
        response = requests.post(url, data=payload, headers=headers)
        
        if response.status_code == 200:
            print("Data sent successfully!")
        else:
            print(f"Error sending data: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")

# Function to read from serial port
def read_from_arduino(ser):
    while True:
        if ser.in_waiting > 0:  # Check if there is incoming data
            line = ser.readline().decode('utf-8').rstrip()  # Read the line from the serial
            
            if line:
                # We assume the data is formatted as a JSON string or something similar
                print(f"Received: {line}")

            try:
                # If the data arrives in JSON-like string format
                data = ast.literal_eval(line)  # Convert string to Python dictionary
                send_data_to_server(data)
            except json.JSONDecodeError:
                print(f"Error decoding data: {data}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Connected to Adafruit IO with code: {rc}")
        # Subscribe to bridge.warning feed
        topic = f"{USERNAME}/feeds/{FEED_WARNING}"
        client.subscribe(topic)
        print(f"📡 Subscribed to feed: {topic}")
        # Subscribe to bridge.command feed
        topic = f"{USERNAME}/feeds/{FEED_COMMAND}"
        client.subscribe(topic)
        print(f"📡 Subscribed to feed: {topic}")
    else:
        print(f"❌ Connection failed to {topic} with code: {rc}")

        
def on_message(client, userdata, msg):
    global stop_timer

    print(f"💡 Message received from {msg.topic}: {msg.payload.decode()}")

    feed = msg.topic.split("/")[-1]
    payload_decoded = msg.payload.decode()

    try:
        address = payload_decoded.split('[')[1].split(']')[0].split(':')
    except IndexError:
        print(f"⚠️ Message {msg.topic} is not formatted correctly")
        return
    
    # Check that the bridge and room are correct
    if ((bridge_name == address[2]) and (room_name == address[1])):
        if not ser.is_open:
            print(f"⚡ Serial not opened, message cannot be sent")
            return

        if feed == FEED_WARNING:
            # Stop timer management
            if any(alarm in payload_decoded for alarm in alarm_mapping):
                cod = message_to_signal(payload_decoded)
                ser.write(cod.encode('utf-8'))
                print(f"✅ Warning sent to Arduino: {cod}")
                
                if stop_timer and stop_timer.is_alive():
                    stop_timer.cancel()

                def send_stop_signal():
                    if ser.is_open:
                        cod = message_to_signal("stop")
                        ser.write(cod.encode('utf-8'))
                        print("🛑 Stop message sent to Arduino")

                stop_timer = threading.Timer(25, send_stop_signal)
                stop_timer.start()

            # Light switch management
            if any(light in payload_decoded for light in light_mapping):
                light_code = None
                for light_keyword, code in light_mapping.items():
                    if light_keyword in payload_decoded:
                        light_code = code
                        break

                if light_code:
                    ser.write(light_code.encode('utf-8'))
                    print(f"💡 Light command sent to Arduino: {light_code}")

        elif feed == FEED_COMMAND:
            cod_to_send = None
            for key, cod in prealert_mapping.items():
                if key in payload_decoded:
                    cod_to_send = cod
                    break

            if cod_to_send:
                ser.write(cod_to_send.encode('utf-8'))
                print(f"✅ Command '{key}' found. Sent code '{cod_to_send}' to Arduino")
            else:
                print(f"⛔No commands found for {key}")

        else:
            print(f"⛔ Feed '{feed}' not managed")
    else:
        print(f"⛔ Message {msg.topic} ignored: room/bridge mismatch")


            
def mqtt_loop():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, AIO_KEY)
    client.on_connect = on_connect
    client.on_message = on_message
    print("Connecting to MQTT Broker...")
    client.connect("io.adafruit.com", 1883, 60)
    client.loop_forever()

# Set up serial connection with Arduino
ser = serial.Serial(serial_port, 9600, timeout=1)

if ser.is_open:
    print("Open serial connection")

# Create threads for reading and writing
read_thread = threading.Thread(target=read_from_arduino, args=(ser,))
write_thread = threading.Thread(target=mqtt_loop)

# Start threads
read_thread.start()
write_thread.start()

# Threads will continue to run until manually stopped
read_thread.join()
write_thread.join()

# Close the serial connection at the end
ser.close()
