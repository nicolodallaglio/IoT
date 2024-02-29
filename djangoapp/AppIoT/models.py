from django.db import models

# Create your models here.
class MainPage(models.Model):
    main = models.TextField()
    
class MyModel(models.Model):
    value = models.BooleanField(default=False)

class DatiSeriale(models.Model):
    dati = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class SaveData(models.Model):
    dati = models.CharField(max_length=255)

    def __str__(self):
        return self.dati
    

#un modello per rappresentare le aule nel tuo database. 
#L’opzione ordering nella classe Meta assicura che quando recuperi le aule dal database, saranno ordinate in base al punteggio in ordine decrescente.
class Aula(models.Model):
    nome = models.CharField(max_length=100)
    punteggio = models.IntegerField()
    
    class Meta:
        ordering = ['-punteggio']

    def __str__(self):
        return self.nome