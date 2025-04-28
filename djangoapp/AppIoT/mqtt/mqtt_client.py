import paho.mqtt.client as mqtt
from AppIoT.models import Room
import json
from django.conf import settings

# MQTT Client
client = mqtt.Client()

# Callback
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT: Connected to the MQTT broker")
        client.subscribe("bridge/warning")
        client.subscribe(f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/stanza-1.status")
        client.subscribe(f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/stanza-2.status")
        client.subscribe(f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/stanza-3.status")

    else:
        print(f"Error: Failed to connect to the MQTT broker with code: {rc}")


alarm_active = {}


def get_posizione_to_stanza():
    stanze_attive = Room.objects.filter(online_status=True, adafruit_position__isnull=False)
    return {stanza.adafruit_position: stanza.name for stanza in stanze_attive}

def on_message(client, userdata, msg):
    topic = msg.topic
    print(f"MQTT: → Message received on topic {topic}")

    try:
        payload = json.loads(msg.payload.decode())
        print(f"MQTT: → Payload decoded: {payload}")
    except Exception as e:
        print(f"MQTT ERROR: Decode JSON failed → {e}")
        return

    topic_parts = topic.split('/')
    feed_name = topic_parts[-1]
    source_stanza = feed_name.split('.')[0]  # es. 'stanza-1'

    # ---- Mapping active positions ----
    posizione_to_stanza = get_posizione_to_stanza()
    # es. {1: 'simulazione4', 2: 'simulazione 1', 3: 'simulazione 2'}

    # Converto 'stanza-1' → 1
    if source_stanza.startswith('stanza-'):
        try:
            source_posizione = int(source_stanza.split('-')[1])
        except ValueError:
            print(f"MQTT WARNING: source_stanza {source_stanza} has not a valid position!")
            return
    else:
        print(f"MQTT WARNING: source_stanza {source_stanza} not found as room-X.")
        return

    # Ottengo il vero nome della stanza dalla posizione
    source_stanza_name = posizione_to_stanza.get(source_posizione)
    if not source_stanza_name:
        print(f"MQTT WARNING: no room assigned to {source_posizione}")
        return

    print(f"MQTT: → Message received from: {source_stanza_name} (position {source_posizione})")

    # ---- Controlla payload ----
    status = payload.get("status")
    co2 = payload.get("co2")
    sound = payload.get("sound")
    people = payload.get("people")
    room_size = payload.get("room_size")
    bridge_name = payload.get("bridge_name", "unknown_bridge")

    if None in [status, co2, sound, people, room_size]:
        print(f"MQTT WARNING: Payload incompleto → {payload}")
        return

    occupancy_ratio = people / room_size if room_size else 0

    # ---- Altre stanze (escludendo quella che ha inviato il messaggio) ----
    other_rooms = [name for pos, name in posizione_to_stanza.items() if pos != source_posizione]

    # ---- Stato allarme ----
    if source_stanza_name not in alarm_active:
        alarm_active[source_stanza_name] = False

    # ---- REGOLA 1: FIRE ----
    if status.strip().upper() == "FIRE":
        alarm_active[source_stanza_name] = True
        for target_stanza in other_rooms:
            action = "activate_fire_alarm"
            message = f"{source_stanza_name} is on fire!"
            command_str = f"[COMMAND:{target_stanza}:{bridge_name}:{action}:{message}]"
            print(f"MQTT COMMAND: → Command to {target_stanza}: {command_str}")
            send_mqtt_command(f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/bridge.command", command_str)

    # ---- REGOLA 2: HIGH_CO2 ----
    if status.strip().upper() == "HIGH_CO2":
        alarm_active[source_stanza_name] = True
        for target_stanza in other_rooms:
            action = "activate_ventilation"
            message = f"High CO2 in {source_stanza_name}, help with ventilation!"
            command_str = f"[COMMAND:{target_stanza}:{bridge_name}:{action}:{message}]"
            print(f"MQTT COMMAND: → Command to {target_stanza}: {command_str}")
            send_mqtt_command(f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/bridge.command", command_str)

    # ---- REGOLA 3: OVERCROWDING ----
    if occupancy_ratio >= 0.8:
        alarm_active[source_stanza_name] = True
        for target_stanza in other_rooms:
            action = "invite_occupancy"
            message = f"{source_stanza_name} is {int(occupancy_ratio * 100)}%, come here!"
            command_str = f"[COMMAND:{target_stanza}:{bridge_name}:{action}:{message}]"
            print(f"MQTT COMMAND: → Command to {target_stanza}: {command_str}")
            send_mqtt_command(f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/bridge.command", command_str)

    # ---- REGOLA 4: OK (reset) ----
    if status.strip().upper() == "OK":
        if alarm_active.get(source_stanza_name, False):
            for target_stanza in other_rooms:
                action = "deactivate_notifications"
                message = f"{source_stanza_name} is OK, you can turn off notifications."
                command_str = f"[COMMAND:{target_stanza}:{bridge_name}:{action}:{message}]"
                print(f"MQTT COMMAND: → Command to {target_stanza}: {command_str}")
                send_mqtt_command(f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/bridge.command", command_str)
            alarm_active[source_stanza_name] = False



# Funzione per inviare comandi o alert tramite MQTT
def send_mqtt_command(topic, payload, target=None):
    try:
        # Se payload è un dizionario e c'è target, aggiungilo
        if isinstance(payload, dict) and target is not None:
            payload['target'] = target

        payload_json = json.dumps(payload)

        if not client.is_connected():
            print("Errore: Client MQTT lost connection, try to reconnect...")
            client.reconnect()

        result = client.publish(topic, payload_json)
        status = result.rc
        if status == mqtt.MQTT_ERR_SUCCESS:
            return True
        else:
            print(f"Error command MQTT: code {status}")
            return False
    except Exception as e:
        print(f"Error command MQTT: {str(e)}")
        return False


# Client conf
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(settings.ADAFRUIT_AIO_USERNAME, settings.ADAFRUIT_AIO_KEY)
client.connect("io.adafruit.com", 1883, 60)
client.loop_start()
