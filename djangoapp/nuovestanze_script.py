import requests
import json
import time
import random

url = "http://127.0.0.1:8000/api/receive_sensor_data/"

# Lista delle stanze simulate
stanze = [
    {
        "bridge_name": "bridge_piano2",
        "room_name": "Aula D - Perfetta",
        "room_size": 70,
        "latitudine": 44.6290,
        "longitudine": 10.9488,
        "type": "studio"
    },
    {
        "bridge_name": "bridge_piano2",
        "room_name": "Aula E - Rumorosa",
        "room_size": 50,
        "latitudine": 44.6291,
        "longitudine": 10.9489,
        "type": "studio"
    },
    {
        "bridge_name": "bridge_piano2",
        "room_name": "Aula F - CO2 Alta",
        "room_size": 50,
        "latitudine": 44.6292,
        "longitudine": 10.9490,
        "type": "studio"
    }
]

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
    print(f"\n🔁 Inizio invio dati stanze...")

    dati_stanze = []
    for base in stanze:
        data = base.copy()
        data.update(genera_dati_sensori(base["room_size"]))
        data["room_name"] = data["room_name"].strip()
        data["bridge_name"] = data["bridge_name"].strip()
        dati_stanze.append(data)

    for idx, data in enumerate(dati_stanze, start=1):
        print(f"🔹 Invio dati simulazione {idx}: {data['room_name']}")
        try:
            response = requests.post(url, json=data)
            print("✅ Status code:", response.status_code)
            print("📬 Risposta:", response.json())
        except json.JSONDecodeError:
            print("❌ Errore: risposta non JSON")
            print("Contenuto:", response.text)
        except Exception as e:
            print("❌ Eccezione:", e)

    print("⏱ Attesa 60 secondi prima del prossimo ciclo...\n")
    time.sleep(60)
