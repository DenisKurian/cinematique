from django.shortcuts import render
import os
import requests
from django.http import JsonResponse

def test_tmdb(request):
    api_key = os.getenv('TMDB_API_KEY')
    url = f"https://api.themoviedb.org/3/movie/550?api_key={api_key}"  # 550 = Fight Club
    response = requests.get(url)
    data = response.json()
    return JsonResponse(data)

# Create your views here.
