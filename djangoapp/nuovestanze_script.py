import requests
import json

url = "http://127.0.0.1:8000/api/receive_sensor_data/"

data = {
    "bridge_name": "bridge_piano2",
    "temperature": 29.5,
    "humidity": 90,
    "lightSensor": 300,
    "Quality": 400,
    "sound": 80,
    "people": 5,
    "room_size": 40,
    "latitudine": 44.62902432803542,
    "longitudine": 10.94885144130329,
    "price": 30,
    "type": "studio"
}

response = requests.post(url, json=data)

print("Status code:", response.status_code)
try:
    print("Response JSON:", response.json())
except json.JSONDecodeError:
    print("Errore: la risposta non è in formato JSON")
    print("Risposta:", response.text)
