from django.shortcuts import render

from django.http import HttpResponse
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView
from django.shortcuts import render

from .models import DatiSeriale
from .models import MyModel
from .bridge import Bridge
from .models import Aula
from .models import MainPage

# Create your views here.

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

class Ranking(View):
    def salva_classifica(request):
        # Dizionario di aule con punteggi
        aule = {
            'Aula1': 85,
            'Aula2': 90,
            'Aula3': 1000,
            'Aula4': 92,
            'Aula5': 88
        }

        # Salva le aule nel database
        for nome, punteggio in aule.items():
            aula, created = Aula.objects.get_or_create(nome=nome, defaults={'punteggio': punteggio})
            if not created:
                aula.punteggio = punteggio
                aula.save()

        return HttpResponse('Classifica salvata con successo!')
    
def index(request):
    #mex di saluto
    greeting_message = "Benvenuto nel nostro progetto IoT 2024"
    #url visualizzabili in main page
    other_urls = [
        {'url': '/create_my_model/', 'label': 'Crea il mio modello'},
        {'url': '/dati-seriale/', 'label': 'Dati seriali'},
        {'url': '/save-data/', 'label': 'Salva dati'},
        {'url': '/classifica/', 'label': 'Salva classifica'},
        # Aggiungi altri URL qui, se necessario
    ]
    #passiamo il mex al template e other urls
    return render(request,'index.html', {'greeting_message': greeting_message, 'other_urls': other_urls})

def home(request):
    # Qui puoi inserire il codice per ottenere eventuali dati da passare al template
    context = {
        'message': 'Benvenuto sulla homepage del tuo sito azure!'
    }
    return render(request, 'home.html', context)