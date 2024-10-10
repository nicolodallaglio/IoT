# serializers.py
# Per esporre i dati del tuo modello, hai bisogno di creare dei serializer che convertiranno gli oggetti del modello in formato JSON.

from rest_framework import serializers
from .models import Aula

class AulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aula
        fields = '__all__'  # Puoi specificare i campi che vuoi esporre, se necessario
