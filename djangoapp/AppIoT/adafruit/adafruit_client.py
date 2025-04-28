import os
import requests
import json
from Adafruit_IO import Client
from django.conf import settings
import time

# Connessione a Adafruit IO
aio = Client(settings.ADAFRUIT_AIO_USERNAME, settings.ADAFRUIT_AIO_KEY)

# ------------------- FUNZIONI ------------------------

# Funzione generica per inviare un dato ad Adafruit
def send_to_adafruit(feed_name, value):
    try:
        aio.send(feed_name, value)
        print(f"ADAFRUIT: data sent {feed_name}: {value}")
    except Exception as e:
        print(f"Erro: Errore nell'invio a {feed_name}: {e}")


# Invia i dati di una stanza a una certa posizione su Adafruit
def send_room_data_to_adafruit(room, position):
    feed_name = f"stanza-{position}.data"

    if room is None:
        # Se non c'è nessuna stanza → pulizia (reset)
        payload = json.dumps({
            "name": "",
            "temperature": 0,
            "humidity": 0,
            "co2": 0,
            "light": 0,
            "sound": 0,
            "occupancy": 0
        })
    else:
        # Preparo il JSON con i dati della stanza
        payload = json.dumps({
            "name": room.name,
            "temperature": round(room.temperature, 1),
            "humidity": round(room.humidity, 1),
            "co2": round(room.co2, 1),
            "light": round(room.light, 1),
            "sound": round(room.sound, 1),
            "occupancy": room.people
        })
        print(f"ADAFRUIT: Room data '{room.name}' sent on feed {feed_name}")

    send_to_adafruit(feed_name, payload)
