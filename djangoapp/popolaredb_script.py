import os
import pandas as pd
import django
import random

# Configura le impostazioni di Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangoapp.settings")
django.setup()

# Ora puoi importare i tuoi modelli dopo aver inizializzato Django
from AppIoT.models import Room

# Percorso del file CSV
csv_file_path = r'C:\Users\Nicolò\Documents\IoT2025\dataset.csv'


# Carica il CSV in un DataFrame Pandas
df = pd.read_csv(csv_file_path)

# Generatore di nomi per le stanze
prefixes = ["Sala", "Aula", "Laboratorio", "Stanza", "Sala Riunioni", "Ufficio", "Centro", "Spazio", "Studio", "Biblioteca"]
adjectives = ["Grande", "Piccola", "Conferenze", "Tecnica", "Magna", "Didattica", "Informatica", "Multimedia", "Polifunzionale"]
suffixes = ["I", "II", "III", "IV", "V", "Alfa", "Beta", "Gamma", "Delta", "Omega","1.1","1.2","1.3","2.1","2.2","2.3"]

def generate_room_name():
    prefix = random.choice(prefixes)
    adjective = random.choice(adjectives)
    suffix = random.choice(suffixes)
    return f"{prefix} {adjective} {suffix}"

# Cicla attraverso ogni riga del DataFrame e crea un'istanza di Room
for index, row in df.iterrows():
    room_name = generate_room_name()  # Genera il nome della stanza
    room_type = 'lavoro' if any(x in room_name for x in ["Sala Riunioni", "Ufficio", "Centro"]) else 'studio'

    Room.objects.create(
        bridge='empty',  # bridge 'empty' per indicare che questa stanza serve solo per la predizione
        name=room_name,  # Usa il nome generato
        type=room_type,  # Assegna il tipo di stanza in base al nome
        price=random.uniform(0, 50),  # Assegna un prezzo casuale tra 0 e 50 euro
        temperature=row['Temperature'],
        humidity=row['Humidity'],
        light=row['Light_scaled'],
        co2=row['CO2_scaled'],
        sound=row['Sound'],
        room_size=row['Room_Size'],
        people=row['People'],
        bestroom=row['BestRoom'],
        probability=0,  # Imposta a 0 o un altro valore se necessario
        last_update=False  # Indica che la stanza non è stata ancora aggiornata
    )

print("Database popolato con successo!")
