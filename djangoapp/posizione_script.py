import random
import os
import django


# Configura le impostazioni di Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangoapp.settings")
django.setup()

from AppIoT.models import Room


# Definisci l'intervallo di coordinate per la provincia di Modena
lat_min, lat_max = 44.5, 44.9   # Intervallo di latitudine per Modena
lon_min, lon_max = 10.7, 11.1   # Intervallo di longitudine per Modena

# Funzione per generare una latitudine e longitudine casuale nell'intervallo
def generate_random_location():
    lat = round(random.uniform(lat_min, lat_max), 6)
    lon = round(random.uniform(lon_min, lon_max), 6)
    return lat, lon

# Popola solo i campi latitudine e longitudine per le stanze esistenti
def populate_location_only():
    rooms = Room.objects.all()
    for room in rooms:
        lat, lon = generate_random_location()
        room.latitudine = lat
        room.longitudine = lon
        room.save(update_fields=['latitudine', 'longitudine'])  # Aggiorna solo i campi specificati

    print(f"Coordinate latitudine e longitudine aggiornate per {rooms.count()} stanze.")

# Esegui lo script per aggiornare le coordinate
populate_location_only()
