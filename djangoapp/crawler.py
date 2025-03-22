import os
import django
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep

# Imposta l'ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoapp.settings')
django.setup()
from AppIoT.models import Event

def scrape_events():
    # Configura ChromeDriver con opzioni
    chrome_options = Options()
    # Rimuovi il parametro headless per testare visivamente
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-webgl")
    chrome_options.add_argument("--disable-webgl2")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors=yes")
    chrome_options.add_argument("--allow-insecure-localhost")
    chrome_options.add_argument("--disable-site-isolation-trials")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.50 Safari/537.36")

    # Specifica il percorso corretto del ChromeDriver
    service = Service(executable_path=r'C:\Users\Nicolò\Documents\IoT2025\chromedriver-win64\chromedriver-win64\chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)

    #url = "https://www.modenatoday.it/eventi/"
    url = "https://www.comune.modena.it/vivere-modena/eventi"
    print(f"🌐 Accedendo all'URL: {url}")
    driver.get(url)

    # Gestione del banner cookie
    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accetta')]"))
        )
        cookie_button.click()
        print("✅ Banner dei cookie accettato")
        sleep(2)
    except Exception as e:
        print(f"⚠️ Nessun banner cookie trovato o errore: {e}")

    # Scorri la pagina per forzare il caricamento degli eventi
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(2)

    # Stampa l'HTML della pagina per il debug
    print("🔎 HTML della pagina:")
    print(driver.page_source[:1000])

    # Attendi il caricamento degli eventi
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.c-article-card"))
        )
        print("✅ Eventi caricati correttamente")
    except Exception as e:
        print(f"❌ Errore durante il caricamento degli eventi: {e}")
        driver.quit()
        return

    # Trova tutti gli eventi
    try:
        events = driver.find_elements(By.CSS_SELECTOR, "div.c-article-card")
        print(f"🔍 Trovati {len(events)} eventi")

        for event in events:
            try:
                title_element = event.find_element(By.CSS_SELECTOR, "h3.c-article-card__title")
                title = title_element.text
                print(f"📝 Titolo: {title}")

                location_element = event.find_element(By.CSS_SELECTOR, "p.c-article-card__location")
                location = location_element.text
                print(f"📍 Luogo: {location}")

                date_element = event.find_element(By.CSS_SELECTOR, "span.c-article-card__date")
                date_text = date_element.text
                print(f"📅 Data: {date_text}")

                # Parsing della data
                try:
                    if "dal" in date_text and "al" in date_text:
                        date_parts = date_text.split(" al ")
                        start_date = datetime.strptime(date_parts[0].replace("dal ", "").strip() + " 2025", "%d %B %Y")
                        end_date = datetime.strptime(date_parts[1].strip() + " 2025", "%d %B %Y")
                    else:
                        start_date = datetime.strptime(date_text, "%d %B %Y")
                        end_date = start_date
                    print(f"📆 Data inizio: {start_date}, Data fine: {end_date}")
                except Exception as e:
                    print(f"❌ Errore nel parsing della data: {e}")
                    continue

                # Verifica se l'evento esiste già nel database
                if not Event.objects.filter(title=title, location=location, start_date=start_date).exists():
                    Event.objects.create(
                        title=title,
                        location=location,
                        start_date=start_date,
                        end_date=end_date
                    )
                    print(f"✅ Evento salvato: {title} a {location} dal {start_date} al {end_date}")
                else:
                    print(f"⚠️ Evento già presente: {title}")

            except Exception as e:
                print(f"❌ Errore durante il parsing dell'evento: {e}")
    except Exception as e:
        print(f"❌ Errore durante il recupero degli eventi: {e}")

    # Chiudi il driver
    driver.quit()
    print("🚪 Driver chiuso correttamente")

if __name__ == "__main__":
    scrape_events()
