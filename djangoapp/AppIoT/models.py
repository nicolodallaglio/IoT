from django.db import models

class Room(models.Model):
    name = models.CharField(max_length=100)
    bridge = models.CharField(max_length=100, null=True, blank=True)  # Identificativo IoT
    type = models.CharField(max_length=100, default='generico')
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
    adafruit_position = models.IntegerField(null=True, blank=True)  # Posizione su Adafruit (1, 2, 3)

    
    adjacent_rooms = models.ManyToManyField("self", blank=True)  # Connessioni tra stanze

    def __str__(self):
        return self.name

    
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

class Event(models.Model):
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.location} ({self.start_date} - {self.end_date})"


