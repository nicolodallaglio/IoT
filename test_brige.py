import requests
import json

# URL dell'API Django che riceve i dati dei sensori
url = 'http://localhost:8000/api/receive_sensor_data/'  # Cambia l'URL con quello del tuo server

# Dati simulati dei sensori
data = {
    "sensor1": 23.5,
    "sensor2": 45.8
}

# Converte i dati in formato JSON
json_data = json.dumps(data)

# Intestazioni HTTP per specificare che si sta inviando JSON
headers = {
    'Content-Type': 'application/json',
}

# Invia una richiesta POST all'API con i dati dei sensori
response = requests.post(url, data=json_data, headers=headers)

# Verifica la risposta dal server
if response.status_code == 200:
    print("Dati inviati con successo!")
    print("Risposta del server:", response.json())
else:
    print(f"Errore nell'invio dei dati. Codice di risposta: {response.status_code}")
    print("Dettagli:", response.text)
