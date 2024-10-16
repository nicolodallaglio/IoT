import requests
import json

# URL per ottenere il token CSRF
csrf_url = "http://127.0.0.1:8000/train/"  # Usa una pagina che abbia il token CSRF
predict_url = "http://127.0.0.1:8000/predict/"

# Inizia una sessione per mantenere i cookie
session = requests.Session()

# Ottieni il token CSRF dalla pagina
response = session.get(csrf_url)

# Estrai il token CSRF dai cookie
csrf_token = session.cookies.get('csrftoken')

"""
    data è un dizionario (o una lista di dizionari) che contiene le caratteristiche (features) necessarie per fare una previsione con il 
    modello addestrato. Ogni chiave del dizionario rappresenta una caratteristica (colonna) che il modello si aspetta, 
    e il valore corrispondente rappresenta il valore specifico di quella caratteristica.

    Caratteristiche (features): Questi sono gli input utilizzati dal modello per fare previsioni. 
    Nel tuo caso, potrebbero essere variabili come la temperatura, l'umidità, ecc., che sono necessarie per prevedere se una stanza sarà occupata.
    Formato: I dati devono essere strutturati nello stesso modo del dataset utilizzato per addestrare il modello. 
    Questo significa che i nomi delle chiavi del dizionario (feature1, feature2, ecc.) 
    devono corrispondere esattamente ai nomi delle colonne del dataset che hai usato durante l'addestramento.
    
"""

if csrf_token:
    # Dati di input per la previsione
    data = [
        {
            "Temperature": 23.7,
            "Humidity": 26.272,
            "Light": 585.2,
            "CO2": 749.2,
            "HumidityRatio": 0.0047641630241641
        }
    ]

    # Converte i dati in formato JSON e invia la richiesta POST
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    response = session.post(predict_url, data=json.dumps(data), headers=headers)

    # Verifica la risposta del server
    if response.status_code == 200:
        print("Risultati delle previsioni:", response.json())
    else:
        print("Errore:", response.status_code, response.text)
else:
    print("Errore: CSRF token non trovato.")
