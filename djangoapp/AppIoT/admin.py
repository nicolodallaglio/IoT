from django.contrib import admin

# Register your models here.
from .models import MyModel
from .models import DatiSeriale
from .models import Aula
from .models import MainPage

admin.site.register(MyModel)
admin.site.register(DatiSeriale)
admin.site.register(Aula)
admin.site.register(MainPage)