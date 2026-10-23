from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health),
    path("geocode/", views.geocode),
    path("routes/analyze/", views.analyze),
    path("heatmap/", views.heatmap),
]
