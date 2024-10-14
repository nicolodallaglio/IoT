# serializers.py
# Per esporre i dati del tuo modello, hai bisogno di creare dei serializer che convertiranno gli oggetti del modello in formato JSON.

from rest_framework import serializers
from .models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['name', 'price', 'rating', 'availability', 'sensor_data']

