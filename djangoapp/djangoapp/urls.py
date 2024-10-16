from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib import admin
from AppIoT.views import RoomViewSet, create_my_model, DatiSerialeView, SaveDataView, train_model_view, predict_view, mostra_migliori_stanze, api_migliori_stanze, index
from AppIoT.views import receive_sensor_data

# Router per le API
router = DefaultRouter()
router.register(r'stanze', RoomViewSet)  # Registra il ViewSet per il modello Room

# Combina gli URL generati dal router con quelli manuali
urlpatterns = [
    path("admin/", admin.site.urls),
    path('create_my_model/', create_my_model, name='create_my_model'),
    path('dati-seriale/', DatiSerialeView.as_view(), name='dati-seriale'),
    path('save-data/', SaveDataView.as_view(), name='save-data'),
    # path('classifica/', Ranking.salva_classifica, name='salva_classifica'),  # Da abilitare se necessario
    path('train/', train_model_view, name='train_model'),
    path('predict/', predict_view, name='predict'),
    path('migliori-stanze/', mostra_migliori_stanze, name='migliori_stanze'),
    path('api/receive_sensor_data/', receive_sensor_data, name='receive_sensor_data'),
    path('api/migliori-stanze/', api_migliori_stanze, name='api_migliori_stanze'),
    path('api/', include(router.urls)),  # Include il router con tutti gli endpoint delle API
    path('', index, name='main-page'),
]
