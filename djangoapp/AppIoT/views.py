from django.shortcuts import render
import pandas as pd
from django.http import HttpResponse
from django.http import JsonResponse
import json
from django.views import View
from django.views.generic import ListView
from django.shortcuts import render
from .ml_model.ml_model import train_model, predict_and_sort_rooms
from AppIoT.utils import check_and_notify_adjacent_rooms
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from .serializers import RoomSerializer
from rest_framework import viewsets

from .models import Room

from AppIoT.adafruit.adafruit_client import (
    send_room_data_to_adafruit,
    send_to_adafruit,
    adafruit_room_mapping
)

# -------------------- ML --------------------
#TRAIN ML
# training a partire dal csv
def train_model_view(request):
    if request.method == 'GET':
        # Renderizza il template HTML per il form di upload
        return render(request, 'train.html')
    elif request.method == 'POST':
        if 'file' not in request.FILES:
            return JsonResponse({"error": "No file provided"}, status=400)

        # Ottieni il file dal form
        file = request.FILES['file']
        response = train_model(file)
        return JsonResponse(response)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=400)

#PREDICT ML -- predirre se la nuova stanza è buona o no
def predict_view(request):
    if request.method == 'POST':
        try:
            # Ottieni i dati di input dal corpo della richiesta (in formato JSON)
            data = json.loads(request.body)

            # Converte i dati in un DataFrame Pandas
            input_data = pd.DataFrame(data)

            # Verifica che il DataFrame non sia vuoto
            if input_data.empty:
                return JsonResponse({"error": "Empty input data provided"}, status=400)

            # Usa la funzione predict_and_sort_rooms per fare previsioni e ordinare le stanze
            sorted_rooms = predict_and_sort_rooms(input_data)

            # Cicla attraverso i dati e le previsioni ordinate, e salva ogni stanza nel database
            for i, row in sorted_rooms.iterrows():
                Room.objects.create(
                    name=f"Room {i + 1}",  # Nome stanza generato dinamicamente
                    temperature=row['Temperature'],  
                    humidity=row['Humidity'], 
                    light=row['Light_scaled'], 
                    co2=row['CO2_scaled'],
                    sound=row['Sound'],
                    room_size=row['Room_Size'],
                    people=row['People'],
                    occupancy=row['predicted_class'],
                    probability=row['probability']
                )

            # Prepara la risposta come JSON
            response = {
                "sorted_rooms": sorted_rooms[['Temperature', 'Humidity', 'Light', 'CO2', 'HumidityRatio', 'probability', 'predicted_class']].to_dict(orient='records')
            }
            return JsonResponse(response, status=200)

        except Exception as e:
            # Gestione di qualsiasi eccezione
            return JsonResponse({"error": str(e)}, status=400)

    # Risposta per metodi HTTP non validi
    return JsonResponse({"error": "Invalid request method. Only POST is allowed."}, status=405)



# logica di regressione lineare per predire il prezzo dinamico delle stanze 
def predici_prezzo(input_data):
    # Inserisci qui il modello di regressione lineare per predire i prezzi
    modello = ...  # Carica il modello addestrato
    prezzo_predetto = modello.predict(input_data)
    return prezzo_predetto

    
# ---------------- INDEX -------------------------

def index(request):
    #mex di saluto
    greeting_message = "Benvenuto in SmartRooms"
    #url visualizzabili in main page
    other_urls = [
        {'url': '/api/migliori-stanze/', 'label': 'api delle stanze per flutter'},
        {'url': '/api/location/', 'label': 'api su cui il server riceve long e lat dell utente'},
        {'url': '/api/receive_sensor_data/', 'label': 'api per caricare sensori arduino'},
        {'url': '/train/', 'label': 'Traina il modello'},
        {'url': '/migliori-stanze/', 'label': 'Stanze Migliori'},
    ]
    #passiamo il mex al template e other urls
    return render(request,'index.html', {'greeting_message': greeting_message, 'other_urls': other_urls})



# ----------------- ALGORITMO --------------------
#algoritmo considererà vari criteri, come il prezzo, la disponibilità e il rating della stanza

def find_optimal_room():
    # Recupera tutte le stanze
    rooms = Room.objects.all()  

    if not rooms.exists():
        return None  # Nessuna stanza disponibile

    def calculate_sensor_score(room):
        # Calcola il punteggio combinato per i dati dei sensori (arrotondando a una cifra decimale)
        sensor_score = (
            (1 - abs(round(room.temperature, 1) - 22) / 10) +  # 22°C come valore ottimale per il comfort
            (1 - abs(round(room.co2, 1) - 400) / 1000) +       # 400 ppm come valore ottimale per il comfort
            (1 - abs(round(room.sound, 1) - 30) / 40) +        # 30 dB come valore ottimale per il comfort acustico
            (round(room.light, 1) / 1000)                      # Normalizza la luce
        ) / 4  # Media dei punteggi dei sensori
        return sensor_score

    def calculate_rating(room):
        # Calcola un rating basato sul rapporto qualità-prezzo e sui sensori
        sensor_score = calculate_sensor_score(room)
        # Normalizza il prezzo: assumendo che 50 sia il massimo prezzo
        price_normalized = (50 - room.price) / 50
        # Rating finale combinando comfort (sensori) e rapporto qualità-prezzo (80% sensori, 20% prezzo)
        return 0.8 * sensor_score + 0.2 * price_normalized

    # Aggiungi il rating a ciascuna stanza e ordina in base a bestroom e rating
    for room in rooms:
        room.rating = calculate_rating(room)

    # Ordina prima per Online, bestroom (1=ottimali) e poi per il rating in ordine decrescente
    rooms_sorted = sorted(rooms, key=lambda r: (r.online_status, r.bestroom, r.rating), reverse=True)
    return rooms_sorted



def mostra_migliori_stanze(request):
    # Trova le stanze ottimali usando la logica dei sensori
    migliori_stanze = find_optimal_room()

    # Se non ci sono stanze disponibili, mostra un messaggio di errore
    if not migliori_stanze:
        return render(request, 'migliori_stanze.html', {'errore': 'Non ci sono stanze disponibili.'})

    # Passa le stanze ottimali al template per essere visualizzate
    return render(request, 'migliori_stanze.html', {'aule': migliori_stanze})



# --------- ARDUINO BRIDGE ------------
# Il server Django riceve i dati da Arduino e aggiorna il database. Subito dopo, invia i dati su Adafruit IO.

# Funzione per generare lo stato della stanza
def generate_status(room):
    return {
        "temperature": "HIGH" if room.temperature > 26 else "OK",
        "humidity": "HIGH" if room.humidity > 60 else "OK",
        "co2": "HIGH" if room.co2 > 1000 else "OK",
        "light": "LOW" if room.light < 200 else "OK",
        "sound": "HIGH" if room.sound > 50 else "OK"
    }

# Funzione per verificare e inviare alert se necessario
def check_and_alert(room):
    if room.temperature > 30:
        alert_message = f"Alta temperatura nella {room.name}: {room.temperature}°C"
        send_alert(alert_message)
        print(alert_message)
        adjacent_rooms = Room.objects.exclude(name=room.name)  # Stanze adiacenti
        for adj_room in adjacent_rooms:
            send_command_to_room(adj_room.name, {"action": "RAFFREDDA", "value": 20})

# Controlla se tutte e tre le stanze del bridge sono aggiornate
def check_bridge_completion(bridge_name):
    rooms = Room.objects.filter(bridge=bridge_name)
    return rooms.count() == 3 and all(room.online_status for room in rooms)

# Mappa dinamica delle stanze su Adafruit
def upload_bridge_to_adafruit(bridge_name):
    rooms = Room.objects.filter(bridge=bridge_name)

    if rooms.count() != 3:
        print(f"❌ Errore: il bridge {bridge_name} non ha 3 stanze collegate.")
        return

    for i, room in enumerate(rooms):
        # Imposta la posizione della stanza su Adafruit (1, 2, 3)
        room.adafruit_position = i + 1
        room.online_status = True
        room.save()
        send_room_data_to_adafruit(room, room.adafruit_position)

    print(f"✅ Bridge {bridge_name} caricato correttamente su Adafruit.")

# Endpoint per ricevere i dati dal bridge e salvarli nel database
@csrf_exempt
@csrf_exempt
def receive_sensor_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bridge_name = data.get('bridge_name', 'default_bridge')
            room_name = data.get('room_name', 'default_room')
            temperature = data.get('temperature')
            humidity = data.get('humidity')
            co2 = data.get('co2')
            light = data.get('light')
            sound = data.get('sound')
            people = data.get('people', 0)
            room_size = data.get('room_size', 25)
            latitudine = data.get('latitudine', 44.62902432803542)
            longitudine = data.get('longitudine', 10.94885144130329)
            price = data.get('price', 0)

            # Verifica dati mancanti
            if not all([temperature, humidity, co2, light, sound]):
                return JsonResponse({"error": "Dati mancanti"}, status=400)

            # Crea o aggiorna la stanza nel database come Offline
            room, created = Room.objects.update_or_create(
                name=room_name,
                bridge=bridge_name,
                defaults={
                    'temperature': temperature,
                    'humidity': humidity,
                    'co2': co2,
                    'light': light,
                    'sound': sound,
                    'room_size': room_size,
                    'people': people,
                    'latitudine': latitudine,
                    'longitudine': longitudine,
                    'price': price,
                    'online_status': False  # Inizialmente Offline
                }
            )

            print(f"Stanza '{room_name}' associata al bridge '{bridge_name}' salvata come Offline.")

            # Controlla se ci sono 3 stanze con lo stesso bridge
            rooms_same_bridge = Room.objects.filter(bridge=bridge_name)

            if rooms_same_bridge.count() == 3:
                print(f"🏠 Trovate 3 stanze con lo stesso bridge '{bridge_name}'. Preparazione invio a Adafruit...")
                
                # Manda i dati su Adafruit e marca come Online
                for i, room in enumerate(rooms_same_bridge):
                    position = i + 1  # Posizione da 1 a 3
                    success = send_room_data_to_adafruit(room, position)
                    if success:
                        room.online_status = True
                        room.adafruit_position = position
                        room.save()
                        print(f"✅ Stanza '{room.name}' inviata ad Adafruit come Online (Posizione {position}).")
                    else:
                        print(f"❌ Errore nell'invio della stanza '{room.name}' ad Adafruit.")

            return JsonResponse({
                "status": "success",
                "message": f"Dati ricevuti da {room.name}",
                "room_id": room.id
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato JSON non valido"}, status=400)
        except Exception as e:
            print(f"Errore: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Metodo non valido. Solo POST consentito."}, status=405)






# --------- API FLUTTER ------------

# Crea un ViewSet per gestire le operazioni CRUD: Il ViewSet viene utilizzato per gestire tutte le operazioni REST (GET, POST, PUT, DELETE).
# Questo RoomViewSet gestirà tutte le operazioni sulle stanze (aule) usando il RoomSerializer
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()  # Recupera tutte le stanze dal database
    serializer_class = RoomSerializer  # Usa il serializer per trasformare i dati


# Nuova vista API per Flutter che restituisce le migliori aule in formato JSON
from django.http import JsonResponse

# Nuova vista API per Flutter che restituisce le migliori aule in formato JSON
def api_migliori_stanze(request):
    # Trova le migliori stanze utilizzando la funzione find_optimal_room
    migliori_stanze = find_optimal_room()

    # Verifica se ci sono stanze disponibili
    if not migliori_stanze:
        return JsonResponse({'error': 'No rooms available'}, status=404)

    # Prepara i dati in formato JSON
    rooms_data = []
    for room in migliori_stanze:
        rooms_data.append({
            'name': room.name,
            'price': round(room.price, 1),               # Prezzo arrotondato
            'temperature': round(room.temperature, 1),   # Temperatura arrotondata
            'humidity': round(room.humidity, 1),         # Umidità arrotondata
            'light': round(room.light, 1),               # Luce arrotondata
            'co2': round(room.co2, 1),                   # CO2 arrotondato
            'sound': round(room.sound, 1),               # Rumore arrotondato
            'room_size': round(room.room_size, 1),       # Dimensione stanza arrotondata
            'people': room.people,                       # Numero di persone
            'probability': round(room.probability, 1),   # Probabilità arrotondata
            'latitudine': round(room.latitudine, 5),     # Latitudine arrotondata
            'longitudine': round(room.longitudine, 5),   # Longitudine arrotondata
            'bestroom': room.bestroom,                   # Se è una delle migliori stanze
            'rating': round(room.rating, 1)              # Rating arrotondato
        })

    # Restituisci la lista di aule come JSON
    return JsonResponse({'rooms': rooms_data})


#posizione
@csrf_exempt
def receive_location_data(request):
    if request.method == 'POST':
        try:
            # Ottieni i dati di input dal corpo della richiesta (in formato JSON)
            data = json.loads(request.body)

            # Estrai longitudine e latitudine dai dati
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            

            if longitude is None or latitude is None:
                return JsonResponse({"error": "latitude and Longitude are required"}, status=400)

            # Qui puoi salvare i dati nel database o processarli come necessario
            print(f"Received location: Latitude={latitude}, Longitude={longitude}")

            return JsonResponse({"status": "success", "latitude": latitude, "longitude": longitude}, status=200)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method. Only POST is allowed."}, status=405)