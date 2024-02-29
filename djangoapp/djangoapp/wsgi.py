"""
WSGI config for djangoapp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""
"""
WSGI config for ServerPython project.
It exposes the WSGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import requests
from django.core.wsgi import get_wsgi_application
from AppIoT.models import MyModel

#sceglie tra deployment o in localhost
settings_module= 'djangoapp.deployment' if 'WEBSITE_HOSTNAME' in os.environ else 'djangoapp.settings'


os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()

"""
def send_to_adafruit_io():
    # Imposta le tue credenziali Adafruit IO qui
    ADAFRUIT_IO_USERNAME = 'nicodalla99'
    ADAFRUIT_IO_KEY = 'aio_FXcQ35cqPK9roCVffNMoqjDKMBT8'

    url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds/serverdiprova/data'
    headers = {'X-AIO-Key': ADAFRUIT_IO_KEY}
    data = {'value': 1}

    response = requests.post(url, headers=headers, json=data)
    
    #Creare un'istanza del modello con il valore impostato su True
    my_model_instance = MyModel(value=True)
    # Salvare l'istanza nel database
    my_model_instance.save()

    if response.status_code == 200:
        print('Dato inviato con successo a Adafruit IO.')
    else:
        print(f'Errore durante l\'invio del dato a Adafruit IO: {response.content}')

# Questa funzione viene chiamata quando il server Django si avvia
send_to_adafruit_io()
"""