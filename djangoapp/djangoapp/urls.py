from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib import admin
from AppIoT.views import RoomViewSet, predict_view, mostra_migliori_stanze, api_migliori_stanze, index, storico_predizioni
from AppIoT.views import receive_sensor_data, receive_location_data, api_eventi_utente, storico_sensori, api_feedback_stanza, admin_dashboard

# Router per le API
router = DefaultRouter()
router.register(r'stanze', RoomViewSet)  # Registra il ViewSet per il modello Room

# Combina gli URL generati dal router con quelli manuali
urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard-admin/", admin_dashboard, name="admin_dashboard"),
    path('predict/', predict_view, name='predict'),
    path('migliori-stanze/', mostra_migliori_stanze, name='migliori_stanze'),
    path('api/receive_sensor_data/', receive_sensor_data, name='receive_sensor_data'),
    path('api/migliori-stanze/', api_migliori_stanze, name='api_migliori_stanze'),
    path('api/location/', receive_location_data, name='receive_location_data'),
    path('api/eventi-utente/', api_eventi_utente, name='api_eventi_utente'),
    path('api/feedback/', api_feedback_stanza, name='api_feedback_stanza'),
    path('storico/<int:room_id>/', storico_predizioni, name='storico_predizioni'),
    path('storico-sensori/<int:room_id>/', storico_sensori, name='storico_sensori'),


    path('api/', include(router.urls)),  # Include il router con tutti gli endpoint delle API
    path('', index, name='main-page'),
]
