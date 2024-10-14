from django.contrib import admin

# Register your models here.
from .models import MyModel
from .models import DatiSeriale
from .models import MainPage
from .models import Venditore, Bridge, Room

admin.site.register(MyModel)
admin.site.register(DatiSeriale)
admin.site.register(MainPage)

admin.site.register(Venditore)
admin.site.register(Bridge)
admin.site.register(Room)
