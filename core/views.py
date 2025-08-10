import os
import time
import requests

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.core.paginator import Paginator
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .models import Movie, JournalEntry, Comment
from .forms import JournalEntryForm, CommentForm


def signup_view(request):
    """
    Simple signup view that creates a user and logs them in.
    Renders registration/signup.html (you'll create this template).
    """
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)  # log the user in right away
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


def fetch_tmdb_data(url, params=None, retries=3, delay=2):
    """
    Safe TMDb fetcher. Handles paged "results" responses and single-movie
    responses. Coerces None -> "" for fields that must not be NULL in DB.
    Returns parsed JSON or None on total failure.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=6)
            response.raise_for_status()
            data = response.json()

            # If this is a search/multi-page response with "results"
            if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
                for movie in data["results"]:
                    tmdb_id = movie.get("id")
                    title = movie.get("title") or movie.get("name") or ""
                    overview = movie.get("overview") or ""
                    poster_path = movie.get("poster_path") or ""      # avoid None
                    release_date = movie.get("release_date") or ""
                    popularity = movie.get("popularity") or 0

                    try:
                        Movie.objects.update_or_create(
                            tmdb_id=tmdb_id,
                            defaults={
                                "title": title,
                                "overview": overview,
                                "poster_path": poster_path,
                                "release_date": release_date,
                                "popularity": popularity,
                            }
                        )
                    except Exception as e:
                        # log and continue
                        print(f"Skipping movie id={tmdb_id} due to DB error: {e}")

            # For single-movie endpoints (no "results"), return data to caller.
            return data

        except requests.exceptions.RequestException as e:
            print(f"TMDb API error (attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return None


class HomeView(View):
    def get(self, request):
        query = request.GET.get("q")
        movies_qs = Movie.objects.all().order_by("-popularity")

        if query:
            movies_qs = movies_qs.filter(title__icontains=query)

        paginator = Paginator(movies_qs, 20)  # 20 movies per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Precompute the "smart" page range for pagination display
        current_page = page_obj.number
        total_pages = page_obj.paginator.num_pages
        page_range = [
            num for num in page_obj.paginator.page_range
            if num <= 2
            or num > total_pages - 2
            or (num >= current_page - 2 and num <= current_page + 2)
        ]

        return render(request, "core/home.html", {
            "page_obj": page_obj,
            "page_range": page_range,
        })


class SearchView(View):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        movies = Movie.objects.none()
        page_obj = None
        page_range = []

        if query:
            # Always call TMDb (to fill DB) then query DB for consistent results
            tmdb_url = "https://api.themoviedb.org/3/search/movie"
            params = {
                "api_key": settings.TMDB_API_KEY,
                "query": query,
                "language": "en-US"
            }
            data = fetch_tmdb_data(tmdb_url, params=params)

            if data and "results" in data:
                for m in data["results"]:
                    # safe coercion for fields which might be None
                    Movie.objects.update_or_create(
                        tmdb_id=m.get("id"),
                        defaults={
                            "title": m.get("title") or "",
                            "overview": m.get("overview") or "",
                            "poster_path": m.get("poster_path") or "",
                            "release_date": m.get("release_date") or "",
                            "popularity": m.get("popularity") or 0,
                        }
                    )

            # Now query DB for combined/consistent results
            movies = Movie.objects.filter(title__icontains=query).order_by("-popularity")

            # Pagination
            paginator = Paginator(movies, 20)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

            current_page = page_obj.number
            total_pages = paginator.num_pages
            page_range = [
                num for num in paginator.page_range
                if num <= 2
                or num > total_pages - 2
                or (num >= current_page - 2 and num <= current_page + 2)
            ]

        return render(request, "core/search_results.html", {
            "query": query,
            "page_obj": page_obj,
            "page_range": page_range,
        })


class MovieDetailView(View):
    def get(self, request, tmdb_id):
        # get local movie (or 404)
        movie = get_object_or_404(Movie, tmdb_id=tmdb_id)

        # Ensure DB has reasonable base info (this keeps existing behaviour)
        if not movie.overview or not movie.poster_path:
            tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
            params = {"api_key": settings.TMDB_API_KEY, "language": "en-US"}
            data = fetch_tmdb_data(tmdb_url, params=params)
            if data:
                Movie.objects.update_or_create(
                    tmdb_id=data.get("id"),
                    defaults={
                        "title": data.get("title") or movie.title or "",
                        "overview": data.get("overview") or movie.overview or "",
                        "poster_path": data.get("poster_path") or movie.poster_path or "",
                        "release_date": data.get("release_date") or movie.release_date or "",
                        "popularity": data.get("popularity") or movie.popularity or 0,
                    }
                )
                movie = Movie.objects.get(tmdb_id=tmdb_id)

        # --- Extra TMDb fetch for genres/runtime/videos (no DB writes) ---
        extra_genres = []
        runtime = None
        runtime_display = None
        trailer_embed = None
        cast = []

        # fetch full movie details + videos in one call
        tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        params = {"api_key": settings.TMDB_API_KEY, "language": "en-US", "append_to_response": "videos,credits"}
        data = fetch_tmdb_data(tmdb_url, params=params)

        if data:
            # genres (list of names)
            genres = data.get("genres") or []
            extra_genres = [g.get("name") for g in genres if g.get("name")]

            # runtime in minutes + human-readable
            runtime = data.get("runtime")
            if isinstance(runtime, int) and runtime > 0:
                hours = runtime // 60
                mins = runtime % 60
                runtime_display = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            # videos -> find a YouTube trailer
            videos = data.get("videos", {}).get("results", []) or []
            trailer_key = None
            # prefer official trailers, then any YouTube trailer
            for v in videos:
                if v.get("site") == "YouTube" and v.get("type") == "Trailer" and v.get("official"):
                    trailer_key = v.get("key")
                    break
            if not trailer_key:
                for v in videos:
                    if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                        trailer_key = v.get("key")
                        break
            if trailer_key:
                trailer_embed = f"https://www.youtube.com/embed/{trailer_key}"

        # Get current user's entry and compute stars_to_fill
         # credits -> top-billed cast (take first N, defensive)
            raw_cast = (data.get("credits") or {}).get("cast", []) or []
            # pick top 8 (or fewer) cast members
            top_cast = raw_cast[:8]
            for member in top_cast:
                cast.append({
                    "name": member.get("name") or "",
                    "character": member.get("character") or "",
                    "profile_path": member.get("profile_path") or "",
                })
        entry = None
        stars_to_fill = 0
        if request.user.is_authenticated:
            entry = JournalEntry.objects.filter(user=request.user, movie=movie).first()
            rating = entry.rating if entry and entry.rating else 0
            try:
                rating_int = int(rating)
            except (TypeError, ValueError):
                rating_int = 0
            stars_to_fill = (rating_int + 1) // 2 if rating_int > 0 else 0

        context = {
            "movie": movie,
            "entry": entry,
            "stars_to_fill": stars_to_fill,
            "genres": extra_genres,
            "runtime": runtime,
            "runtime_display": runtime_display,
            "trailer_embed": trailer_embed,
            "cast": cast,
        }

        return render(request, "core/movie_detail.html", context)




# -------------------------
# Journal views (additive)
# -------------------------
@method_decorator(login_required, name="dispatch")
class AddToJournalView(View):
    def post(self, request, tmdb_id):
        movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
        if not movie:
            tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
            params = {"api_key": settings.TMDB_API_KEY, "language": "en-US"}
            data = fetch_tmdb_data(tmdb_url, params=params)
            if data:
                movie, _ = Movie.objects.update_or_create(
                    tmdb_id=data.get("id"),
                    defaults={
                        "title": data.get("title") or "",
                        "overview": data.get("overview") or "",
                        "poster_path": data.get("poster_path") or "",
                        "release_date": data.get("release_date") or "",
                        "popularity": data.get("popularity") or 0,
                    },
                )

        if not movie:
            return redirect("home")

        entry, created = JournalEntry.objects.get_or_create(user=request.user, movie=movie)
        return redirect("edit_journal_entry", pk=entry.pk)


@method_decorator(login_required, name="dispatch")
class EditJournalEntryView(View):
    def get(self, request, pk):
        entry = JournalEntry.objects.get(pk=pk, user=request.user)
        form = JournalEntryForm(instance=entry)
        comment_form = CommentForm()
        return render(request, "core/journal_entry_form.html", {"form": form, "entry": entry, "comment_form": comment_form})

    def post(self, request, pk):
        entry = JournalEntry.objects.get(pk=pk, user=request.user)
        form = JournalEntryForm(request.POST, instance=entry)
        comment_form = CommentForm(request.POST)
        if "save_entry" in request.POST and form.is_valid():
            form.save()
            return redirect("my_journal")
        if "add_comment" in request.POST and comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.entry = entry
            comment.save()
            return redirect("edit_journal_entry", pk=entry.pk)
        return render(request, "core/journal_entry_form.html", {"form": form, "entry": entry, "comment_form": comment_form})


@method_decorator(login_required, name="dispatch")
class MyJournalView(View):
    def get(self, request):
        qs = JournalEntry.objects.filter(user=request.user).select_related("movie")
        paginator = Paginator(qs, 20)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        return render(request, "core/my_journal.html", {"page_obj": page_obj})


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

@method_decorator(login_required, name="dispatch")
class UpdateStatusView(View):
    """
    POST: set status to one of: watched, watchlist, favorite
    Expects form field 'status'.
    """
    def post(self, request, tmdb_id):
        status = request.POST.get("status")
        if status not in ("watched", "watchlist", "favorite"):
            return JsonResponse({"ok": False, "error": "invalid status"}, status=400)

        movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
        if not movie:
            tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
            params = {"api_key": settings.TMDB_API_KEY, "language": "en-US"}
            data = fetch_tmdb_data(tmdb_url, params=params)
            if data:
                movie, _ = Movie.objects.update_or_create(
                    tmdb_id=data.get("id"),
                    defaults={
                        "title": data.get("title") or "",
                        "overview": data.get("overview") or "",
                        "poster_path": data.get("poster_path") or "",
                        "release_date": data.get("release_date") or "",
                        "popularity": data.get("popularity") or 0,
                    },
                )
        if not movie:
            return JsonResponse({"ok": False, "error": "movie not found"}, status=404)

        entry, _ = JournalEntry.objects.get_or_create(user=request.user, movie=movie)
        entry.status = status
        entry.save()
        return JsonResponse({"ok": True, "status": entry.status})


@method_decorator(login_required, name="dispatch")
class RateView(View):
    """
    POST: set rating (1-10). Expects form field 'rating'.
    """
    def post(self, request, tmdb_id):
        try:
            rating = int(request.POST.get("rating", ""))
        except (ValueError, TypeError):
            return JsonResponse({"ok": False, "error": "invalid rating"}, status=400)

        if rating < 1 or rating > 10:
            return JsonResponse({"ok": False, "error": "rating out of range"}, status=400)

        movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
        if not movie:
            tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
            params = {"api_key": settings.TMDB_API_KEY, "language": "en-US"}
            data = fetch_tmdb_data(tmdb_url, params=params)
            if data:
                movie, _ = Movie.objects.update_or_create(
                    tmdb_id=data.get("id"),
                    defaults={
                        "title": data.get("title") or "",
                        "overview": data.get("overview") or "",
                        "poster_path": data.get("poster_path") or "",
                        "release_date": data.get("release_date") or "",
                        "popularity": data.get("popularity") or 0,
                    },
                )
        if not movie:
            return JsonResponse({"ok": False, "error": "movie not found"}, status=404)

        entry, _ = JournalEntry.objects.get_or_create(user=request.user, movie=movie)
        entry.rating = rating
        entry.save()
        return JsonResponse({"ok": True, "rating": entry.rating})
