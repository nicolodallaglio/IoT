# serializers.py
# Per esporre i dati del tuo modello, hai bisogno di creare dei serializer che convertiranno gli oggetti del modello in formato JSON.

from rest_framework import serializers
from .models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            'name',          # Nome della stanza
            'price',
            'co2',           # Livello di CO2
            'humidity',      # Umidità
            'latitudine',    # Latitudine della stanza
            'longitudine',   # Longitudine della stanza
            'light',         # Livello di luce
            'temperature',   # Temperatura
            'people',        # Numero di persone
            'probability',   # Probabilità della migliore stanza
            'room_size',     # Dimensione della stanza
            'sound',         # Rumore nella stanza
            'bestroom',      # Campo per indicare se è la migliore stanza
        ]

