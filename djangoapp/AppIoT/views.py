from django.shortcuts import render
import pandas as pd
from django.http import HttpResponse
from django.http import JsonResponse
import json
from django.views import View
from django.views.generic import ListView
from django.shortcuts import render
from .ml_model.ml_model import train_model, predict_and_sort_rooms
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from .serializers import RoomSerializer
from rest_framework import viewsets

from .models import Room

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

#PREDICT ML
# predice se la nuova stanza è buona o no
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
        # Aggiungi altri URL qui, se necessario
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

    # Ordina prima per bestroom (1=ottimali) e poi per il rating in ordine decrescente
    rooms_sorted = sorted(rooms, key=lambda r: (r.bestroom, r.rating), reverse=True)
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

@csrf_exempt
def receive_sensor_data(request):
    if request.method == 'POST':
        try:
            # Debug: stampa il corpo della richiesta
            print("Raw request body:", request.body)
            
            # Verifica il Content-Type
            if request.content_type != 'application/json':
                return JsonResponse({"error": "Content-Type must be application/json"}, status=400)

            # Carica i dati JSON inviati
            data = json.loads(request.body)

            # Estrai i dati dai sensori e il nome del bridge
            bridge_name = data.get('bridge_name', 'bridge_stanza1_piano1')  # Nome del bridge con valore predefinito
            temperature = data.get('temperature')
            humidity = data.get('humidity')
            light_scaled = data.get('lightSensor')
            co2_scaled = data.get('Quality')
            sound = data.get('sound')
            people = data.get('people', 0)  # Valore predefinito se non fornito
            room_size = data.get('room_size', 25)  # Valore predefinito
            latitudine = data.get('latitudine', 44.62902432803542)  
            longitudine = data.get('longitudine', 10.94885144130329)
            price = data.get('price', 0)  # Valore predefinito
            room_type = data.get('type', 'studio')  # Tipo di stanza predefinito

            # Verifica che tutti i dati necessari siano presenti
            if not all(v is not None for v in [temperature, humidity, light_scaled, co2_scaled, sound]):
                return JsonResponse({"error": "Missing data fields"}, status=400)

            # Prepara i dati per la predizione
            input_data = pd.DataFrame([{
                'Temperature': temperature,
                'Humidity': humidity,
                'Light_scaled': light_scaled,
                'CO2_scaled': co2_scaled,
                'Sound': sound,
                'Room_Size': room_size,
                'People': people
            }])

            # Predici se la stanza è ottimale
            try:
                print("Dati ricevuti per la predizione:", input_data)

                # Predici se la stanza è ottimale
                prediction = predict_and_sort_rooms(input_data)
                print("Risultato della predizione:", prediction)

                bestroom_prediction = int(prediction.iloc[0]['predicted_class'])  # 0 = non ottimale, 1 = ottimale
                probability = float(prediction.iloc[0]['probability'])
                print(f"Predizione: BestRoom={bestroom_prediction}, Probabilità={probability}")
            except Exception as e:
                return JsonResponse({"error": f"Prediction error: {str(e)}"}, status=500)

            # Aggiorna o crea la stanza nel database
            print("Aggiorno/creo la stanza nel database...")
            room, created = Room.objects.update_or_create(
                bridge=bridge_name,  # Cerca una stanza con questo bridge
                defaults={  # Se esiste, aggiorna questi campi
                    'name': bridge_name,  # Può essere personalizzato
                    'temperature': temperature,
                    'humidity': humidity,
                    'light': light_scaled,
                    'co2': co2_scaled,
                    'sound': sound,
                    'room_size': room_size,
                    'people': people,
                    'latitudine': latitudine,
                    'longitudine': longitudine,
                    'price': price,
                    'type': room_type,
                    'bestroom': bestroom_prediction,
                    'probability': probability
                }
            )

            # Risposta in caso di successo
            if created:
                message = f"New room created: {room.name}"
            else:
                message = f"Room updated: {room.name}"

            return JsonResponse({
                "status": "success",
                "message": message,
                "room_id": room.id,
                "bestroom": bestroom_prediction,
                "probability": probability
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)





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

