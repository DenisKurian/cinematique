from django.db import models
from django.conf import settings

class JournalEntry(models.Model):
    STATUS_WATCHED = "watched"
    STATUS_WATCHLIST = "watchlist"
    STATUS_FAVORITE = "favorite"
    STATUS_CHOICES = [
        (STATUS_WATCHED, "Watched"),
        (STATUS_WATCHLIST, "Watchlist"),
        (STATUS_FAVORITE, "Favorite"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WATCHED)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-10
    review = models.TextField(blank=True)
    mood = models.CharField(max_length=32, blank=True)  # optional mood tag
    watched_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "movie")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} — {self.movie.title} ({self.status})"


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    entry = models.ForeignKey(JournalEntry, related_name="comments", on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user} on {self.entry}"

class Movie(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    overview = models.TextField(blank=True)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    release_date = models.CharField(max_length=20, blank=True)
    popularity = models.FloatField(default=0)

    def __str__(self):
        return self.title

