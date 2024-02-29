
from django.contrib import admin
from django.urls import path
from AppIoT.views import DatiSerialeView, Ranking, SaveDataView, create_my_model, index, home

urlpatterns = [
    path('home', home, name='home'),
    path("admin/", admin.site.urls),
    path('create_my_model/', create_my_model, name='create_my_model'),
    path('dati-seriale/', DatiSerialeView.as_view(), name='dati-seriale'),
    path('save-data/', SaveDataView.as_view(), name='save-data'),
    path('classifica/', Ranking.salva_classifica, name='salva_classifica'),
    path('', index, name='main-page')
]