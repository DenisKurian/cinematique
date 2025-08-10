import requests
from django.core.management.base import BaseCommand
from core.models import Movie  # adjust if needed
from django.conf import settings


class Command(BaseCommand):
    help = "Refresh movies from TMDb API"

    def handle(self, *args, **kwargs):
        api_key = settings.TMDB_API_KEY
        url = "https://api.themoviedb.org/3/movie/popular"
        total_added = 0

        for page in range(1, 6):  # Get pages 1 to 5 (about 100 movies)
            params = {
                "api_key": api_key,
                "language": "en-US",
                "page": page
            }

            try:
                response = requests.get(url, params=params, timeout=5)
                response.raise_for_status()
                data = response.json()

                for movie in data.get("results", []):
                    obj, created = Movie.objects.update_or_create(
                        tmdb_id=movie["id"],
                        defaults={
                            "title": movie["title"],
                            "overview": movie.get("overview", ""),
                            "release_date": movie.get("release_date"),
                            "poster_path": movie.get("poster_path", ""),
                        }
                    )
                    if created:
                        total_added += 1

                self.stdout.write(self.style.SUCCESS(f"Page {page} done."))

            except requests.RequestException as e:
                self.stderr.write(self.style.ERROR(f"Error fetching page {page}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Added {total_added} new movies."))
