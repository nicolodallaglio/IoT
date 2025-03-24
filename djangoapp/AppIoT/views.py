from django.shortcuts import render
import pandas as pd
from django.http import HttpResponse
from django.http import JsonResponse
import json
from django.views import View
from django.views.generic import ListView
from django.shortcuts import render
from .ml_model.ml_model import predict_and_sort_rooms
from AppIoT.utils import check_and_notify_adjacent_rooms
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from .serializers import RoomSerializer
from rest_framework import viewsets
from AppIoT.mqtt.mqtt_client import send_mqtt_command
from .models import Room

from AppIoT.adafruit.adafruit_client import (
    send_room_data_to_adafruit,
    send_to_adafruit,
    adafruit_room_mapping
)

 
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
    rooms_sorted = sorted(rooms, key=lambda r: (r.online_status, r.bridge!='empty', r.bestroom, r.rating), reverse=True)
    return rooms_sorted[:20]



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

# Funzione per inviare un avviso tramite MQTT
def send_alert_mqtt(room, alert_type, value):
    topic = "nicodalla99/feeds/bridge.alert"
    payload = f"{alert_type}: {value} in {room.name}"  # Payload come stringa
    try:
        result = send_mqtt_command(topic, payload)
        if result:
            print(f"✅ Alert inviato correttamente tramite MQTT: {payload}")
        else:
            print(f"❌ Errore nell'invio dell'alert tramite MQTT: {payload}")
    except Exception as e:
        print(f"❌ Errore durante l'invio tramite MQTT: {e}")


# Funzione per inviare un comando specifico a una stanza
def send_room_command(room_name, command):
    topic = f"{room_name}/comando"
    payload = {"action": command}
    send_mqtt_command(topic, payload)
    print(f"🚀 Comando inviato tramite MQTT a {room_name}: {payload}")

# Funzione per verificare e inviare alert se necessario
def check_and_alert(room):
    if room.temperature > 30:
        alert_message = f"Alta temperatura nella {room.name}: {room.temperature}°C"
        send_alert_mqtt(room, "Alta temperatura", room.temperature)
        print(alert_message)

    if room.temperature > 50 and room.co2 > 2000:
        alert_message = f"Alta temperatura e alta Co2 nella {room.name}: {room.temperature}°C"
        send_alert_mqtt(room, "Allarme incendio", room.temperature)
        print(alert_message)
    
    if room.co2 > 1000:
        alert_message = f"CO2 elevata nella {room.name}: {room.co2} ppm"
        send_alert_mqtt(room, "CO2 alta", room.co2)
        print(alert_message)
    
    if room.sound > 50:
        alert_message = f"Rumore elevato nella {room.name}: {room.sound} dB"
        send_alert_mqtt(room, "Rumore alto", room.sound)
        print(alert_message)

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
def receive_sensor_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bridge_name = data.get('bridge_name', 'missing_bridge')
            room_name = data.get('room_name', 'missing_name')
            temperature = data.get('temperature')
            humidity = data.get('humidity')
            co2 = data.get('co2')
            light = data.get('light')
            sound = data.get('sound')
            people = data.get('people')
            room_size = data.get('room_size')
            latitudine = data.get('latitudine')
            longitudine = data.get('longitudine')
            price = data.get('price')

            # Verifica dati mancanti
            if not all([temperature, humidity, co2, light, sound]):
                return JsonResponse({"error": "Dati mancanti"}, status=400)
            
            #--ML--
            # Crea il DataFrame per la predizione
            input_data = pd.DataFrame([{
                'Temperature': temperature,
                'Humidity': humidity,
                'Light_scaled': light,
                'CO2_scaled': co2,
                'Sound': sound,
                'Room_Size': room_size,
                'People': people
            }])

            # Chiama la funzione di predizione
            predicted_room = predict_and_sort_rooms(input_data).iloc[0]
            predicted_class = int(predicted_room['predicted_class'])
            probability = round(predicted_room['probability'], 3)


            # Crea o aggiorna la stanza nel database, con la classificazione
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
                    'online_status': False,  # Inizialmente Offline
                    'bestroom': predicted_class,  # Imposta la classificazione
                    'probability': probability  # Aggiungi la probabilità
                }
            )

            print(f"Stanza '{room_name}' associata al bridge '{bridge_name}' salvata come Offline.")
            print(f"📊 Stanza '{room_name}' classificata come {'Migliore' if predicted_class == 1 else 'Non Ottimale'} con probabilità {probability * 100:.1f}%.")

            # ⚠️ Chiamata alla funzione per verificare e inviare alert
            check_and_alert(room)

            # Controlla se ci sono 3 stanze con lo stesso bridge
            rooms_same_bridge = Room.objects.filter(bridge=bridge_name)

            # Invia i dati solo se ci sono 3 stanze collegate allo stesso bridge
            if rooms_same_bridge.count() == 3:
                print(f"🏠 Trovate 3 stanze con lo stesso bridge '{bridge_name}'. Preparazione invio a Adafruit...")

                # Itera sulle 3 stanze e invia i dati ad Adafruit
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
                "room_id": room.id,
                "classification": predicted_class,
                "probability": probability
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato JSON non valido"}, status=400)
        except Exception as e:
            print(f"Errore: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Metodo non valido. Solo POST consentito."}, status=405)


# -------------------- ML --------------------
# PREDICT ML -- predire se la nuova stanza è buona o no
def predict_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            input_data = pd.DataFrame(data)

            if input_data.empty:
                return JsonResponse({"error": "Empty input data provided"}, status=400)

            # Usa la funzione predict_and_sort_rooms per fare previsioni
            sorted_rooms = predict_and_sort_rooms(input_data)

            # Prepara la risposta come JSON
            response = {
                "sorted_rooms": sorted_rooms[['Temperature', 'Humidity', 'Light_scaled', 'CO2_scaled', 'Sound', 'Room_Size', 'People', 'probability', 'predicted_class']].to_dict(orient='records')
            }
            return JsonResponse(response, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method. Only POST is allowed."}, status=405)


# logica di regressione lineare per predire il prezzo dinamico delle stanze 
def predici_prezzo(input_data):
    # Inserisci qui il modello di regressione lineare per predire i prezzi
    modello = ...  # Carica il modello addestrato
    prezzo_predetto = modello.predict(input_data)
    return prezzo_predetto


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