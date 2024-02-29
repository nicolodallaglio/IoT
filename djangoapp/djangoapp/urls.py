"""
URL configuration for djangoapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from AppIoT.views import DatiSerialeView, Ranking, SaveDataView, create_my_model, index

urlpatterns = [
    path("admin/", admin.site.urls),
    path('create_my_model/', create_my_model, name='create_my_model'),
    path('dati-seriale/', DatiSerialeView.as_view(), name='dati-seriale'),
    path('save-data/', SaveDataView.as_view(), name='save-data'),
    path('classifica/', Ranking.salva_classifica, name='salva_classifica'),
    path('', index, name='main-page')
]