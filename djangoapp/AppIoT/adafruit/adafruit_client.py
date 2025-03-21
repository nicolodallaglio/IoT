import os
import requests
from Adafruit_IO import Client, Group
from django.conf import settings

# Connessione a Adafruit IO
aio = Client(settings.ADAFRUIT_AIO_USERNAME, settings.ADAFRUIT_AIO_KEY)

def create_group_if_not_exists(group_name):
    """Crea un gruppo se non esiste."""
    try:
        aio.groups(group_name)
        print(f"Gruppo '{group_name}' già esistente.")
    except Exception:
        print(f"Il gruppo '{group_name}' non esiste, lo creo...")
        try:
            group = Group(name=group_name)
            aio.create_group(group)
            print(f"Gruppo '{group_name}' creato correttamente.")
        except Exception as e:
            print(f"Errore nella creazione del gruppo '{group_name}': {e}")

def create_feed_if_not_exists(feed_name, group_name):
    """Crea un feed se non esiste all'interno di un gruppo utilizzando l'API REST."""
    try:
        # Verifica se il feed esiste già
        feed_key = f'{group_name}.{feed_name}'
        feed = aio.feeds(feed_key)
        print(f"Feed '{feed_name}' trovato nel gruppo '{group_name}'.")
    except Exception:
        print(f"Il feed '{feed_name}' non esiste nel gruppo '{group_name}', lo creo tramite API REST...")
        try:
            # Costruzione dell'URL dell'API
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

def send_room_data_to_adafruit(room):
    """Invia i dati della stanza a Adafruit IO usando il nome della stanza come prefisso."""
    try:
        # Usa il nome del bridge come gruppo
        group_name = room.name.replace(" ", "-").lower()

        # Crea il gruppo se non esiste
        create_group_if_not_exists(group_name)

        # Elenco dei feed da creare
        feeds = [
            'temperature',
            'humidity',
            'co2',
            'light',
            'sound',
            'occupancy',
            'bestroom',
            'room-status'
        ]

        # Crea i feed se non esistono
        for feed_name in feeds:
            create_feed_if_not_exists(feed_name, group_name)

        # Invia i dati ai feed
        aio.send_data(f'{group_name}.temperature', room.temperature)
        aio.send_data(f'{group_name}.humidity', room.humidity)
        aio.send_data(f'{group_name}.co2', room.co2)
        aio.send_data(f'{group_name}.light', room.light)
        aio.send_data(f'{group_name}.sound', room.sound)
        aio.send_data(f'{group_name}.occupancy', room.people)
        aio.send_data(f'{group_name}.bestroom', room.bestroom)
        aio.send_data(f'{group_name}.room-status', "online" if room.online_status else "offline")

        print(f"Dati inviati ad Adafruit per la stanza {room.name}")
        return True
    except Exception as e:
        print(f"Errore nell'invio dati Adafruit: {e}")
        return False
