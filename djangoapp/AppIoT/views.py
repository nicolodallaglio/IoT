from django.shortcuts import render
from django.views import View
from django.views.generic import ListView
from django.http import (HttpResponse, JsonResponse)
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
import math
from datetime import datetime
import re
import pickle
import locale
import unicodedata
import pandas as pd
import json
import numpy as np
from django.shortcuts import render
from .models import Room
from django.utils import timezone
from collections import defaultdict
from django.db.models import Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .ml_model.ml_regressione import predict_and_sort_rooms
from .serializers import RoomSerializer
from AppIoT.mqtt.mqtt_client import send_mqtt_command
from .models import ( Room, User, Event, UserEvent, PredictionHistory, SensorHistory, Feedback)
from AppIoT.adafruit.adafruit_client import (
    send_room_data_to_adafruit)
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="smartrooms-geocoder")

 
# ---------------- INDEX -------------------------

def index(request):
    greeting_message = "Benvenuto in SmartRooms"
    
    # Recupera le stanze disponibili
    stanze = Room.objects.all()
    
    other_urls = [
        {'url': '/dashboard-admin/', 'label': 'Dashboard'},
        {'url': '/migliori-stanze/', 'label': 'SmartRooms'},
        
    ]

    return render(request, 'index.html', {
        'greeting_message': greeting_message,
        'other_urls': other_urls,
        'stanze': stanze
    })

# ----------------- ADMIN DASHBOARD ---------------------

def admin_dashboard(request):
    stanze = Room.objects.all().order_by('bridge')

    bridges = {}
    for stanza in stanze:
        bridge_name = stanza.bridge or "Nessun Bridge"
        if bridge_name not in bridges:
            bridges[bridge_name] = []
        
        # Puoi calcolare un alert_level fittizio se non c'è nel modello
        alert = "Incendio" if stanza.temperature > 50 and stanza.co2 > 2000 else "OK"
        stanza.alert_level = alert

        bridges[bridge_name].append(stanza)

    return render(request, 'admin_dashboard.html', {'bridges': bridges})


# ----------------- ALGORITMO --------------------

def calculate_rating(room, user_lat=None, user_lon=None, user=None):
    # Calcola il punteggio combinato per i dati dei sensori (arrotondando a una cifra decimale)
    sensor_score = (
        (1 - abs(round(room.temperature, 1) - 22) / 10) +  # 22°C valore ottimale
        (1 - abs(round(room.co2, 1) - 400) / 1000) +       # 400 ppm valore ottimale
        (1 - abs(round(room.sound, 1) - 30) / 40) +        # 30 dB valore ottimale
        (round(room.light, 1) / 1000)                      # Normalizza la luce
    ) / 4  # Media dei punteggi dei sensori

    # Calcolo della distanza dall'utente, max distanza 2 km
    distance_score = 0
    if user_lat is not None and user_lon is not None and room.latitudine and room.longitudine:
        distance = haversine(user_lat, user_lon, room.latitudine, room.longitudine)
        max_distance = 2000  
        distance_score = max(0, 1 - (distance / max_distance))
        if distance <= max_distance:
            print(f"Stanza vicina trovata: {room.name} a {distance:.2f} m")

    # Normalizza il prezzo: assumendo che 30 sia il massimo prezzo
    price_normalized = (30 - room.price) / 30

    feedback_score = 0
    feedbacks = room.feedbacks.all()
    if feedbacks.exists():
        avg_voto = feedbacks.aggregate(Avg('voto'))['voto__avg']
        feedback_score = min(avg_voto / 5, 1)

    # Calcola il contributo degli eventi se c'è l'utente
    event_score = event_proximity_score(room, user) if user else 0

    final_rating = (
        0.5 * sensor_score +
        0.2 * price_normalized +
        0.2 * distance_score +
        0.05 * feedback_score +
        0.05 * event_score
    )

    return final_rating


def find_optimal_room(user_lat=None, user_lon=None):
    # Recupera tutte le stanze
    rooms = Room.objects.all()  

    if not rooms.exists():
        return None

    try:
        user = User.objects.get(name="Riccardo", surname="Reale")
    except User.DoesNotExist:
        user = None
    
    for room in rooms:
        room.rating = calculate_rating(room, user_lat, user_lon, user=user)

    # Ordina prima per Online, bestroom (1=ottimali) e poi per il rating in ordine decrescente
    rooms_sorted = sorted(rooms, key=lambda r: (r.online_status, r.bridge != 'empty', r.bestroom, r.rating), reverse=True)
    return rooms_sorted[:20]



def mostra_migliori_stanze(request):
    try:
        user = User.objects.get(name="Riccardo", surname="Reale")
        user_lat, user_lon = user.latitudine, user.longitudine
    except User.DoesNotExist:
        user_lat, user_lon = None, None

    migliori_stanze = find_optimal_room(user_lat, user_lon)

    if not migliori_stanze:
        return render(request, 'migliori_stanze.html', {'errore': 'Non ci sono stanze disponibili.'})

    return render(request, 'migliori_stanze.html', {'aule': migliori_stanze})



# --------- ARDUINO BRIDGE ------------
# Il server Django riceve i dati da Arduino e aggiorna il database. Subito dopo, invia i dati su Adafruit IO.

# Funzione per inviare un alert MQTT
def send_alert_mqtt(room, value, severity="WARNING"):
    """if severity == "CRITICAL":
        topic = "nicodalla99/feeds/bridge.alert"
    else:"""
    
    topic = "nicodalla99/feeds/bridge.warning"

    #payload = f"[{severity}] {alert_type}: {value} in {room.name}"
    payload = f"{value} in {room.name}"

    try:
        result = send_mqtt_command(topic, payload)
        if result:
            print(f"Debug: Warning inviato su {topic}: {payload}")
        else:
            print(f"Errore nell'invio dell'alert su {topic}: {payload}")
    except Exception as e:
        print(f"Errore durante l'invio MQTT su {topic}: {e}")


# Funzione per verificare e inviare alert se necessario
def check_and_alert(room, bridge_name):
    # Alert gravi (CRITICAL)
    if room.temperature > 50 and room.co2 > 2000:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Allarme incendio: {room.temperature}°C e {room.co2} ppm"
        send_alert_mqtt(room, alert_message, severity="CRITICAL")
        print(f"Debug: {alert_message}")

    if room.people >= room.room_size:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Capacita' massima raggiunta: {room.people} persone"
        send_alert_mqtt(room, alert_message, severity="CRITICAL")
        print(f"Debug: {alert_message}")

    # Alert meno gravi (WARNING)
    if room.temperature > 26:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Alta temperatura: {room.temperature} gradi"
        send_alert_mqtt(room, alert_message)
        print(f"Debug: {alert_message}")
    
    if room.temperature < 17:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Bassa temperatura: {room.temperature} gradi"
        send_alert_mqtt(room, alert_message)
        print(f"Debug: {alert_message}")

    if room.co2 > 750:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : CO2 elevata: {room.co2} ppm"
        send_alert_mqtt(room, alert_message)
        print(f"Debug: {alert_message}")

    if room.light < 300:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Luce bassa: {room.light} lux"
        send_alert_mqtt(room, alert_message)
        print(f"Debug: {alert_message}")

    if room.light > 650:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Luce alta: {room.light} lux"
        send_alert_mqtt(room, alert_message)
        print(f"Debug: {alert_message}")

    if room.sound > 50:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Rumore elevato: {room.sound} dB"
        send_alert_mqtt(room, alert_message)
        print(f"Debug: {alert_message}")

    if room.people > (room.room_size / 2):
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Meta' capienza raggiunta {room.name}: {room.people} persone"
        send_alert_mqtt(room, alert_message)
        print(f"Debug: {alert_message}")

    if room.people > (room.room_size / 2 + 10):
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Troppo affollamento: {room.people} persone"
        send_alert_mqtt(room, alert_message)
        print(f"Debug: {alert_message}")
    
    
    #NOTIFICA ALL'UTENTE FLUTTER
    # Se ci sono utenti associati alla stanza, notifica
    #utenti_nella_stanza = User.objects.filter(latitudine=room.latitudine, longitudine=room.longitudine)
    utenti_nella_stanza = User.objects.filter(id=3, latitudine=room.latitudine, longitudine=room.longitudine)

    for user in utenti_nella_stanza:
        if room.co2 > 1000:
            send_user_notification(user, f"CO2 alta in {room.name}. Ti consigliamo di spostarti.")
        elif room.sound > 60:
            send_user_notification(user, f"Rumore elevato in {room.name}. Cerca una stanza più silenziosa.")
        elif room.people >= room.room_size:
            send_user_notification(user, f"Troppa gente in {room.name}. Raggiunta la capienza massima.")

    # Notifica utenti vicini alla stanza in fiamme
    if room.temperature > 50 and room.co2 > 2000:
        utenti = User.objects.all()
        for utente in utenti:
            distanza = haversine(room.latitudine, room.longitudine, utente.latitudine, utente.longitudine)
            if distanza < 300:  # tra 0 e 300 metri
                send_user_notification(utente, f"Allarme incendio in {room.name} a {int(distanza)} metri. Evita l’area!")



#--- Calcola il punteggio di priorità del bridge--

def bridge_priority_score(bridge_name):
    rooms = Room.objects.filter(bridge=bridge_name)
    if not rooms.exists():
        return 0

    now = timezone.now()

    # Se il timestamp è troppo vecchio, resettiamo
    latest_score_time = max([room.last_score_time for room in rooms if room.last_score_time], default=None)
    if latest_score_time and now - latest_score_time > timedelta(seconds=60):
        print(f"Debug: Bridge '{bridge_name}' ha uno score scaduto, reset a 0")
        return 0

    # Logica normale del punteggio
    variation_scores = []
    for room in rooms:
        v = 0
        if all([room.last_temperature, room.temperature]):
            v += abs(room.temperature - room.last_temperature) / 10
        if all([room.last_co2, room.co2]):
            v += abs(room.co2 - room.last_co2) / 1000
        if all([room.last_sound, room.sound]):
            v += abs(room.sound - room.last_sound) / 50
        if all([room.last_light, room.light]):
            v += abs(room.light - room.last_light) / 1000
        if all([room.last_humidity, room.humidity]):
            v += abs(room.humidity - room.last_humidity) / 100
        variation_scores.append(v)

    variation_score = min(np.mean(variation_scores), 1) if variation_scores else 0

    # Affollamento medio e critici
    full_rooms = 0
    total_ratio = 0
    for room in rooms:
        if room.room_size:
            ratio = room.people / room.room_size
            total_ratio += ratio
            if ratio >= 0.7:
                full_rooms += 1
    avg_occupancy = total_ratio / len(rooms) if rooms else 0
    occupancy_score = min(avg_occupancy, 1)

    critical_events = 0
    for room in rooms:
        if room.co2 and room.co2 > 1000:
            critical_events += 1
        if room.sound and room.sound > 60:
            critical_events += 1
        if room.temperature and room.temperature > 30:
            critical_events += 1
    critical_score = min(critical_events / (len(rooms) * 2), 1)

    final_score = round(0.4 * variation_score + 0.4 * occupancy_score + 0.2 * critical_score, 3)

    # Aggiorna il timestamp
    rooms.update(last_score_time=now)

    return final_score


# Calcolo della distanza tra due coordinate geografiche
def haversine(lat1, lon1, lat2, lon2):
    # Controllo se una delle coordinate è None
    if None in [lat1, lon1, lat2, lon2]:
        print("Errore: Coordinate non valide per il calcolo della distanza.")
        return float('inf')  # Restituiamo una distanza infinita per ignorare l'evento

    R = 6371  # Raggio della Terra in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c * 1000  # Converti in metri
    return distance

def event_proximity_score(room, user):
    eventi = UserEvent.objects.filter(utente=user)
    min_distance = float('inf')
    
    for evento in eventi:
        if evento.latitudine and evento.longitudine:
            distance = haversine(room.latitudine, room.longitudine, evento.latitudine, evento.longitudine)
            if distance < min_distance:
                min_distance = distance
    
    # Se nessun evento ha coordinate, score = 0
    if min_distance == float('inf'):
        return 0

    # Score decrescente: più l'evento è vicino, più alto è lo score
    return max(0, 1 - (min_distance / 5000))  # 5 km → score da 1 a 0

@csrf_exempt
def receive_sensor_data(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Metodo non valido. Solo POST è consentito."}, status=405)

    try:
        # --- Parsing dati in arrivo ---
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
        type = data.get('type', 'missing_type')

        if not all([temperature, humidity, co2, light, sound]):
            return JsonResponse({"error": "Dati sensori mancanti"}, status=400)

        sound = sound / 20 + 20

        # --- Giorno attuale codificato per il modello prezzo ---
        giorno_eng = datetime.now().strftime("%A")
        giorni_tradotti = {
            "Monday": "Lunedì", "Tuesday": "Martedì", "Wednesday": "Mercoledì",
            "Thursday": "Giovedì", "Friday": "Venerdì", "Saturday": "Sabato", "Sunday": "Domenica"
        }
        giorno = giorni_tradotti.get(giorno_eng, giorno_eng)

        # --- Eventi nelle vicinanze ---
        distanza_massima = 5000  # 5 km
        evento_vicinanze = any(
            haversine(latitudine, longitudine, e.latitudine, e.longitudine) <= distanza_massima
            for e in Event.objects.all()
        )

        # --- ML: Regressione e classificazione stanza ---
        input_data = pd.DataFrame([{
            'Temperature': temperature,
            'Humidity': humidity,
            'Light_scaled': light,
            'CO2_scaled': co2,
            'Sound': sound,
            'Room_Size': room_size,
            'People': people
        }])

        # Preprocessing per la regressione: applica la differenza assoluta dai valori ideali
        input_data["Temperature"] = (input_data["Temperature"] - 23).abs()
        input_data["Humidity"] = (input_data["Humidity"] - 50).abs()
        input_data["Light_scaled"] = (input_data["Light_scaled"] - 500).abs()

        prediction = predict_and_sort_rooms(input_data).iloc[0]
        probability = round(prediction['probability'], 3)
        # Limita la probabilità tra 0 e 1 per evitare valori assurdi
        probability = max(0, min(probability, 1))
        # Determina bestroom sulla base di una soglia (es. 0.5)
        predicted_class = 1 if probability >= 0.5 else 0

        # --- ML: Prezzo predetto ---
        if type and type.lower() == "studio":
            prezzo_arrotondato = 0
        else:
            with open("AppIoT/ml_model/modello_prezzo.pkl", "rb") as file:
                model, label_encoder = pickle.load(file)

            giorno_codificato = label_encoder.transform([giorno])[0]
            prezzo_input = pd.DataFrame([{
                "Capienza Massima": room_size,
                "Evento nelle Vicinanze": int(evento_vicinanze),
                "Giorno Codificato": giorno_codificato
            }])
            prezzo_predetto = model.predict(prezzo_input)[0]
            prezzo_arrotondato = 5 * round(prezzo_predetto / 5)


        # --- Recupera stanza se già esiste ---
        room = Room.objects.filter(name=room_name, bridge=bridge_name).first()
        if room:
            room.last_temperature = room.temperature
            room.last_co2 = room.co2
            room.last_sound = room.sound
            room.last_light = room.light
            room.last_humidity = room.humidity
            room.save()

        # --- Crea/Aggiorna stanza ---
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
                'price': prezzo_arrotondato,
                'online_status': False,
                'bestroom': predicted_class,
                'probability': probability,
                'last_prediction_time': timezone.now(),
                'type': type
            }
        )

        if(room.type == "studio"):
            print(f"Debug: Stanza studio '{room.name}' associata al bridge '{bridge_name}' classificata come {'Ottima' if predicted_class == 1 else 'Non Ottima'} con probabilità {probability * 100:.1f}% e prezzo gratuito.")
        else:
            print(f"Debug: Stanza lavoro '{room.name}' associata al bridge '{bridge_name}' classificata come {'Ottima' if predicted_class == 1 else 'Non Ottima'} con probabilità {probability * 100:.1f}% e prezzo {prezzo_arrotondato}€.")


        PredictionHistory.objects.create(
            room=room,
            predicted_class=predicted_class,
            probability=probability,
            predicted_price=prezzo_arrotondato,
            source="arduino"
        )

        SensorHistory.objects.create(
            room=room,
            temperature=temperature,
            humidity=humidity,
            co2=co2,
            light=light,
            sound=sound,
            people=people
        )
        
        # --- Alert MQTT se serve ---
        check_and_alert(room, bridge_name)

        # --- Bridge Priority Logic ---
        room.last_update = timezone.now()
        room.save()

        new_score = bridge_priority_score(bridge_name)
        print(f"Debug: Punteggio del bridge '{bridge_name}': {new_score}")

        # Check se tutte le stanze del bridge sono aggiornate di recente
        bridge_rooms = Room.objects.filter(bridge=bridge_name)
        update_threshold = timezone.now() - timedelta(seconds=1200000)

        # Debug: stampa stato aggiornamento di ogni stanza del bridge
        print(f"Debug: Stato aggiornamenti stanze del bridge '{bridge_name}':")
        for r in bridge_rooms:
            print(f" - {r.name}: aggiornamento = {r.last_update}")

        # Solo se tutte le stanze sono aggiornate di recente, procedi
        if all(r.last_update and r.last_update > update_threshold for r in bridge_rooms):
            active_bridges = Room.objects.filter(online_status=True).values_list("bridge", flat=True).distinct()
            should_upload = all(bridge_priority_score(b) < new_score for b in active_bridges if b != bridge_name)
            print(f"Debug: Bridge attivi: {[(b, bridge_priority_score(b)) for b in active_bridges]}")

            if should_upload:
                print(f"Debug: Upload dei dati per il bridge '{bridge_name}' con punteggio {new_score}")

                # Reset stanze attive
                Room.objects.filter(online_status=True).update(online_status=False, adafruit_position=None)

                stanze_attive = []
                stanze_selezionate = set()

                for room in bridge_rooms.order_by('-probability'):
                    print(f"Debug: Candidato → {room.name} con probability {room.probability}")
                    if (room.name, room.bridge) not in stanze_selezionate:
                        stanze_attive.append(room)
                        stanze_selezionate.add((room.name, room.bridge))
                    if len(stanze_attive) == 3:
                        break

                print("Debug: Stanze selezionate per upload Adafruit (senza duplicati):")
                for stanza in stanze_attive:
                    print(f" - {stanza.name} → probabilità: {stanza.probability}")


                # Assegna posizione SOLO se esiste una stanza per quella posizione
                for i, stanza in enumerate(stanze_attive, start=1):
                    stanza.adafruit_position = i
                    stanza.online_status = True
                    stanza.save()

                # Ricarica dal DB le stanze aggiornate
                stanze_attive = Room.objects.filter(id__in=[s.id for s in stanze_attive])

                # Disattiva le altre stanze
                Room.objects.filter(bridge=bridge_name).exclude(id__in=[s.id for s in stanze_attive]).update(
                    online_status=False,
                    adafruit_position=None
                )

                # Ricarica le stanze dal DB per avere la versione aggiornata
                stanze_attive = Room.objects.filter(id__in=[s.id for s in stanze_attive])

                print("Debug: Stanze selezionate per upload Adafruit:")
                for stanza in stanze_attive:
                    pos = stanza.adafruit_position
                    print(f" - {stanza.name} → posizione: {pos}, probabilità: {stanza.probability}")
                    success = send_room_data_to_adafruit(stanza, pos)
                    if success:
                        print(f"Dati inviati per {stanza.name} su stanza-{pos}")
                    else:
                        print(f"Fallito invio per {stanza.name}")
        else:
            print(f"Debug: In attesa che tutte le stanze del bridge '{bridge_name}' siano aggiornate...")


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
        print(f"Errore generale: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

# Vista per mostrare lo storico dei sensori
def storico_sensori(request, room_id):
    room = Room.objects.get(id=room_id)
    history = room.sensor_history.order_by('timestamp')[:50]

    context = {
        'room': room,
        'labels': [h.timestamp.strftime("%H:%M") for h in history],
        'temps': [h.temperature for h in history],
        'hums': [h.humidity for h in history],
        'co2s': [h.co2 for h in history],
        'lights': [h.light for h in history],
        'sounds': [h.sound for h in history],
        'people': [h.people for h in history],
    }

    return render(request, 'storico_sensori.html', context)



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
                "sorted_rooms": sorted_rooms[['Temperature', 'Humidity', 'Light_scaled', 'CO2_scaled', 'Sound', 'Room_Size', 'People', 'probability']].to_dict(orient='records')
            }

            return JsonResponse(response, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method. Only POST is allowed."}, status=405)


def storico_predizioni(request, room_id):
    room = Room.objects.get(id=room_id)
    history = room.predictions.all().order_by('-timestamp')[:20]
    return render(request, 'storico_predizioni.html', {'room': room, 'history': history})



# --------- API FLUTTER ------------

#  Recupera tutte le stanze dal database e usa il serializer per trasformare i dati
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer


# Nuova vista API per Flutter che restituisce le migliori aule in formato JSON
def api_migliori_stanze(request):
    # Recupera l'ultima posizione salvata nel database
    try:
        user = User.objects.get(name="Riccardo", surname="Reale")
        user_lat, user_lon = user.latitudine, user.longitudine
        print(f"Debug: posizione utente: Nome={user.name},Cognome={user.surname},Latitudine={user_lat}, Longitudine={user_lon}")
    except User.DoesNotExist:
        print("Errore: Nessuna posizione salvata per l'utente")
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
            'type': room.type,   
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


# Posizione utente da app flutter
@csrf_exempt
def receive_location_data(request):
    if request.method == 'POST':
        try:
            # Ottieni i dati di input dal corpo della richiesta (in formato JSON)
            data = json.loads(request.body)

            # Estrai longitudine e latitudine dai dati
            name= data.get('name')
            surname= data.get('surname')
            latitudine = data.get('latitudine')
            longitudine = data.get('longitudine')
            
            """name = "Riccardo"
            surnarme = "Reale" """
            # Verifica la validità delle coordinate
            if name is None or surname is None:
                return JsonResponse({"error": "Nome e Cognome sono obbligatori"}, status=400)
            if latitudine is None or longitudine is None:
                return JsonResponse({"error": "Latitudine e Longitudine sono obbligatorie"}, status=400)
            if not isinstance(latitudine, (int, float)) or not isinstance(longitudine, (int, float)):
                return JsonResponse({"error": "Latitudine e Longitudine devono essere numerici"}, status=400)


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

# EVENTI utente da app flutter
@csrf_exempt
def api_eventi_utente(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            name = data.get('name', '')
            surname = data.get('surname', '')
            eventi = data.get('eventi', [])

            if not name or not eventi:
                return JsonResponse({"error": "Nome o eventi mancanti"}, status=400)

            print(f"Debug: Eventi ricevuti per {name} {surname}:")

            # Lista di parole chiave per filtrare gli eventi
            keywords = ['studio', 'riunione', 'esame', 'aula', 'conferenza', 'lezione', 'seminario']

            utente, _ = User.objects.get_or_create(name=name, surname=surname)

            for evento in eventi:
                titolo = evento.get('titolo', '').lower()  # Converto in minuscolo per confrontare senza case-sensitive
                luogo = evento.get('luogo', '')
                inizio = evento.get('inizio')
                fine = evento.get('fine')

                # Filtra gli eventi che NON contengono nessuna delle keyword → SKIP
                if not any(kw in titolo for kw in keywords):
                    print(f"Debug: Evento '{titolo}' ignorato (non matcha le keyword)")
                    continue

                if not titolo or not inizio or not fine:
                    continue

                print(f"Debug: Evento valido: {titolo}")

                # Ignora le lat/lon arrivate
                latitudine = None
                longitudine = None

                try:
                    luogo_clean = unicodedata.normalize('NFKD', luogo).encode('ascii', 'ignore').decode('utf-8')
                    luogo_clean = pulisci_luogo(luogo)
                    location = geolocator.geocode(luogo_clean)
                    if location:
                        latitudine = location.latitude
                        longitudine = location.longitude
                        print(f"Debug: Geocodificato '{luogo}' → ({latitudine}, {longitudine})")
                    else:
                        print(f"Debug: Nominatim NON ha trovato il luogo: '{luogo}'")
                except Exception as e:
                    print(f"Debug: Errore geocoding '{luogo}': {e}")

                # Conversione timestamp ISO con Z
                fromiso = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))

                UserEvent.objects.get_or_create(
                    utente=utente,
                    titolo=titolo,
                    luogo=luogo,
                    inizio=fromiso(inizio),
                    fine=fromiso(fine),
                    latitudine=latitudine,
                    longitudine=longitudine
                )

            return JsonResponse({"message": "Eventi salvati correttamente (filtrati per keyword)"})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato JSON non valido"}, status=400)
        except Exception as e:
            print(f"Errore nel salvataggio degli eventi: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Metodo non valido. Solo POST è consentito."}, status=405)


def pulisci_luogo(luogo_raw):
    # Rimuove virgolette e caratteri non ASCII
    luogo = unicodedata.normalize('NFKD', luogo_raw).encode('ascii', 'ignore').decode('utf-8')
    # Rimuove eventuali CAP e provincia
    luogo = re.sub(r'\d{5}(?:\s?[A-Z]{2})?', '', luogo)
    # Limita a max 2 componenti
    componenti = [x.strip() for x in luogo.split(',')]
    return ", ".join(componenti[:2])

#FEEDBACK stanza dell'utente da app flutter
@csrf_exempt
def api_feedback_stanza(request):
    if request.method == 'POST':
        try:
            print("Richiesta POST ricevuta")

            data = json.loads(request.body)
            print("Dati ricevuti:", data)

            name_stanza = data.get('name_stanza')
            latitudine = data.get('latitudine')
            longitudine = data.get('longitudine')
            voto = int(data.get('voto'))
            commento = data.get('commento', '')
            name = data.get('name')
            surname = data.get('surname')

            print(f"Stanza: {name_stanza}, Lat: {latitudine}, Lon: {longitudine}")
            print(f"Voto: {voto}, Commento: {commento}")
            print(f"Utente: {name} {surname}")

            if not (1 <= voto <= 5):
                print("Errore: voto fuori scala")
                return JsonResponse({"error": "Voto fuori scala"}, status=400)

            if not all([name_stanza, latitudine, longitudine]):
                print("Errore: dati stanza incompleti")
                return JsonResponse({"error": "Dati stanza incompleti"}, status=400)

            room = Room.objects.filter(
                name=name_stanza,
                latitudine=latitudine,
                longitudine=longitudine
            ).first()

            if not room:
                print("Errore: stanza non trovata")
                return JsonResponse({"error": "Stanza non trovata"}, status=404)

            print("Stanza trovata:", room)

            utente, created = User.objects.get_or_create(name=name, surname=surname)
            print("Utente ottenuto:", utente, "- Creato nuovo?" , created)

            Feedback.objects.create(
                room=room,
                utente=utente,
                voto=voto,
                commento=commento
            )

            print("Feedback creato con successo")

            return JsonResponse({"message": "Feedback ricevuto!"})

        except Exception as e:
            print("Errore eccezione:", str(e))
            return JsonResponse({"error": str(e)}, status=500)

    print("Metodo non valido")
    return JsonResponse({"error": "Metodo non valido. Usa POST."}, status=405)

#Invio notifica all'user - se sono in una stanza e un'altra stanza prende fuoco mando una notifica agli utenti
def send_user_notification(user, message):
    #user.id=3
    topic = f"nicodalla99/feeds/utente_notifiche"
    send_mqtt_command(topic, message)
    print(f"Notifica inviata a {user.name} {user.surname} {user.id} sull'app Flutter: {message}")
