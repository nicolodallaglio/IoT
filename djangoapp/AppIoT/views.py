from django.shortcuts import render
from django.views import View
from django.views.generic import ListView
from django.shortcuts import render
from django.http import (HttpResponse, JsonResponse)
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
import math
from datetime import datetime
import pickle
import locale
import unicodedata
import pandas as pd
import json

from .ml_model.ml_classificazione import predict_and_sort_rooms
from AppIoT.utils import check_and_notify_adjacent_rooms
from .serializers import RoomSerializer
from AppIoT.mqtt.mqtt_client import send_mqtt_command
from .models import ( Room, User, Event )
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
"""algoritmo considererà vari criteri, come il prezzo, la disponibilità e il rating della stanza
Daremo un peso alla distanza dall'utente, il 20% del rating totale.
La distanza sarà normalizzata (per esempio, massimo 5 km).
La parte "distanza" contribuirà negativamente al rating (più è lontano, peggiore è il rating)."""

def calculate_rating(room, user_lat=None, user_lon=None):
    # Calcola il punteggio combinato per i dati dei sensori (arrotondando a una cifra decimale)
    sensor_score = (
        (1 - abs(round(room.temperature, 1) - 22) / 10) +  # 22°C come valore ottimale per il comfort
        (1 - abs(round(room.co2, 1) - 400) / 1000) +       # 400 ppm come valore ottimale per il comfort
        (1 - abs(round(room.sound, 1) - 30) / 40) +        # 30 dB come valore ottimale per il comfort acustico
        (round(room.light, 1) / 1000)                      # Normalizza la luce
    ) / 4  # Media dei punteggi dei sensori

    # Calcolo della distanza dall'utente (se fornita)
    distance_score = 0
    if user_lat is not None and user_lon is not None and room.latitudine and room.longitudine:
        distance = haversine(user_lat, user_lon, room.latitudine, room.longitudine)
        max_distance = 5000  # Consideriamo 5 km come distanza massima
        distance_score = max(0, 1 - (distance / max_distance))  # Normalizzato tra 0 e 1
        print(f"Distanza per la stanza {room.name}: {distance} m, Score: {distance_score}")

    # Normalizza il prezzo: assumendo che 50 sia il massimo prezzo
    price_normalized = (50 - room.price) / 50

    # Rating finale combinando comfort (sensori), prezzo e distanza
    return 0.6 * sensor_score + 0.2 * price_normalized + 0.2 * distance_score


def find_optimal_room(user_lat=None, user_lon=None):
    # Recupera tutte le stanze
    rooms = Room.objects.all()  

    if not rooms.exists():
        return None  # Nessuna stanza disponibile

    # Aggiungi il rating a ciascuna stanza e ordina in base a bestroom e rating
    for room in rooms:
        room.rating = calculate_rating(room, user_lat, user_lon)

    # Ordina prima per Online, bestroom (1=ottimali) e poi per il rating in ordine decrescente
    rooms_sorted = sorted(rooms, key=lambda r: (r.online_status, r.bridge != 'empty', r.bestroom, r.rating), reverse=True)
    return rooms_sorted[:20]



def mostra_migliori_stanze(request):
    # Recupera l'utente per ottenere la posizione
    try:
        user = User.objects.get(name="Mario", surname="Rossi")
        user_lat, user_lon = user.latitudine, user.longitudine
    except User.DoesNotExist:
        user_lat, user_lon = None, None

    # Trova le stanze ottimali usando la logica dei sensori e la posizione dell'utente
    migliori_stanze = find_optimal_room(user_lat, user_lon)

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
    #temperature e allarme incendio
    if room.temperature > 30:
        alert_message = f"Alta temperatura nella {room.name}: {room.temperature}°C"
        send_alert_mqtt(room, "Alta temperatura", room.temperature)
        print(alert_message)

    if room.temperature > 50 and room.co2 > 2000:
        alert_message = f"Alta temperatura e alta Co2 nella {room.name}: {room.temperature}°C"
        send_alert_mqtt(room, "Allarme incendio", room.temperature)
        print(alert_message)
    
    #co2
    if room.co2 > 500:
        alert_message = f"CO2 elevata nella {room.name}: {room.co2} ppm"
        send_alert_mqtt(room, "CO2 alta", room.co2)
        print(alert_message)
    
    #light
    if room.light < 200:
        alert_message = f"Luce molto bassa nella {room.name}: {room.light} lux"
        send_alert_mqtt(room, "Luce molto bassa", room.light)
        print(alert_message)

    if room.light < 800:
        alert_message = f"Luce bassa nella {room.name}: {room.light} lux"
        send_alert_mqtt(room, "Luce bassa", room.light)
        print(alert_message)

    #sound
    if room.sound > 50:
        alert_message = f"Rumore elevato nella {room.name}: {room.sound} dB"
        send_alert_mqtt(room, "Rumore alto", room.sound)
        print(alert_message)

    #N* persone
    if room.people > (room.room_size/2):
        alert_message = f"Metà capienza raggiunta nella {room.name}: {room.people} persone"
        send_alert_mqtt(room, "Metà capienza", room.people)
        print(alert_message)

    if room.people > (room.room_size /2 + 10):
        alert_message = f"Troppo affollamento nella {room.name}: {room.people} persone"
        send_alert_mqtt(room, "Troppo affollato", room.people)
        print(alert_message)
    
    if room.people == room.room_size:
        alert_message = f"Capacità massima raggiunta nella {room.name}: {room.people} persone"
        send_alert_mqtt(room, "Capacità massima", room.people)
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


# Calcolo della distanza tra due coordinate geografiche
def haversine(lat1, lon1, lat2, lon2):
    # Controllo se una delle coordinate è None
    if None in [lat1, lon1, lat2, lon2]:
        print("❌ Errore: Coordinate non valide per il calcolo della distanza.")
        return float('inf')  # Restituiamo una distanza infinita per ignorare l'evento

    R = 6371  # Raggio della Terra in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c * 1000  # Converti in metri
    return distance


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

            print(temperature, humidity, co2, light, sound)

            # Verifica dati mancanti
            if not all([temperature, humidity, co2, light, sound]):
                return JsonResponse({"error": "Dati mancanti"}, status=400)

            # -- Ottenere il giorno corrente in italiano --

            # Ottieni il giorno corrente in inglese
            giorno_eng = datetime.now().strftime("%A")

            # Mappatura dei giorni della settimana da inglese a italiano senza accenti
            giorni_tradotti = {
                "Monday": "Lunedì",
                "Tuesday": "Martedì",
                "Wednesday": "Mercoledì",
                "Thursday": "Giovedì",
                "Friday": "Venerdì",
                "Saturday": "Sabato",
                "Sunday": "Domenica"
            }

            # Converti il giorno corrente da inglese a italiano senza accenti
            giorno = giorni_tradotti.get(giorno_eng, giorno_eng)
            print(f"Giorno corrente (tradotto e normalizzato): {giorno}")

            # -- Calcolo degli eventi nelle vicinanze --
            distanza_massima = 10000  # Distanza massima in metri (10km)
            eventi_vicini = Event.objects.all()
            evento_vicinanze = 0  # Default: nessun evento vicino

            for evento in eventi_vicini:
                distanza = haversine(latitudine, longitudine, evento.latitudine, evento.longitudine)
                if distanza <= distanza_massima:
                    evento_vicinanze = 1
                    print(f"Evento vicino trovato: {evento.title} a {distanza:.2f} metri.")
                    break
            
                
            # -- ML -- CLASSIFICAZIONE
            input_data = pd.DataFrame([{
                'Temperature': temperature,
                'Humidity': humidity,
                'Light_scaled': light,
                'CO2_scaled': co2,
                'Sound': sound,
                'Room_Size': room_size,
                'People': people
            }])
            predicted_room = predict_and_sort_rooms(input_data).iloc[0]
            predicted_class = int(predicted_room['predicted_class'])
            probability = round(predicted_room['probability'], 3)

            # -- ML -- PREDIZIONE PREZZO
            # Caricare il modello di pricing
            with open("AppIoT\ml_model\modello_prezzo.pkl", "rb") as file:
                model, label_encoder = pickle.load(file)

            # Codificare il giorno
            giorno_codificato = label_encoder.transform([giorno])[0]

            # Creare il DataFrame per la predizione del prezzo
            prezzo_input = pd.DataFrame([{
                "Capienza Massima": room_size,
                "Evento nelle Vicinanze": int(evento_vicinanze),
                "Giorno Codificato": giorno_codificato
            }])

            # Fare la predizione del prezzo
            prezzo_predetto = model.predict(prezzo_input)[0]
            prezzo_arrotondato = 5 * round(prezzo_predetto / 5)

            # -- CREAZIONE O AGGIORNAMENTO STANZA NEL DB --
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
                    'price': prezzo_arrotondato,  # Prezzo predetto
                    'online_status': False,
                    'bestroom': predicted_class,
                    'probability': probability
                }
            )

            print(f"Stanza '{room_name}' associata al bridge '{bridge_name}' salvata come Offline.")
            print(f"📊 Stanza '{room_name}' classificata come {'Migliore' if predicted_class == 1 else 'Non Ottimale'} con probabilità {probability * 100:.1f}% e prezzo {prezzo_arrotondato}€.")


            # ⚠️ Verifica e invio alert
            check_and_alert(room)

            # Verifica se ci sono 3 stanze con lo stesso bridge
            rooms_same_bridge = Room.objects.filter(bridge=bridge_name)

            # Invia i dati solo se ci sono 3 stanze collegate allo stesso bridge
            if rooms_same_bridge.count() == 3:
                print(f"🏠 Trovate 3 stanze con lo stesso bridge '{bridge_name}'. Preparazione invio a Adafruit...")
                for i, room in enumerate(rooms_same_bridge):
                    position = i + 1
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
                "probability": probability,
                "prezzo_predetto": prezzo_arrotondato
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


# --------- API FLUTTER ------------

# Crea un ViewSet per gestire le operazioni CRUD: Il ViewSet viene utilizzato per gestire tutte le operazioni REST (GET, POST, PUT, DELETE).
# Questo RoomViewSet gestirà tutte le operazioni sulle stanze (aule) usando il RoomSerializer
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()  # Recupera tutte le stanze dal database
    serializer_class = RoomSerializer  # Usa il serializer per trasformare i dati


# Nuova vista API per Flutter che restituisce le migliori aule in formato JSON
def api_migliori_stanze(request):
    # Recupera l'ultima posizione salvata nel database
    try:
        user = User.objects.get(name="Mario", surname="Rossi")
        user_lat, user_lon = user.latitudine, user.longitudine
        print(f"Ultima posizione utente trovata: Latitudine={user_lat}, Longitudine={user_lon}")
    except User.DoesNotExist:
        print("❌ Errore: Nessuna posizione salvata per l'utente")
        return JsonResponse({'error': 'Nessuna posizione utente salvata'}, status=404)

    # Trova le migliori stanze utilizzando la funzione find_optimal_room con la posizione dell'utente
    migliori_stanze = find_optimal_room(user_lat, user_lon)

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



#posizione utente da app flutter
@csrf_exempt
def receive_location_data(request):
    if request.method == 'POST':
        try:
            # Ottieni i dati di input dal corpo della richiesta (in formato JSON)
            data = json.loads(request.body)

            # Estrai longitudine e latitudine dai dati
            latitudine = data.get('latitudine')
            longitudine = data.get('longitudine')
            
            # Verifica la validità delle coordinate
            if latitudine is None or longitudine is None:
                return JsonResponse({"error": "Latitudine e Longitudine sono obbligatorie"}, status=400)
            if not isinstance(latitudine, (int, float)) or not isinstance(longitudine, (int, float)):
                return JsonResponse({"error": "Latitudine e Longitudine devono essere numerici"}, status=400)

            # Nome e cognome fissi
            name = "Mario"
            surname = "Rossi"

            # Salva o aggiorna l'utente nel database
            user, created = User.objects.update_or_create(
                name=name,
                surname=surname,
                defaults={'latitudine': latitudine, 'longitudine': longitudine}
            )

            print(f"Posizione salvata: {user} - Lat: {latitudine}, Lon: {longitudine}")

            return JsonResponse({"status": "success", "latitudine": latitudine, "longitudine": longitudine}, status=200)
        
        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato JSON non valido"}, status=400)
        except Exception as e:
            print(f"Errore nel salvataggio della posizione utente: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Metodo non valido. Solo POST è consentito."}, status=405)
