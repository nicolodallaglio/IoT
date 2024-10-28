import requests
import json

# URL per ottenere il token CSRF (puoi rimuoverlo se non usi il token CSRF per l'API)
csrf_url = "http://127.0.0.1:8000/train/"  # URL che supporta il token CSRF, se necessario
predict_url = "http://127.0.0.1:8000/predict/"

# Inizia una sessione per mantenere i cookie
session = requests.Session()

# Ottieni il token CSRF dalla pagina (se necessario)
response = session.get(csrf_url)

# Estrai il token CSRF dai cookie (se necessario)
csrf_token = session.cookies.get('csrftoken')

if csrf_token:
    # Dati di input per la previsione
    data = [
        {
            "Temperature": 23.7,
            "Humidity": 26.272,
            "Light_scaled": 585.2,  # Usa lo stesso nome del dataset di addestramento
            "CO2_scaled": 749.2,    # Usa lo stesso nome del dataset di addestramento
            "Sound": 33.201601386017245,
            "Room_Size": 130,
            "People": 90,
        }
    ]

    # Converte i dati in formato JSON e invia la richiesta POST
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token  # Solo se il token CSRF è richiesto
    }
    response = session.post(predict_url, data=json.dumps(data), headers=headers)

    # Verifica la risposta del server
    if response.status_code == 200:
        print("Risultati delle previsioni:", response.json())
    else:
        print("Errore:", response.status_code, response.text)
else:
    print("Errore: CSRF token non trovato.")
