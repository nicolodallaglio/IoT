# serializers.py
# Per esporre i dati del tuo modello, hai bisogno di creare dei serializer che convertiranno gli oggetti del modello in formato JSON.

from rest_framework import serializers
from .models import Room

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'  # Puoi specificare i campi che vuoi esporre, se necessario
