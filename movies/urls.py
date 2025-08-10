from django.urls import path
from .views import test_tmdb

urlpatterns = [
    path('test-tmdb/', test_tmdb, name='test_tmdb'),
]
