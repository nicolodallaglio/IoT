import os
import requests
from Adafruit_IO import Client, Group
from django.conf import settings
import time

# Connessione a Adafruit IO
aio = Client(settings.ADAFRUIT_AIO_USERNAME, settings.ADAFRUIT_AIO_KEY)


# Funzione generica per inviare un dato ad Adafruit
def send_to_adafruit(feed_name, value):
    try:
        aio.send(feed_name, value)
        print(f"Debug: Dato inviato a {feed_name}: {value}")
    except Exception as e:
        print(f"Errore: errore nell'invio a {feed_name}: {e}")


def send_room_data_to_adafruit(room, position):
    try:
        group_name = f"stanza-{position}"
        print(f"\n Debug: Inizio invio dati per la stanza: {room.name} (gruppo: {group_name})")

        # Prepara i dati da inviare
        data = {
            "temperature": room.temperature,
            "humidity": room.humidity,
            "co2": room.co2,
            "light": room.light,
            "sound": room.sound,
            "occupancy": room.people,
            "name": room.name,
        }

        # Invio dei dati uno ad uno
        for key, value in data.items():
            feed_name = f"{group_name}.{key}"
            print(f"Adafruit: Invio dato → Feed: {feed_name} | Valore: {value}")
            send_to_adafruit(feed_name, value)
            time.sleep(0.3)  # Ritardo per evitare rate limit

        print(f"Debug: Tutti i dati della stanza '{room.name}' sono stati inviati correttamente su Adafruit nel gruppo '{group_name}'\n")
        return True

    except Exception as e:
        print(f"Errore: Errore durante l'invio dei dati per la stanza '{room.name}': {e}")
        return False
