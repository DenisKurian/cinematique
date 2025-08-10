from django.urls import path, include
from .views import (
    HomeView, SearchView, MovieDetailView,
    AddToJournalView, EditJournalEntryView, MyJournalView,
    signup_view
)
from .views import UpdateStatusView, RateView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("search/", SearchView.as_view(), name="search"),
    path("movie/<int:tmdb_id>/", MovieDetailView.as_view(), name="movie_detail"),

    # Journal
    path("journal/add/<int:tmdb_id>/", AddToJournalView.as_view(), name="add_to_journal"),
    path("journal/edit/<int:pk>/", EditJournalEntryView.as_view(), name="edit_journal_entry"),
    path("journal/my/", MyJournalView.as_view(), name="my_journal"),

    # Signup (local simple signup view)
    path("signup/", signup_view, name="signup"),

    # Auth routes (login/logout/password) under /accounts/
    path("accounts/", include("django.contrib.auth.urls")),

    path("journal/status/<int:tmdb_id>/", UpdateStatusView.as_view(), name="journal_update_status"),
    path("journal/rate/<int:tmdb_id>/", RateView.as_view(), name="journal_rate"),
]

