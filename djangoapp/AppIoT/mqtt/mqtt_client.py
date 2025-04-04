import paho.mqtt.client as mqtt
import json
from django.conf import settings

# MQTT Client
client = mqtt.Client()

# Callback per la connessione
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connesso al broker MQTT")
        client.subscribe("bridge/comunicazione")
        client.subscribe("bridge/alert")
        client.subscribe("stanza-1/status")
        client.subscribe("stanza-2/status")
        client.subscribe("stanza-3/status")
    else:
        print(f"❌ Connessione fallita al broker MQTT con codice: {rc}")


# Callback per la ricezione dei messaggi
def on_message(client, userdata, msg):
    print(f"📥 Messaggio ricevuto da {msg.topic}: {msg.payload.decode()}")
    payload = json.loads(msg.payload.decode())
    handle_message(msg.topic, payload)

# Gestore dei messaggi ricevuti
def handle_message(topic, payload):
    try:
        # Identifica la stanza che ha pubblicato lo stato
        source_room = payload.get("room")  # es. "stanza-1"
        co2 = payload.get("co2", 0)
        sound = payload.get("sound", 0)
        people = payload.get("people", 0)
        status = payload.get("status", "OK")
        room_size = payload.get("room_size", 0)
        occupancy_ratio = people / room_size if room_size else 0 

        print(f"📡 Stato ricevuto da {source_room}: CO2={co2}, SOUND={sound}, PEOPLE={people}, STATUS={status}")

        # Lista delle altre stanze (per comunicazione interna)
        all_rooms = ["stanza-1", "stanza-2", "stanza-3"]
        other_rooms = [room for room in all_rooms if room != source_room]

        # --- REGOLA 1: RUMORE ALTO → LE ALTRE STANZE ATTIVANO LUCE DI AVVISO ---
        if status == "NOISY" or sound > 50:
            for room in other_rooms:
                print(f"🔇 {source_room} è rumorosa, invio comando silenzioso a {room}")
                send_mqtt_command(f"{room}/comando", {
                    "action": "attiva_luce_silenzio",
                    "message": f"{source_room} è rumorosa. Mantenere quiete."
                })

        # --- REGOLA 2: CO2 ALTA → LE ALTRE STANZE ATTIVANO VENTILAZIONE ---
        if co2 > 1200:
            for room in other_rooms:
                print(f"🌀 CO2 alta in {source_room}, attivo ventilazione in {room}")
                send_mqtt_command(f"{room}/comando", {
                    "action": "attiva_ventilazione",
                    "message": f"CO2 alta in {source_room}. Aiuto con ventilazione."
                })

        # --- REGOLA 3: STANZA AFFOLLATA (>80%) → LE ALTRE INVITANO ---
        if occupancy_ratio >= 0.8:
            for room in other_rooms:
                print(f"🚶 {source_room} è affollata ({occupancy_ratio:.1%}), invito a trasferirsi in {room}")
                send_mqtt_command(f"{room}/comando", {
                    "action": "invita_occupazione",
                    "message": f"{source_room} è al {int(occupancy_ratio*100)}% della capienza. Questa stanza è libera!"
                })


        # --- REGOLA 4 (extra): Tutto OK → Disattiva notifiche nelle altre stanze ---
        if status == "OK" and co2 < 800 and sound < 40 and people < 4:
            for room in other_rooms:
                print(f"✅ {source_room} è tranquilla, disattivo notifiche in {room}")
                send_mqtt_command(f"{room}/comando", {
                    "action": "disattiva_notifiche",
                    "message": f"{source_room} è tornata in condizioni ottimali."
                })

    except Exception as e:
        print(f"❌ Errore durante handle_message: {str(e)}")


# Invio comando tramite MQTT
def send_mqtt_command(topic, payload):
    try:
        # Converti il payload in JSON
        payload_json = json.dumps(payload)

        # Verifica lo stato della connessione prima di inviare
        if not client.is_connected():
            print("❗ Client non connesso, tentativo di riconnessione...")
            client.reconnect()

        # Pubblica il messaggio e ottieni il risultato
        result = client.publish(topic, payload_json)

        # Verifica il risultato della pubblicazione
        status = result.rc
        if status == mqtt.MQTT_ERR_SUCCESS:
            print(f"✅ Comando inviato a {topic}: {payload}")
            return True
        else:
            print(f"❌ Errore nell'invio comando MQTT: Codice {status}")
            return False
    except Exception as e:
        print(f"❌ Errore nell'invio comando MQTT: {str(e)}")
        return False


# Configurazione del client
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(settings.ADAFRUIT_AIO_USERNAME, settings.ADAFRUIT_AIO_KEY)

# Avvia la connessione
client.connect("io.adafruit.com", 1883, 60)

# Avvia il loop in background
client.loop_start()
