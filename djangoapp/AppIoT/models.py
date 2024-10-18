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
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    posizione = models.CharField(max_length=255, default=True)
    rating = models.FloatField(default=0.0)  # Punteggio da 1 a 5
    availability = models.BooleanField(default=True)
    sensor_data = models.JSONField(default=dict)  # Può contenere i dati dei sensori come temperatura, umidità, comfort, ecc.

    def __str__(self):
        return self.name

class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    user = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.room.name} - {self.user}"
