import os
import django
import random

# Configura l'ambiente Django (assicurati che il percorso sia corretto)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoapp.settings')
django.setup()

# Importa il modello Room
from AppIoT.models import Room

# Funzione per popolare il database con stanze
def popola_rooms():
    # Lista di nomi fittizi per le stanze
    nomi_stanze = [
    'Sala Conferenze 1',
    'Sala Conferenze 2',
    'Aula Magna',
    'Laboratorio Informatica 1',
    'Laboratorio Informatica 2',
    'Aula Studio 1',
    'Aula Studio 2',
    'Sala Riunioni 1',
    'Sala Riunioni 2',
    'Aula Didattica 1',
    'Aula Didattica 2',
    'Auditorium 1',
    'Auditorium 2',
    'Sala Proiezioni',
    'Sala Seminari 1',
    'Sala Seminari 2',
    'Biblioteca 1',
    'Biblioteca 2',
    'Laboratorio Chimica 1',
    'Laboratorio Chimica 2',
    'Laboratorio Fisica 1',
    'Laboratorio Fisica 2',
    'Aula Informatica Avanzata',
    'Aula Scienze 1',
    'Aula Scienze 2',
    'Sala Multimediale 1',
    'Sala Multimediale 2',
    'Aula Linguistica 1',
    'Aula Linguistica 2',
    'Sala Stampa',
    'Sala Lettura',
    'Spazio Co-working 1',
    'Spazio Co-working 2'
]


    # Dati da inserire
    for nome in nomi_stanze:
        room = Room(
            name=nome,
            price=random.uniform(100, 500),  # Prezzo tra 100 e 500 euro
            posizione= 'via Roma',
            rating=random.uniform(3, 5),     # Rating tra 0 e 1
            availability=random.choice([True, False]),  # Disponibile o no
            sensor_data={
                'light': random.uniform(18, 25),
                'noise': random.uniform(18, 25),
                'temperature': random.uniform(18, 25),  # Temperatura casuale
                'humidity': random.uniform(30, 50),     # Umidità casuale
                'comfort': random.uniform(5, 10)        # Comfort casuale (da 5 a 10)
            }
        )
        room.save()  # Salva la stanza nel database
        print(f"Stanza {room.name} creata con successo.")

if __name__ == '__main__':
    popola_rooms()
