from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import time
import re
import locale
from datetime import datetime
from geopy.geocoders import GoogleV3

# Imposta il locale su italiano per gestire i mesi in italiano
locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
# Funzione per convertire le date
def format_date(date_str):
    # Riconosciamo il formato "dal {data_inizio} al {data_fine}"
    date_range_pattern = r"dal (\d{1,2} [a-zA-Z]+ \d{4}) al (\d{1,2} [a-zA-Z]+ \d{4})"
    match = re.search(date_range_pattern, date_str)

    if match:
        date_start = datetime.strptime(match.group(1), "%d %B %Y")
        date_end = datetime.strptime(match.group(2), "%d %B %Y")
        return date_start, date_end
    return None, None


# Funzione per ottenere latitudine e longitudine usando geopy
ape = "AIzaSyCpdJrhynybDB1T7E1_7ajF6BziTVm8IFQ"
def get_coordinates(luogo):
    geolocator = GoogleV3(api_key=ape)

    try:
        location = geolocator.geocode(luogo, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None  # Se non trovato, ritorna None
    except Exception as e:
        print(f"Errore nel geocoding per {luogo}: {e}")
        return None, None  # Se c'è un errore, ritorna None


# Funzione per trasformare gli eventi
def process_events(events):
    processed_events = []

    for event in events:
        # Separiamo Data e Luogo
        data_match, luogo_match = event

        if data_match and luogo_match:
            # Formattiamo la data
            formatted_date_start, formatted_date_end = format_date(data_match)
            if formatted_date_start and formatted_date_end:
                # Escludiamo "Location varie" e altri luoghi non interessanti
                luogo = luogo_match
                if "Location varie" in luogo:
                    continue

                # Otteniamo le coordinate del luogo
                coordinates = get_coordinates(luogo)
                if coordinates:
                    lat, lon = coordinates
                    processed_events.append({
                        "data_inizio": formatted_date_start,
                        "data_fine": formatted_date_end,
                        "luogo": luogo,
                        "latitudine": lat,
                        "longitudine": lon
                    })

    return processed_events
# Impostare il WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Esegui in modalità invisibile (opzionale)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# URL della pagina eventi
url = "https://www.modenatoday.it/eventi/"

# Aprire la pagina
driver.get(url)
time.sleep(3)  # Attendere il caricamento

# Cliccare il pulsante "Accetta" dei cookie
try:
    # Trova il pulsante "Accetta" (può variare, quindi verifica il nome esatto)
    pulsante_cookie = driver.find_element(By.XPATH, "//button[contains(text(), 'Accetta')]")



    # Usa ActionChains nel caso ci siano problemi di sovrapposizione
    ActionChains(driver).move_to_element(pulsante_cookie).click().perform()
    time.sleep(1)
    ActionChains(driver).move_to_element(pulsante_cookie).click().perform()
    print("Cookie accettati con successo!")

    # Attendere un attimo per assicurarsi che il banner scompaia
    time.sleep(2)
except Exception as e:
    print("Nessun banner dei cookie trovato o errore:", e)

# Trova tutti gli <span> con la classe specificata
span_eventi = driver.find_elements(By.CLASS_NAME, "u-label-07.u-ml-medium.u-inline-block")

# Estrarre i testi dagli span
dati_testo = [span.text.strip() for span in span_eventi]

# Creare la lista di coppie [luogo, data]
eventi_organizzati = [[dati_testo[i], dati_testo[i + 1]] for i in range(0, len(dati_testo) - 1, 2)]

# Stampare il risultato
for evento in eventi_organizzati:
    evento[1] = evento[1] + ' Modena'
    print(f"Data: {evento[0]} | Luogo: {evento[1]}")

# Processa gli eventi
processed_events = process_events(eventi_organizzati)

# Mostra il risultato
for event in processed_events:
    print(f"Data Inizio: {event['data_inizio']},Data Fine: {event['data_fine']}, Luogo: {event['luogo']}, Latitudine: {event['latitudine']}, Longitudine: {event['longitudine']}")

# Chiudere il driver
driver.quit()
