import os
import requests
from Adafruit_IO import Client, Group
from django.conf import settings
import time

# Connessione a Adafruit IO
aio = Client(settings.ADAFRUIT_AIO_USERNAME, settings.ADAFRUIT_AIO_KEY)

# Crea un gruppo su Adafruit IO se non esiste già
def create_group_if_not_exists(group_name):
    try:
        aio.groups(group_name)
    except Exception:
        print(f"Il gruppo '{group_name}' non esiste, lo creo...")
        try:
            group = Group(name=group_name)
            aio.create_group(group)
            print(f"Gruppo '{group_name}' creato correttamente.")
        except Exception as e:
            print(f"Errore nella creazione del gruppo '{group_name}': {e}")

# Crea un feed su Adafruit IO se non esiste già
def create_feed_if_not_exists(feed_name, group_name):
    try:
        feed_key = f'{group_name}.{feed_name}'
        aio.feeds(feed_key)
    except Exception:
        print(f"Il feed '{feed_name}' non esiste nel gruppo '{group_name}', lo creo...")
        try:
            url = f'https://io.adafruit.com/api/v2/{settings.ADAFRUIT_AIO_USERNAME}/groups/{group_name}/feeds'
            headers = {
                'X-AIO-Key': settings.ADAFRUIT_AIO_KEY,
                'Content-Type': 'application/json'
            }
            payload = {
                "name": feed_name,
                "key": f"{group_name}.{feed_name}"
            }
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 201:
                print(f"Feed '{feed_name}' creato correttamente nel gruppo '{group_name}'.")
            else:
                print(f"Errore nella creazione del feed '{feed_name}' nel gruppo '{group_name}': {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"Errore nella creazione del feed '{feed_name}' nel gruppo '{group_name}': {e}")

# Funzione generica per inviare un dato ad Adafruit
def send_to_adafruit(feed_name, value):
    try:
        aio.send(feed_name, value)
        print(f"✅ Dato inviato a {feed_name}: {value}")
    except Exception as e:
        print(f"❌ Errore nell'invio a {feed_name}: {e}")


def send_room_data_to_adafruit(room, position):
    try:
        group_name = f"stanza-{position}"

        # Crea gruppo e feed (facoltativo)
        create_group_if_not_exists(group_name)
        for key in ["temperature", "humidity", "co2", "light", "sound", "occupancy", "status", "name"]:
            create_feed_if_not_exists(key, group_name)

        data = {
            "temperature": room.temperature,
            "humidity": room.humidity,
            "co2": room.co2,
            "light": room.light,
            "sound": room.sound,
            "occupancy": room.people,
            "status": "online" if room.online_status else "offline",
            "name": room.name,
        }

        for key, value in data.items():
            feed_name = f"{group_name}.{key}"
            send_to_adafruit(feed_name, value)
            time.sleep(0.3)  # opzionale, evita errori di rate limit

        print(f"✅ Dati stanza {room.name} inviati correttamente su Adafruit come {group_name}")
        return True
    except Exception as e:
        print(f"❌ Errore nell'invio dati per la stanza '{room.name}': {e}")
        return False