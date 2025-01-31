from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
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

# Helper function to generate floating point range
def frange(start, stop, step):
    while start <= stop:
        yield start
        start += step

class CustomSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    # Define USTA rating choices (3.00 to 6.00 in 0.25 increments)
    USTA_RATING_CHOICES = [(round(x, 2), f"{round(x, 2)}") for x in frange(3.00, 6.00, 0.25)]

    usta_rating = forms.ChoiceField(choices=USTA_RATING_CHOICES, required=True, label="USTA Rating")

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

