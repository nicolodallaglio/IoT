import warnings
from sklearn.exceptions import InconsistentVersionWarning
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
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
from django.conf import settings
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
    greeting_message = "Welcome"
    
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

def calcola_alert_level(room):
    if room.temperature > 50 and room.co2 > 2000:
        return "FIRE"
    if room.co2 > 1200:
        return "HIGH CO2"
    if room.people >= room.room_size:
        return "MAX CAPACITY"
    if room.sound > 50:
        return "HIGH NOISE"
    if room.light < 400:
        return "LOW LIGHT"
    return "OK"

def admin_dashboard(request):
    stanze = Room.objects.all().order_by('bridge')

    bridges = {}
    for stanza in stanze:
        bridge_name = stanza.bridge or "Nessun Bridge"
        if bridge_name not in bridges:
            bridges[bridge_name] = []

        stanza.alert_level = calcola_alert_level(stanza)
        bridges[bridge_name].append(stanza)

    return render(request, 'admin_dashboard.html', {'bridges': bridges})


# ----------------- ALGORITHM --------------------

def calculate_rating(room, user_lat=None, user_lon=None, user=None, max_price=30):
    # ---- Sensor Score ----
    temp_score = max(0, 1 - abs(round(room.temperature, 1) - 22) / 10)
    co2_score = max(0, 1 - abs(round(room.co2, 1) - 400) / 1000)
    sound_score = max(0, 1 - abs(round(room.sound, 1) - 30) / 40)
    light_score = min(round(room.light, 1) / 1000, 1)

    sensor_score = (
        0.30 * temp_score +
        0.35 * co2_score +
        0.20 * sound_score +
        0.15 * light_score
    )

    # ---- Distance Score ----
    distance_score = 0
    if user_lat is not None and user_lon is not None and room.latitudine and room.longitudine:
        distance = haversine(user_lat, user_lon, room.latitudine, room.longitudine)
        max_distance = 2000  
        distance_score = max(0, 1 - (distance / max_distance))
        if distance <= max_distance:
            print(f"Stanza vicina trovata: {room.name} a {distance:.2f} m")

    # ---- Price Score ----
    price_normalized = max(0, (max_price - room.price) / max_price)

    # ---- Feedback Score ----
    feedback_score = 0
    feedbacks = room.feedbacks.all()
    if feedbacks.exists():
        avg_voto = feedbacks.aggregate(Avg('voto'))['voto__avg']
        feedback_score = min(avg_voto / 5, 1)

    # ---- Event Score ----
    event_score = event_proximity_score(room, user) if user else 0

    # ---- Final Rating (Weighted Sum) ----
    final_rating = (
        0.40 * sensor_score +
        0.20 * price_normalized +
        0.10 * distance_score +
        0.05 * feedback_score +
        0.25 * event_score
    )

    return round(final_rating, 2)


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
            print(f"WARNING: Warning sent on {topic}: {payload}")
        else:
            print(f"Errore nell'invio dell'alert su {topic}: {payload}")
    except Exception as e:
        print(f"Errore durante l'invio MQTT su {topic}: {e}")


def check_and_alert(room, bridge_name):
    # Critical alerts (CRITICAL)
    if room.temperature > 45 and room.co2 > 2000:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Fire alarm: {room.temperature}°C and {room.co2} ppm"
        send_alert_mqtt(room, alert_message, severity="CRITICAL")
        print(f"WARNING: {alert_message}")

    if room.people >= room.room_size:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Maximum capacity reached: {room.people} people"
        send_alert_mqtt(room, alert_message, severity="CRITICAL")
        print(f"WARNING: {alert_message}")

    # Less critical alerts (WARNING)
    if room.temperature > 30:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : High temperature: {room.temperature}°C"
        send_alert_mqtt(room, alert_message)
        print(f"WARNING: {alert_message}")
    
    if room.temperature < 17:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Low temperature: {room.temperature}°C"
        send_alert_mqtt(room, alert_message)
        print(f"WARNING: {alert_message}")

    if room.co2 > 750:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : High CO2: {room.co2} ppm"
        send_alert_mqtt(room, alert_message)
        print(f"WARNING: {alert_message}")

    if room.light < 400 and room.people > 0:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Low light: {room.light} lux"
        send_alert_mqtt(room, alert_message)
        print(f"WARNING: {alert_message}")

    if room.light and room.people == 0:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Light off: {room.light} lux"
        send_alert_mqtt(room, alert_message)
        print(f"WARNING: {alert_message}")

    if room.light > 650:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : High light: {room.light} lux"
        send_alert_mqtt(room, alert_message)
        print(f"WARNING: {alert_message}")

    if room.sound > 50:
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : High noise: {room.sound} dB"
        send_alert_mqtt(room, alert_message)
        print(f"WARNING: {alert_message}")

    if room.people > (room.room_size / 2 + 10):
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Overcrowding: {room.people} people"
        send_alert_mqtt(room, alert_message)
        print(f"WARNING: {alert_message}")
    elif room.people > (room.room_size / 2):
        alert_message = f"[WARNING:{room.name}:{bridge_name}] : Half capacity reached in {room.name}: {room.people} people"
        send_alert_mqtt(room, alert_message)
        print(f"WARNING: {alert_message}")
    
    
    #Notification to Flutter
    #utenti_nella_stanza = User.objects.filter(latitudine=room.latitudine, longitudine=room.longitudine)
    utenti_nella_stanza = User.objects.filter(id=3) #, latitudine=room.latitudine, longitudine=room.longitudine)

    for user in utenti_nella_stanza:
        if room.co2 > 1000:
            print(f"FLUTTER: → Invio notifica CO2 alta a utente ID {user.id}")
            send_user_notification(user, f"CO2 alta in {room.name}. Ti consigliamo di spostarti o di aerare.")
        elif room.sound > 60:
            print(f"FLUTTER: → Invio notifica rumore elevato a utente ID {user.id}")
            send_user_notification(user, f"Rumore elevato in {room.name}. Cerca una stanza più silenziosa.")
        elif room.people >= room.room_size:
            print(f"FLUTTER: → Invio notifica affollamento a utente ID {user.id}")
            send_user_notification(user, f"Troppa gente in {room.name}. Ti consigliamo di spostarti.")

    # Notifica utenti vicini alla stanza in fiamme
    if room.temperature > 50 and room.co2 > 2000:
        utenti = User.objects.all()
        for utente in utenti:
            distanza = haversine(room.latitudine, room.longitudine, utente.latitudine, utente.longitudine)
            if distanza < 300:  # tra 0 e 300 metri
                send_user_notification(utente, f"Allarme incendio in {room.name} a {int(distanza)} metri. Evita l’area!")



#--- Bridge priority--

def bridge_priority_score(bridge_name):
    rooms = Room.objects.filter(bridge=bridge_name)
    if not rooms.exists():
        return 0

    now = timezone.now()

     # CONTROLLA SE QUALCHE STANZA È STATA AGGIORNATA DI RECENTE (ad es. negli ultimi 60 secondi)
    recently_updated = rooms.filter(last_update__gte=now - timedelta(seconds=60)).exists()
    
    if not recently_updated:
        print(f"BRIDGE LOGIC: no room updated recently for '{bridge_name}', score set to 0")
        rooms.update(last_score_time=None)  # Resetto anche last_score_time per sicurezza
        return 0
    

    latest_score_time = max([room.last_score_time for room in rooms if room.last_score_time], default=None)

    # Se scaduto, reset e aggiorno direttamente QUI
    if latest_score_time is None or now - latest_score_time > timedelta(seconds=100):
        print(f"BRIDGE LOGIC: Bridge '{bridge_name}' has an outdated score, reset to 0")
        rooms.update(last_score_time=now)
        return 0

    # Logica di calcolo normale dello score...
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

    rooms.update(last_score_time=now)

    return final_score


# Distance
def haversine(lat1, lon1, lat2, lon2):
    # None check
    if None in [lat1, lon1, lat2, lon2]:
        print("Errore: Coordinate non valide per il calcolo della distanza.")
        return float('inf')

    R = 6371
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

        # Giorno per modello prezzo
        giorno_eng = datetime.now().strftime("%A")
        giorni_tradotti = {
            "Monday": "Lunedì", "Tuesday": "Martedì", "Wednesday": "Mercoledì",
            "Thursday": "Giovedì", "Friday": "Venerdì", "Saturday": "Sabato", "Sunday": "Domenica"
        }
        giorno = giorni_tradotti.get(giorno_eng, giorno_eng)

        # Eventi nelle vicinanze
        distanza_massima = 5000  # 5 km
        evento_vicinanze = any(
            haversine(latitudine, longitudine, e.latitudine, e.longitudine) <= distanza_massima
            for e in Event.objects.all()
        )

        # --- Predizione ML ---
        input_data = pd.DataFrame([{
            'Temperature': temperature,
            'Humidity': humidity,
            'Light_scaled': light,
            'CO2_scaled': co2,
            'Sound': sound,
            'Room_Size': room_size,
            'People': people
        }])

        input_data["Temperature"] = (input_data["Temperature"] - 23).abs()
        input_data["Humidity"] = (input_data["Humidity"] - 50).abs()
        input_data["Light_scaled"] = (input_data["Light_scaled"] - 500).abs()

        prediction = predict_and_sort_rooms(input_data).iloc[0]
        probability = round(prediction['probability'], 3)
        probability = max(0, min(probability, 1))
        predicted_class = 1 if probability >= 0.5 else 0

        # --- Prezzo ---
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

        # --- Aggiornamento stanza ---
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

        # --- Storico e predizione ---
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

        # --- Alert ---
        check_and_alert(room, bridge_name)

        # --- Aggiorna last_update e priority score ---
        room.last_update = timezone.now()
        room.save()

        new_score = bridge_priority_score(bridge_name)
        print(f"BRIDGE LOGIC: bridge score '{bridge_name}': {new_score}")

        # --- Logica assegnazione posizioni Adafruit ---
        stanze_bridge = Room.objects.filter(bridge=bridge_name)
        posizioni_possibili = {1, 2, 3}

        # Se ci sono più di 3 stanze, limitiamo comunque a 3 posizioni
        stanze_da_mandare = stanze_bridge[:3]

        # Reset a tutti
        Room.objects.filter(bridge=bridge_name).update(online_status=False, adafruit_position=None)

        # Assegna le posizioni a tutte le stanze (fino a massimo 3)
        for posizione, stanza in enumerate(stanze_da_mandare, start=1):
            stanza.adafruit_position = posizione
            stanza.online_status = True
            stanza.save()
            print(f"DEBUG: Room {stanza.name} assigned position {stanza.adafruit_position} and online status {stanza.online_status}")
            print(f"DEBUG: Assegnata nuova posizione {posizione} a {stanza.name}")
            send_room_data_to_adafruit(stanza, posizione)

        # Pulisci le eventuali posizioni vuote (se meno di 3 stanze)
        posizioni_occupate = {r.adafruit_position for r in stanze_da_mandare}
        posizioni_libere = posizioni_possibili - posizioni_occupate

        for posizione_libera in posizioni_libere:
            print(f"DEBUG: Clear position {posizione_libera} on Adafruit (no room assigned)")
            send_room_data_to_adafruit(None, posizione_libera)
        
        # Reset delle stanze NON attive (quelle non tra le prime 3 del bridge)
        stanze_attive = list(Room.objects.filter(bridge=bridge_name, online_status=True, adafruit_position__isnull=False))
        stanze_id_attive = {r.id for r in stanze_attive}

        # Tutte le stanze del bridge
        stanze_bridge = Room.objects.filter(bridge=bridge_name)


        for stanza in stanze_bridge:
            if stanza.id not in stanze_id_attive:
                stanza.online_status = False
                stanza.adafruit_position = None
                stanza.save()

        aggiorna_bridge_attivo(bridge_name)

        # ---- Pulizia posizioni vuote su Adafruit se ci sono meno di 3 stanze attive ----
        stanze_attive = list(Room.objects.filter(online_status=True, adafruit_position__isnull=False))
        posizioni_occupate = {r.adafruit_position for r in stanze_attive}
        posizioni_possibili = {1, 2, 3}
        posizioni_libere = posizioni_possibili - posizioni_occupate

        # Pulisci le posizioni libere su Adafruit
        for posizione_libera in posizioni_libere:
            print(f"ADAFRUIT: Clear position {posizione_libera} on Adafruit (no room assigned)")
            send_room_data_to_adafruit(None, posizione_libera)

        
        # --- Pubblica lo status della stanza su Adafruit ---
        # Definizione dello status in base ai parametri
        if room.temperature > 45 and room.co2 > 2000:
            status = "FIRE"
        elif room.people >= room.room_size:
            status = "FULL"
        elif room.co2 > 1200:
            status = "HIGH_CO2"
        elif room.sound > 50:
            status = "NOISY"
        else:
            status = "OK"


        # Preparo il payload da inviare
        status_payload = {
            "status": status,
            "co2": room.co2,
            "sound": room.sound,
            "people": room.people,
            "room_size": room.room_size,
            "bridge_name": bridge_name
        }

        # Feed Adafruit per questa stanza
        username = settings.ADAFRUIT_AIO_USERNAME
        feed_status = f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/stanza-{room.adafruit_position}.status" if room.adafruit_position else None

        if feed_status:  # Invio solo se la stanza ha una posizione assegnata
            print(f"ADAFRUIT: Checking status publish for {room.name} → position: {room.adafruit_position}")
            send_mqtt_command(feed_status, status_payload)
            print(f"ADAFRUIT: Status published to {feed_status}: {status_payload}")
        else:
            print(f"ADAFRUIT: No Adafruit position for room {room.name}, status not published.")

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

def aggiorna_bridge_attivo(current_bridge_name):
    # Calculate the score for each bridge
    bridges = Room.objects.values_list('bridge', flat=True).distinct()
    punteggi = {}

    for bridge in bridges:
        punteggi[bridge] = bridge_priority_score(bridge)

    # Filter out bridges with score <= 0
    active_bridges = {bridge: score for bridge, score in punteggi.items() if score > 0}

    if active_bridges:
        # Select the bridge with the highest score
        bridge_attivo = max(active_bridges, key=active_bridges.get)
        print(f"BRIDGE LOGIC: Active bridge selected → {bridge_attivo} with score {punteggi[bridge_attivo]}")
    else:
        # No active bridge with score > 0, fallback to the current one
        bridge_attivo = current_bridge_name
        print(f"BRIDGE LOGIC: No active bridges with score > 0, keeping current bridge '{bridge_attivo}' as active.")

    # Turn off all rooms not belonging to the active bridge
    Room.objects.exclude(bridge=bridge_attivo).update(online_status=False, adafruit_position=None)
    Room.objects.exclude(bridge=bridge_attivo).update(last_score_time=None)  # Also reset last_score_time

    # Do not touch the rooms of the active bridge (they are handled by receive_sensor_data)
    return bridge_attivo


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


#  API Flutter for best rooms
def api_migliori_stanze(request):
    try:
        user = User.objects.get(name="Riccardo", surname="Reale")
        user_lat, user_lon = user.latitudine, user.longitudine
        print(f"Debug: User position: Nome={user.name},Cognome={user.surname},Latitudine={user_lat}, Longitudine={user_lon}")
    except User.DoesNotExist:
        print("Error: No position found for user.")
        return JsonResponse({'error': 'No position found for user'}, status=404)

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
            'price': round(room.price, 1),               # Prezzo
            'temperature': round(room.temperature, 1),   # Temperatura
            'humidity': round(room.humidity, 1),         # Umidità
            'light': round(room.light, 1),               # Luce
            'co2': round(room.co2, 1),                   # CO2
            'sound': round(room.sound, 1),               # Rumore
            'room_size': round(room.room_size, 1),       # Dimensione stanza
            'people': room.people,                       # Numero di persone
            'probability': round(room.probability, 1),   # Probabilità 
            'latitudine': round(room.latitudine, 5),     # Latitudine 
            'longitudine': round(room.longitudine, 5),   # Longitudine
            'bestroom': room.bestroom,                   # Se è una delle migliori stanze
            'rating': round(room.rating, 1)              # Rating 
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

            print(f"DEBUG: Position saved: {user} - Lat: {latitudine}, Lon: {longitudine}")

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
                return JsonResponse({"error": "Missing name or events"}, status=400)

            print(f"FLUTTER: Events received for {name} {surname}:")

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
                    print(f"FLUTTER: Event '{titolo}' ignored (keyword missmatching)")
                    continue

                if not titolo or not inizio or not fine:
                    continue

                print(f"FLUTTER: Event received correctly: {titolo}")

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
                        print(f"DEBUG: Geocoded '{luogo}' → ({latitudine}, {longitudine})")
                    else:
                        print(f"DEBUG: Nominatim NON ha trovato il luogo: '{luogo}'")
                except Exception as e:
                    print(f"Error: error in geocoding '{luogo}': {e}")

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
            data = json.loads(request.body)
            print("FLUTTER: Data received:", data)

            name_stanza = data.get('name_stanza')
            latitudine = data.get('latitudine')
            longitudine = data.get('longitudine')
            voto = int(data.get('voto'))
            commento = data.get('commento', '')
            name = data.get('name')
            surname = data.get('surname')

            print(f"FLUTTER: Room: {name_stanza}, Lat: {latitudine}, Lon: {longitudine}")
            print(f"FLUTTER: Rating: {voto}, Comment: {commento}")
            print(f"FLUTTER: User: {name} {surname}")

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

            print("Room found:", room)

            utente, created = User.objects.get_or_create(name=name, surname=surname)
            print("User found:", utente, "- Creato nuovo?" , created)

            Feedback.objects.create(
                room=room,
                utente=utente,
                voto=voto,
                commento=commento
            )

            print("DEBUG: Feedback success")

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
    print(f"FLUTTER: Notification sent to {user.name} {user.surname} {user.id} on Flutter: {message}")
