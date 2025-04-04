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
import numpy as np
from django.db.models import Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .ml_model.ml_classificazione import predict_and_sort_rooms
from .serializers import RoomSerializer
from AppIoT.mqtt.mqtt_client import send_mqtt_command
from .models import ( Room, User, Event, UserEvent, PredictionHistory, SensorHistory, Feedback)
from AppIoT.adafruit.adafruit_client import (
    send_room_data_to_adafruit)

 
# ---------------- INDEX -------------------------

def index(request):
    greeting_message = "Benvenuto in SmartRooms"
    
    # Recupera le stanze disponibili
    stanze = Room.objects.all()
    
    other_urls = [
        {'url': '/migliori-stanze/', 'label': 'SmartRooms'},
    ]

    return render(request, 'index.html', {
        'greeting_message': greeting_message,
        'other_urls': other_urls,
        'stanze': stanze
    })



# ----------------- ALGORITMO --------------------

def calculate_rating(room, user_lat=None, user_lon=None):
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

    return 0.5 * sensor_score + 0.2 * price_normalized + 0.2 * distance_score + 0.1 * feedback_score


def find_optimal_room(user_lat=None, user_lon=None):
    # Recupera tutte le stanze
    rooms = Room.objects.all()  

    if not rooms.exists():
        return None

    for room in rooms:
        room.rating = calculate_rating(room, user_lat, user_lon)

    # Ordina prima per Online, bestroom (1=ottimali) e poi per il rating in ordine decrescente
    rooms_sorted = sorted(rooms, key=lambda r: (r.online_status, r.bridge != 'empty', r.bestroom, r.rating), reverse=True)
    return rooms_sorted[:20]



def mostra_migliori_stanze(request):
    try:
        user = User.objects.get(name="Mario", surname="Rossi")
        user_lat, user_lon = user.latitudine, user.longitudine
    except User.DoesNotExist:
        user_lat, user_lon = None, None

    migliori_stanze = find_optimal_room(user_lat, user_lon)

    if not migliori_stanze:
        return render(request, 'migliori_stanze.html', {'errore': 'Non ci sono stanze disponibili.'})

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
def send_alert_mqtt(room, alert_type, value, severity="WARNING"):
    if severity == "CRITICAL":
        topic = "nicodalla99/feeds/bridge.alert"
    else:
        feed_room = f"stanza-{room.adafruit_position}"  # Es. stanza-1
        topic = f"nicodalla99/feeds/{feed_room}.alert"

    payload = f"[{severity}] {alert_type}: {value} in {room.name}"

    try:
        result = send_mqtt_command(topic, payload)
        if result:
            print(f"✅ Alert inviato su {topic}: {payload}")
        else:
            print(f"❌ Errore nell'invio dell'alert su {topic}: {payload}")
    except Exception as e:
        print(f"❌ Errore durante l'invio MQTT su {topic}: {e}")



# Funzione per inviare un comando specifico a una stanza
def send_room_command(room_name, command):  
    topic = f"{room_name}/comando"
    payload = {"action": command}
    send_mqtt_command(topic, payload)
    print(f"🚀 Comando inviato tramite MQTT a {room_name}: {payload}")

# Funzione per verificare e inviare alert se necessario
def check_and_alert(room):
    # Alert gravi (CRITICAL)
    if room.temperature > 50 and room.co2 > 2000:
        alert_message = f"Allarme incendio nella {room.name}: {room.temperature}°C e {room.co2} ppm"
        send_alert_mqtt(room, "Allarme incendio", alert_message, severity="CRITICAL")
        send_room_command(room.name, "emergenza_evacuazione")
        print(alert_message)

    if room.people >= room.room_size:
        alert_message = f"Capacità massima raggiunta nella {room.name}: {room.people} persone"
        send_alert_mqtt(room, "Capacità massima", alert_message, severity="CRITICAL")
        send_room_command(room.name, "blocco_ingressi")
        print(alert_message)

    # Alert meno gravi (WARNING)
    if room.temperature > 30:
        alert_message = f"Alta temperatura nella {room.name}: {room.temperature}°C"
        send_alert_mqtt(room, "Alta temperatura", alert_message)
        send_room_command(room.name, "attiva_ventilazione")
        print(alert_message)

    if room.co2 > 500:
        alert_message = f"CO2 elevata nella {room.name}: {room.co2} ppm"
        send_alert_mqtt(room, "CO2 alta", alert_message)
        send_room_command(room.name, "apri_finestra")
        print(alert_message)

    if room.light < 200:
        alert_message = f"Luce molto bassa nella {room.name}: {room.light} lux"
        send_alert_mqtt(room, "Luce molto bassa", alert_message)
        send_room_command(room.name, "accendi_luci")
        print(alert_message)

    if room.sound > 50:
        alert_message = f"Rumore elevato nella {room.name}: {room.sound} dB"
        send_alert_mqtt(room, "Rumore alto", alert_message)
        send_room_command(room.name, "mostra_cartello_silenzio")
        print(alert_message)

    if room.people > (room.room_size / 2):
        alert_message = f"Metà capienza raggiunta nella {room.name}: {room.people} persone"
        send_alert_mqtt(room, "Metà capienza", alert_message)
        print(alert_message)

    if room.people > (room.room_size / 2 + 10):
        alert_message = f"Troppo affollamento nella {room.name}: {room.people} persone"
        send_alert_mqtt(room, "Troppo affollato", alert_message)
        send_room_command(room.name, "limita_accessi")
        print(alert_message)
    
    # Comunicazione con altre stanze se condizioni critiche
    room_communication_logic(room)

    # Se ci sono utenti associati alla stanza, notifica
    utenti_nella_stanza = User.objects.filter(latitudine=room.latitudine, longitudine=room.longitudine)

    for user in utenti_nella_stanza:
        if room.co2 > 1000:
            send_user_notification(user, f"CO2 alta in {room.name}. Ti consigliamo di spostarti.")
        elif room.sound > 60:
            send_user_notification(user, f"Rumore elevato in {room.name}. Cerca una stanza più silenziosa.")
        elif room.people >= room.room_size:
            send_user_notification(user, f"Troppa gente in {room.name}. Raggiunta la capienza massima.")



def room_communication_logic(room):
    gruppo = room.adafruit_position
    if not gruppo:
        return  # Nessuna posizione Adafruit assegnata

    candidate_rooms = Room.objects.filter(adafruit_position=gruppo).exclude(id=room.id)

    # Stanze valide: poco affollate e classificate come ottimali
    stanze_valide = [
        r for r in candidate_rooms
        if r.people < (r.room_size * 0.5) and r.bestroom == 1
    ]

    if not stanze_valide:
        return

    # Trova la migliore in base al comfort
    target_room = max(stanze_valide, key=lambda r: calculate_rating(r))

    motivi = []
    if room.co2 > 1000:
        motivi.append("CO2 alta")
    if room.temperature > 30:
        motivi.append("Temperatura alta")
    if room.sound > 60:
        motivi.append("Rumore elevato")

    if motivi:
        motivo = ", ".join(motivi)

        # Comando alla stanza corrente → invita a spostarsi
        comando_spostamento = f"sposta_occupanti_in_{target_room.name}"
        send_room_command(room.name, comando_spostamento)

        # Comando alla stanza target → prepara accoglienza
        send_room_command(target_room.name, "prepara_accoglienza")

        print(f"📢 {room.name} → '{comando_spostamento}' | "
              f"{target_room.name} → 'prepara_accoglienza' | Motivo: {motivo}")



#--- Calcola il punteggio di priorità del bridge--

def bridge_priority_score(bridge_name):
    rooms = Room.objects.filter(bridge=bridge_name)
    if not rooms.exists():
        return 0

    now = timezone.now()

    # Se il timestamp è troppo vecchio, resettiamo
    latest_score_time = max([room.last_score_time for room in rooms if room.last_score_time], default=None)
    if latest_score_time and now - latest_score_time > timedelta(seconds=60):
        print(f"⏳ Bridge '{bridge_name}' ha uno score scaduto, reset a 0")
        return 0

    # ⬇️ Logica normale del punteggio
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
        type = data.get('type')

        if not all([temperature, humidity, co2, light, sound]):
            return JsonResponse({"error": "Dati mancanti"}, status=400)

        sound = sound / 20 + 20

        # --- Giorno attuale codificato per il modello prezzo ---
        giorno_eng = datetime.now().strftime("%A")
        giorni_tradotti = {
            "Monday": "Lunedì", "Tuesday": "Martedì", "Wednesday": "Mercoledì",
            "Thursday": "Giovedì", "Friday": "Venerdì", "Saturday": "Sabato", "Sunday": "Domenica"
        }
        giorno = giorni_tradotti.get(giorno_eng, giorno_eng)

        # --- Eventi nelle vicinanze ---
        distanza_massima = 10000  # 10 km
        evento_vicinanze = any(
            haversine(latitudine, longitudine, e.latitudine, e.longitudine) <= distanza_massima
            for e in Event.objects.all()
        )

        # --- ML: Classificazione stanza ---
        input_data = pd.DataFrame([{
            'Temperature': temperature,
            'Humidity': humidity,
            'Light_scaled': light,
            'CO2_scaled': co2,
            'Sound': sound,
            'Room_Size': room_size,
            'People': people
        }])
        prediction = predict_and_sort_rooms(input_data).iloc[0]
        predicted_class = int(prediction['predicted_class'])
        probability = round(prediction['probability'], 3)

        # --- ML: Prezzo predetto ---
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
                'last_prediction_time': timezone.now()
            }
        )

        print(f"📊 Stanza '{room.name}' classificata come {'Migliore' if predicted_class == 1 else 'Non Ottimale'} con probabilità {probability * 100:.1f}% e prezzo {prezzo_arrotondato}€.")

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
        check_and_alert(room)

        # --- Bridge Priority Logic ---
        new_score = bridge_priority_score(bridge_name)
        print(f"🎯 Punteggio del bridge '{bridge_name}': {new_score}")

        active_bridges = Room.objects.filter(online_status=True).values_list("bridge", flat=True).distinct()
        should_upload = all(bridge_priority_score(b) < new_score for b in active_bridges)
        print(f"🔍 Bridge attivi: {[(b, bridge_priority_score(b)) for b in active_bridges]}")

        if should_upload:
            print(f"🚀 Upload dei dati per il bridge '{bridge_name}' con punteggio {new_score}")

            Room.objects.filter(online_status=True).update(online_status=False, adafruit_position=None)
            stanze_attive = Room.objects.filter(bridge=bridge_name).order_by('-probability')[:3]

            for i, stanza in enumerate(stanze_attive, start=1):
                stanza.adafruit_position = i
                stanza.online_status = True
                stanza.save()

            Room.objects.filter(bridge=bridge_name).exclude(id__in=[s.id for s in stanze_attive]).update(
                online_status=False,
                adafruit_position=None
            )

            for stanza in stanze_attive:
                pos = stanza.adafruit_position
                success = send_room_data_to_adafruit(stanza, pos)
                if success:
                    print(f"✅ Dati inviati per {stanza.name} su stanza-{pos}")
                else:
                    print(f"❌ Fallito invio per {stanza.name}")

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
        print(f"❌ Errore generale: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

#Vista per mostrare lo storico dei sensori
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
                "sorted_rooms": sorted_rooms[['Temperature', 'Humidity', 'Light_scaled', 'CO2_scaled', 'Sound', 'Room_Size', 'People', 'probability', 'predicted_class']].to_dict(orient='records')
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

#EVENTI utente da app flutter
@csrf_exempt
def api_eventi_utente(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            name = data.get('name', 'Mario')
            surname = data.get('surname', 'Rossi')
            eventi = data.get('eventi', [])

            if not name or not eventi:
                return JsonResponse({"error": "Nome o eventi mancanti"}, status=400)

            utente, _ = User.objects.get_or_create(name=name, surname=surname)

            for evento in eventi:
                titolo = evento.get('titolo')
                luogo = evento.get('luogo', '')
                inizio = evento.get('inizio')  # formato ISO: '2025-03-31T10:00:00'
                fine = evento.get('fine')
                latitudine = evento.get('latitudine')
                longitudine = evento.get('longitudine')

                if not titolo or not inizio or not fine:
                    continue  # salta eventi incompleti

                UserEvent.objects.get_or_create(
                    utente=utente,
                    titolo=titolo,
                    luogo=luogo,
                    inizio=datetime.fromisoformat(inizio),
                    fine=datetime.fromisoformat(fine)
                )

            return JsonResponse({"message": "Eventi salvati correttamente"})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato JSON non valido"}, status=400)
        except Exception as e:
            print(f"Errore nel salvataggio degli eventi: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Metodo non valido. Solo POST è consentito."}, status=405)

#FEEDBACK STANZA da app flutter
@csrf_exempt
def api_feedback_stanza(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            room_id = data.get('room_id')
            voto = int(data.get('voto'))
            commento = data.get('commento', '')
            name = data.get('name', 'Mario')  # o da auth token in futuro
            surname = data.get('surname', 'Rossi')

            if not (1 <= voto <= 5):
                return JsonResponse({"error": "Voto fuori scala"}, status=400)

            room = Room.objects.get(id=room_id)
            utente, _ = User.objects.get_or_create(name=name, surname=surname)

            Feedback.objects.create(
                room=room,
                utente=utente,
                voto=voto,
                commento=commento
            )

            return JsonResponse({"message": "Feedback ricevuto!"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Metodo non valido. Usa POST."}, status=405)

#Invio notifica all'user
def send_user_notification(user, message):
    topic = f"nicodalla99/feeds/utente_{user.id}_notifiche"
    send_mqtt_command(topic, message)
    print(f"📲 Notifica inviata a {user.name} {user.surname}: {message}")
