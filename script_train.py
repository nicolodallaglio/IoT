import requests

# URL dell'endpoint corretto
url = "http://127.0.0.1:8000/train/"

# Ottieni il token CSRF dalla pagina
session = requests.Session()
response = session.get(url)  # Ottieni il cookie CSRF dalla risposta

# Verifica che il token CSRF sia presente nei cookie
csrf_token = session.cookies.get('csrftoken')

if csrf_token:
    # Apri il file CSV e invialo come parte della richiesta POST
    with open('C:/Users/dalla/Desktop/Project/Dataset/Occupancy.csv', 'rb') as file:
        files = {'file': file}
        headers = {
            'X-CSRFToken': csrf_token
        }
        response = session.post(url, files=files, headers=headers)

        # Verifica la risposta del server
        if response.status_code == 200:
            print("Risposta ricevuta:", response.json())
        else:
            print("Errore:", response.status_code, response.text)
else:
    print("Errore: CSRF token non trovato.")

