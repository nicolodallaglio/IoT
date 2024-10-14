
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from AppIoT.views import DatiSerialeView, SaveDataView, create_my_model, index, train_model_view, predict_view, RoomViewSet, mostra_migliori_stanze


router = DefaultRouter()
router.register(r'aule', RoomViewSet)


urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include(router.urls)),
    path('create_my_model/', create_my_model, name='create_my_model'),
    path('dati-seriale/', DatiSerialeView.as_view(), name='dati-seriale'),
    path('save-data/', SaveDataView.as_view(), name='save-data'),
    #path('classifica/', Ranking.salva_classifica, name='salva_classifica'),
    path('train/', train_model_view, name='train_model'),
    path('predict/', predict_view, name='predict'),
    path('migliori-stanze/', mostra_migliori_stanze, name='migliori_stanze'),
    path('', index, name='main-page')
]