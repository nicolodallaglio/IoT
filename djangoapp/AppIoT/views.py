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

from .models import DatiSeriale
from .models import MyModel
from .bridge import Bridge
from .models import MainPage
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

            # Usa la funzione predict_occupancy per fare previsioni
            probabilities, predicted_classes = predict_occupancy(input_data)

            # Cicla attraverso i dati e le previsioni, e salva ogni stanza nel database
            for i, row in input_data.iterrows():
                Room.objects.create(
                    name=f"Room {i + 1}",
                    temperature=row['Temperature'],
                    humidity=row['Humidity'],
                    light=row['Light'],
                    co2=row['CO2'],
                    humidity_ratio=row['HumidityRatio'],
                    occupancy=predicted_classes[i]  # Salva la previsione di occupazione
                )

            # Restituisci il risultato come risposta JSON
            response = {
                "probabilities": probabilities.tolist(),
                "predicted_classes": predicted_classes.tolist()
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


def create_my_model(request):
    # Creare un'istanza del modello con il valore impostato su True
    my_model_instance = MyModel(value=True)
    # Salvare l'istanza nel database
    my_model_instance.save()
    return HttpResponse("Istanza di MyModel creata con successo!")

class DatiSerialeView(ListView):
    model = DatiSeriale
    template_name = 'seriale.html'

class SaveDataView(View):
    def get(self, request, *args, **kwargs):
        bridge = Bridge()
        bridge.useData1()
        return JsonResponse({"message": "Dati salvati correttamente."})
    

# ---------------- INDEX -------------------------

def index(request):
    #mex di saluto
    greeting_message = "Benvenuto nel nostro progetto IoT 2024/2025"
    #url visualizzabili in main page
    other_urls = [
        {'url': '/create_my_model/', 'label': 'Crea il mio modello'},
        {'url': '/dati-seriale/', 'label': 'Dati seriali'},
        {'url': '/save-data/', 'label': 'Salva dati'},
        {'url': '/classifica/', 'label': 'Salva classifica'},
        {'url': '/train/', 'label': 'Traina il modello'},
        {'url': '/migliori-stanze/', 'label': 'Stanze'},
        # Aggiungi altri URL qui, se necessario
    ]
    #passiamo il mex al template e other urls
    return render(request,'index.html', {'greeting_message': greeting_message, 'other_urls': other_urls})



# ----------------- ALGORITMO --------------------
#algoritmo considererà vari criteri, come il prezzo, la disponibilità e il rating della stanza

def find_optimal_room(max_price, min_rating):
    rooms = Room.objects.filter(availability=True, price__lte=max_price, rating__gte=min_rating)

    if not rooms.exists():
        return None  # Nessuna stanza disponibile

    def score_room(room):
        price_weight = 0.4  # Peso del prezzo
        rating_weight = 0.5  # Peso del rating
        sensor_weight = 0.1  # Peso dei dati del sensore (ad es., temperatura, comfort)

        # Normalizza il prezzo, rating e dati del sensore
        price_score = (max_price - float(room.price)) / max_price  # Converti il prezzo in float
        rating_score = room.rating / 5.0
        sensor_score = room.sensor_data.get('comfort', 1) / 10.0  # supponendo un valore di comfort da 1 a 10

        # Calcola il punteggio finale
        return price_weight * price_score + rating_weight * rating_score + sensor_weight * sensor_score


    rooms_sorted = sorted(rooms, key=score_room, reverse=True)
    return rooms_sorted

def mostra_migliori_stanze(request):
    max_price = 1000  # Prezzo massimo predefinito
    min_rating = 3    # Punteggio minimo predefinito

    migliori_stanze = find_optimal_room(max_price, min_rating)
    
    return render(request, 'migliori_stanze.html', {'aule': migliori_stanze})


# --------- ARDUINO BRIDGE ------------

@csrf_exempt
def receive_sensor_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)  # Carica i dati JSON inviati
            
            temperature = data.get('temperature')
            humidity = data.get('humidity')
            light_scaled = data.get('light_scaled')
            co2_scaled = data.get('co2_scaled')
            sound = data.get('sound')
            room_size = data.get('room_size')
            people = data.get('people')

            # Stampa i dati ricevuti per verificare
            print(f"Received data: Temperature={temperature}, Humidity={humidity}, Light_scaled={light_scaled}, CO2_scaled={co2_scaled}, Sound={sound}, Room_Size={room_size}, People={people}")

            return JsonResponse({"status": "success", "data_received": data}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

# --------- API FLUTTER ------------

# Crea un ViewSet per gestire le operazioni CRUD: Il ViewSet viene utilizzato per gestire tutte le operazioni REST (GET, POST, PUT, DELETE).
# Questo RoomViewSet gestirà tutte le operazioni sulle stanze (aule) usando il RoomSerializer
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()  # Recupera tutte le stanze dal database
    serializer_class = RoomSerializer  # Usa il serializer per trasformare i dati


# Nuova vista API per Flutter che restituisce le migliori aule in formato JSON
def api_migliori_stanze(request):
    # Parametri predefiniti o puoi permettere all'app Flutter di passarli come GET params
    max_price = float(request.GET.get('max_price', 1000))
    min_rating = float(request.GET.get('min_rating', 3))

    # Trova le migliori stanze utilizzando la tua logica esistente
    migliori_stanze = Room.objects.filter(availability=True, price__lte=max_price, rating__gte=min_rating).order_by('-rating')

    if not migliori_stanze.exists():
        return JsonResponse({'error': 'No rooms available'}, status=404)

    # Prepara i dati in formato JSON
    rooms_data = []
    for room in migliori_stanze:
        rooms_data.append({
            'name': room.name,
            'posizione': room.posizione,
            'price': float(room.price),  # Converti Decimal in float
            'rating': room.rating,
            'availability': room.availability,
            'sensor_data': room.sensor_data  # JSON compatibile
        })

    # Restituisci la lista di aule come JSON
    return JsonResponse({'rooms': rooms_data})

