from django.db import models

class Room(models.Model):
    bridge = models.CharField(max_length=100, unique=True, null=True, blank=True)  # Identificativo IoT
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100, default='studio')
    price = models.FloatField(default=0)

    temperature = models.FloatField(default=0)
    humidity = models.FloatField(default=0)
    light = models.FloatField(default=0)
    co2 = models.FloatField(default=0)
    sound = models.FloatField(default=0)

    latitudine = models.FloatField(default=0)
    longitudine = models.FloatField(default=0)
    room_size = models.FloatField(default=0)
    people = models.IntegerField(default=0)

    bestroom = models.IntegerField(default=0)
    probability = models.FloatField(default=0)

    online_status = models.BooleanField(default=False)  # Indica se la stanza è attiva nel cloud
    last_update = models.DateTimeField(auto_now=True)   # Ultima sincronizzazione
    
    adjacent_rooms = models.ManyToManyField("self", blank=True)  # Connessioni tra stanze

    def __str__(self):
        return self.name

class InteractionLog(models.Model):
    room_from = models.ForeignKey(Room, related_name="interactions_from", on_delete=models.CASCADE)
    room_to = models.ForeignKey(Room, related_name="interactions_to", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    data_transferred = models.TextField()  # Informazioni scambiate tra le stanze

    def __str__(self):
        return f"Interaction from {self.room_from.name} to {self.room_to.name} at {self.timestamp}"
    
class Venditore(models.Model):
    nome = models.CharField(max_length=255)
    pubblica = models.BooleanField(default=False)  # Pubblico o privato

    def __str__(self):
        return self.nome

class Bridge(models.Model):
    nome = models.CharField(max_length=255)
    descrizione = models.TextField(null=True, blank=True)  # Dettagli aggiuntivi sul bridge

    def __str__(self):
        return self.nome


