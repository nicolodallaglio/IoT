from django.db import models

class Room(models.Model):
    name = models.CharField(max_length=100)
    bridge = models.CharField(max_length=100, null=True, blank=True)  # Identificativo IoT
    type = models.CharField(max_length=100, null=True, blank=True)  # Tipo di stanza (studio, lavoro)
    price = models.FloatField(default=0.0)

    temperature = models.FloatField(default=0)
    humidity = models.FloatField(default=0)
    light = models.FloatField(default=0)
    co2 = models.FloatField(default=0)
    sound = models.FloatField(default=0)

    last_temperature = models.FloatField(null=True, blank=True)
    last_co2 = models.FloatField(null=True, blank=True)
    last_sound = models.FloatField(null=True, blank=True)
    last_light = models.FloatField(null=True, blank=True)
    last_humidity = models.FloatField(null=True, blank=True)

    latitudine = models.FloatField(default=0)
    longitudine = models.FloatField(default=0)
    room_size = models.FloatField(default=0)
    people = models.IntegerField(default=0)

    bestroom = models.IntegerField(default=0)
    probability = models.FloatField(default=0)

    online_status = models.BooleanField(default=False)  # Indica se la stanza è attiva nel cloud
    last_update = models.DateTimeField(auto_now=True)   # Ultima sincronizzazione
    adafruit_position = models.IntegerField(null=True, blank=True)  # Posizione su Adafruit (1, 2, 3)
    last_score_time = models.DateTimeField(null=True, blank=True)  # <-- nuovo campo

    last_prediction_time = models.DateTimeField(null=True, blank=True)
    
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
    latitudine = models.FloatField(null=True, blank=True)
    longitudine = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.location} ({self.start_date} - {self.end_date})"

class User(models.Model):
    name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255, default="Rossi")
    latitudine = models.FloatField(null=True, blank=True)
    longitudine = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} {self.surname}"


class UserEvent(models.Model):
    utente = models.ForeignKey('User', on_delete=models.CASCADE, related_name='eventi')
    titolo = models.CharField(max_length=255)
    luogo = models.CharField(max_length=255, null=True, blank=True)
    inizio = models.DateTimeField()
    fine = models.DateTimeField()
    latitudine = models.FloatField(null=True, blank=True)
    longitudine = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.titolo} - {self.inizio.strftime('%Y-%m-%d %H:%M')}"
    
class Feedback(models.Model):
    room = models.ForeignKey(Room, related_name='feedbacks', on_delete=models.CASCADE)
    utente = models.ForeignKey(User, on_delete=models.CASCADE)
    voto = models.IntegerField()  # da 1 a 5
    commento = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utente.name} su {self.room.name} → {self.voto}/5"

class PredictionHistory(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="predictions")
    timestamp = models.DateTimeField(auto_now_add=True)
    predicted_class = models.IntegerField()
    probability = models.FloatField()
    predicted_price = models.FloatField()
    source = models.CharField(max_length=20, default="arduino")  # oppure "manuale", "admin", ecc.

class SensorHistory(models.Model):
    room = models.ForeignKey(Room, related_name="sensor_history", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField()
    humidity = models.FloatField()
    co2 = models.FloatField()
    light = models.FloatField()
    sound = models.FloatField()
    people = models.IntegerField()

    def __str__(self):
        return f"{self.room.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"