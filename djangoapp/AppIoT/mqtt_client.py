import paho.mqtt.client as mqtt
import json
from django.conf import settings

# MQTT Client
client = mqtt.Client()

# Callback per la connessione
def on_connect(client, userdata, flags, rc):
    print(f"Connesso al broker MQTT con codice: {rc}")
    client.subscribe("bridge/comunicazione")
    client.subscribe("bridge/alert")
    client.subscribe("stanza-1/status")
    client.subscribe("stanza-2/status")
    client.subscribe("stanza-3/status")

# Callback per la ricezione dei messaggi
def on_message(client, userdata, msg):
    print(f"📥 Messaggio ricevuto da {msg.topic}: {msg.payload.decode()}")
    payload = json.loads(msg.payload.decode())
    handle_message(msg.topic, payload)

# Gestore dei messaggi ricevuti
def handle_message(topic, payload):
    if topic == "bridge/alert":
        print(f"🚨 ALERT ricevuto: {payload}")
        # Logica per gestire l'alert (ad es. cambio stanza)
    elif "status" in topic:
        print(f"💡 Stato stanza aggiornato: {payload}")
        # Logica per aggiornare lo stato nel database
    elif "comunicazione" in topic:
        print(f"🔄 Comunicazione tra stanze: {payload}")
        # Logica per gestire richieste o interazioni tra stanze

# Invio comando tramite MQTT
def send_mqtt_command(topic, payload):
    try:
        client.publish(topic, json.dumps(payload))
        print(f"✅ Comando inviato a {topic}: {payload}")
    except Exception as e:
        print(f"❌ Errore nell'invio comando MQTT: {str(e)}")

# Configurazione del client
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(settings.ADAFRUIT_AIO_USERNAME, settings.ADAFRUIT_AIO_KEY)

# Avvia la connessione
client.connect("io.adafruit.com", 1883, 60)

# Avvia il loop in background
client.loop_start()
