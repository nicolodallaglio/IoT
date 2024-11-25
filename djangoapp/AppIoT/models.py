from django.db import models

class Venditore(models.Model):
    nome = models.CharField(max_length=255)
    pubblica = models.BooleanField(default=False)  # Pubblico o privato
    
    def __str__(self):
        return self.nome

class Bridge(models.Model):
    venditore = models.ForeignKey(Venditore, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    descrizione = models.TextField(null=True, blank=True)  # Dettagli aggiuntivi sul bridge

    def __str__(self):
        return f"{self.nome} - {self.venditore.nome}"

class Utente(models.Model):
    nome = models.CharField(max_length=255)
    cognome = models.CharField(max_length=255)
    nascita = models.DateField()
    carta_di_pagamento = models.CharField(max_length=16)
    stato = models.CharField(max_length=50, choices=[('studente', 'Studente'), ('relatore', 'Relatore di Conferenze')])

class Calendario(models.Model):
    utente = models.ForeignKey(Utente, on_delete=models.CASCADE)
    evento = models.CharField(max_length=255)
    data_evento = models.DateTimeField()


#definisci i modelli per rappresentare le stanze e le relative informazioni (ranking, prezzo, ecc.)
class Room(models.Model):
    bridge = models.CharField(max_length=100, unique=True, null=True, blank=True)  # Campo per identificare il bridge
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
    

    def __str__(self):
        return self.name


class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    user = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.room.name} - {self.user}"
