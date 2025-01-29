from django import forms
from .models import Match, Player

class MatchForm(forms.ModelForm):
    set_scores = forms.CharField(
        label="Set Scores",
        help_text="Enter set scores in the format '6-4 3-6 7-5'."
    )

    class Meta:
        model = Match
        fields = ['winner', 'loser', 'set_scores']

    def clean_set_scores(self):
        set_scores = self.cleaned_data['set_scores']
        try:
            # Convert set scores to a list of tuples
            sets = [tuple(map(int, s.split('-'))) for s in set_scores.split()]
            return sets
        except (ValueError, AttributeError):
            raise forms.ValidationError("Invalid set scores format. Use '6-4 3-6 7-5'.")