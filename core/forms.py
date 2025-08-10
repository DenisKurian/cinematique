from django import forms
from .models import JournalEntry, Comment

class JournalEntryForm(forms.ModelForm):
    watched_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    rating = forms.IntegerField(required=False, min_value=1, max_value=10)

    class Meta:
        model = JournalEntry
        fields = ["status", "rating", "watched_date", "mood", "review"]
        widgets = {
            "review": forms.Textarea(attrs={"rows":4, "placeholder":"Write your thoughts..."}),
            "mood": forms.TextInput(attrs={"placeholder":"e.g. nostalgic, excited, chill"}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={"rows":2, "placeholder":"Add a comment..."}),
        }
