import requests
import json
import time
import random

url = "http://127.0.0.1:8000/api/receive_sensor_data/"

# Stanza unica simulata
stanza = {
    "bridge_name": "bridge3",
    "room_name": "Aula C",
    "room_size": 100,
    "latitudine": 44.6290,
    "longitudine": 10.9488,
    "type": "studio"
}

# Funzione per generare dati sensori
def genera_dati_sensori(room_size):
    return {
        "temperature": round(random.uniform(18, 30), 1),
        "humidity": round(random.uniform(30, 65), 1),
        "light": round(random.uniform(200, 800), 1),
        "co2": round(random.uniform(350, 2000), 1),
        "sound": round(random.uniform(20, 80), 1),
        "people": random.randint(0, room_size)
    }

# Loop infinito ogni 60 secondi
while True:
    print(f"\n🔁 Invio dati simulazione per: {stanza['room_name']}")

    data = stanza.copy()
    data.update(genera_dati_sensori(stanza["room_size"]))
    data["room_name"] = data["room_name"].strip()
    data["bridge_name"] = data["bridge_name"].strip()

    try:
        response = requests.post(url, json=data)
        print("✅ Status code:", response.status_code)
        print("📬 Risposta:", response.json())
    except json.JSONDecodeError:
        print("❌ Errore: risposta non JSON")
        print("Contenuto:", response.text)
    except Exception as e:
        print("❌ Eccezione:", e)

    print("⏱ Attesa 60 secondi prima del prossimo invio...\n")
    time.sleep(60)
