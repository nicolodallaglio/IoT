import os
from Adafruit_IO import Client
from django.conf import settings

# Connessione a Adafruit IO
aio = Client(settings.ADAFRUIT_AIO_USERNAME, settings.ADAFRUIT_AIO_KEY)

def send_room_data_to_adafruit(room):
    """Invia i dati della stanza a Adafruit IO usando il nome della stanza come prefisso."""
    try:
        room_prefix = room.name.replace(" ", "-").lower()  # Converte il nome della stanza in un formato compatibile

        aio.send(f'{room_prefix}.temperature', room.temperature)
        aio.send(f'{room_prefix}.humidity', room.humidity)
        aio.send(f'{room_prefix}.co2', room.co2)
        aio.send(f'{room_prefix}.light', room.light)
        aio.send(f'{room_prefix}.sound', room.sound)
        aio.send(f'{room_prefix}.occupancy', room.people)
        aio.send(f'{room_prefix}.bestroom', room.bestroom)
        aio.send(f'{room_prefix}.room-status', "online" if room.online_status else "offline")

        print(f"Dati inviati ad Adafruit per la stanza {room.name}")
        return True
    except Exception as e:
        print(f"Errore nell'invio dati Adafruit: {e}")
        return False
