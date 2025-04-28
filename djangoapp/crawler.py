import os
import django

# Imposta l'ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoapp.settings')
django.setup()

from AppIoT.models import Event
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import time
import re
from datetime import datetime
from pytz import timezone
from django.utils.timezone import make_aware

import locale

# Imposta il locale su italiano
try:
    locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
except locale.Error:
    print("Errore: locale 'it_IT.UTF-8' non supportato. Provo con 'it_IT'.")
    try:
        locale.setlocale(locale.LC_TIME, 'it_IT')
    except locale.Error:
        print("Errore: locale italiano non disponibile.")

from geopy.geocoders import GoogleV3

# Key API Google
api_key = "AIzaSyCpdJrhynybDB1T7E1_7ajF6BziTVm8IFQ"


def get_coordinates(location):
    geolocator = GoogleV3(api_key=api_key)
    try:
        # Primo tentativo: utilizza il nome esatto
        geo_location = geolocator.geocode(location, timeout=10)
        if geo_location:
            print(f"Coordinate trovate per '{location}': {geo_location.latitude}, {geo_location.longitude}")
            return geo_location.latitude, geo_location.longitude
        
        # Secondo tentativo: aggiungi "Modena" alla fine del nome
        geo_location = geolocator.geocode(f"{location}, Modena", timeout=10)
        if geo_location:
            print(f"Coordinate trovate per '{location}, Modena': {geo_location.latitude}, {geo_location.longitude}")
            return geo_location.latitude, geo_location.longitude
        
        # Terzo tentativo: prova con un termine più generico
        geo_location = geolocator.geocode(f"{location}, Italia", timeout=10)
        if geo_location:
            print(f"Coordinate trovate per '{location}, Italia': {geo_location.latitude}, {geo_location.longitude}")
            return geo_location.latitude, geo_location.longitude
        
        print(f"Coordinate non trovate per '{location}'")
        return None, None
    except Exception as e:
        print(f"Errore nel geocoding per '{location}': {e}")
        return None, None


# Configurazione del WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--disable-web-security")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def format_date(date_str):
    rome_tz = timezone('Europe/Rome')

    # Pattern per data singola (es. "30 marzo 2025")
    single_date_pattern = r"(\d{1,2}) ([a-zA-Z]+) (\d{4})"
    match = re.search(single_date_pattern, date_str)
    if match:
        try:
            date = datetime.strptime(f"{match.group(1)} {match.group(2)} {match.group(3)}", "%d %B %Y")
            print(f"Data singola riconosciuta: {date}")
            return make_aware(date, rome_tz), make_aware(date, rome_tz)
        except Exception as e:
            print(f"Errore nel parsing della data singola: {e} - Data: {match.group(0)}")

    # Pattern per data singola senza anno (es. "30 marzo")
    single_date_no_year_pattern = r"(\d{1,2}) ([a-zA-Z]+)"
    match = re.search(single_date_no_year_pattern, date_str)
    if match:
        try:
            current_year = datetime.now().year
            date = datetime.strptime(f"{match.group(1)} {match.group(2)} {current_year}", "%d %B %Y")
            print(f"Data singola senza anno riconosciuta: {date}")
            return make_aware(date, rome_tz), make_aware(date, rome_tz)
        except Exception as e:
            print(f"Errore nel parsing della data singola senza anno: {e} - Data: {match.group(0)}")

    # Pattern per intervallo con anni (es. "dal 2 ottobre 2024 al 28 maggio 2025")
    range_date_pattern = r"dal (\d{1,2} [a-zA-Z]+ \d{4}) al (\d{1,2} [a-zA-Z]+ \d{4})"
    match = re.search(range_date_pattern, date_str)
    if match:
        try:
            start_date = datetime.strptime(match.group(1), "%d %B %Y")
            end_date = datetime.strptime(match.group(2), "%d %B %Y")
            print(f"Intervallo con anni riconosciuto: {start_date} - {end_date}")
            return make_aware(start_date, rome_tz), make_aware(end_date, rome_tz)
        except Exception as e:
            print(f"Errore nel parsing dell'intervallo data con anno: {e} - Data: {match.group(0)}")

    # Pattern per intervallo breve (es. "dal 5 al 29 marzo 2025")
    short_range_date_pattern = r"dal (\d{1,2}) al (\d{1,2}) ([a-zA-Z]+) (\d{4})"
    match = re.search(short_range_date_pattern, date_str)
    if match:
        try:
            start_date = datetime.strptime(f"{match.group(1)} {match.group(3)} {match.group(4)}", "%d %B %Y")
            end_date = datetime.strptime(f"{match.group(2)} {match.group(3)} {match.group(4)}", "%d %B %Y")
            print(f"Intervallo breve riconosciuto: {start_date} - {end_date}")
            return make_aware(start_date, rome_tz), make_aware(end_date, rome_tz)
        except Exception as e:
            print(f"Errore nel parsing dell'intervallo breve: {e} - Data: {match.group(0)}")

    # Pattern per intervallo misto (es. "dal 1 marzo al 5 maggio 2025")
    mixed_range_date_pattern = r"dal (\d{1,2} [a-zA-Z]+) al (\d{1,2} [a-zA-Z]+) (\d{4})"
    match = re.search(mixed_range_date_pattern, date_str)
    if match:
        try:
            start_date = datetime.strptime(f"{match.group(1)} {match.group(3)}", "%d %B %Y")
            end_date = datetime.strptime(f"{match.group(2)} {match.group(3)}", "%d %B %Y")
            print(f"Intervallo misto riconosciuto: {start_date} - {end_date}")
            return make_aware(start_date, rome_tz), make_aware(end_date, rome_tz)
        except Exception as e:
            print(f"Errore nel parsing dell'intervallo misto: {e} - Data: {match.group(0)}")

    print(f"Formato data non riconosciuto: {date_str}")
    return None, None


# Funzione per salvare l'evento nel database
def save_event(title, location, dates):
    try:
        if dates is None or dates[0] is None or dates[1] is None:
            print(f"Evento '{title}' non salvato a causa di date non valide.")
            return
        
        start_date, end_date = dates

        # Otteniamo le coordinate del luogo
        lat, lon = get_coordinates(location)

        # Se sono None, assegna coordinate fisse
        if lat is None or lon is None:
            lat = 44.62902432803542
            lon = 10.94885144130329
            print(f"Coordinate non trovate, inserite coordinate fisse per '{location}'")

        # Verifica se le date sono effettivamente oggetti datetime
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            print(f"Errore: le date non sono nel formato datetime - Start: {start_date}, End: {end_date}")
            return

        # Usa update_or_create per aggiornare o creare l'evento
        event_instance, created = Event.objects.update_or_create(
            title=title,
            location=location,
            start_date=start_date,
            end_date=end_date,
            defaults={
                'latitudine': lat,
                'longitudine': lon
            }
        )

        # Se l'evento esiste già e ha ancora latitudine o longitudine NULL, forzare l'aggiornamento
        if not created and (event_instance.latitudine is None or event_instance.longitudine is None):
            event_instance.latitudine = lat
            event_instance.longitudine = lon
            event_instance.save()
            print(f"Aggiornato (forzato): {event_instance}")
        else:
            print(f"Creato: {event_instance}")

    except Exception as e:
        print(f"Errore nel salvataggio dell'evento: {e}")


# Crawler per ModenaToday
def crawl_modenatoday():
    url = "https://www.modenatoday.it/eventi/"
    driver.get(url)
    time.sleep(3)

    try:
        pulsante_cookie = driver.find_element(By.XPATH, "//button[contains(text(), 'Accetta')]")
        ActionChains(driver).move_to_element(pulsante_cookie).click().perform()
        time.sleep(2)
    except Exception:
        pass

    eventi = driver.find_elements(By.CLASS_NAME, "u-label-07.u-ml-medium.u-inline-block")
    dati_testo = [event.text.strip() for event in eventi]

    eventi_organizzati = [[dati_testo[i], dati_testo[i + 1]] for i in range(0, len(dati_testo) - 1, 2)]
    for evento in eventi_organizzati:
        title = f"Evento a {evento[1]}"
        location = evento[1]
        dates = format_date(evento[0])  # Otteniamo una coppia (start_date, end_date)
        save_event(title, location, dates)

# Crawler per Comune di Modena
def crawl_comune_modena():
    url = "https://www.comune.modena.it/vivere-modena/eventi"
    driver.get(url)
    time.sleep(3)

    eventi = driver.find_elements(By.CSS_SELECTOR, ".evento .titolo")
    date_elements = driver.find_elements(By.CSS_SELECTOR, ".evento .data")

    for title, date in zip(eventi, date_elements):
        event_title = title.text.strip()
        event_date = format_date(date.text.strip())
        save_event(event_title, "Modena", event_date)

# Crawler per TicketOne
def crawl_ticketone():
    url = "https://www.ticketone.it/cityd/modena-1151/"
    driver.get(url)
    time.sleep(3)

    eventi = driver.find_elements(By.CSS_SELECTOR, ".event-title")
    date_elements = driver.find_elements(By.CSS_SELECTOR, ".event-date")

    for title, date in zip(eventi, date_elements):
        event_title = title.text.strip()
        event_date = format_date(date.text.strip())
        save_event(event_title, "Modena", event_date)

# Funzione principale
def main():
    crawl_modenatoday()
    crawl_comune_modena()
    crawl_ticketone()
    driver.quit()

if __name__ == "__main__":
    main()
