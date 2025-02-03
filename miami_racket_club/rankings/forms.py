from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Match, Player
from django.forms import DateInput
import re
from django.core.exceptions import ValidationError

class MatchForm(forms.ModelForm):
    winner_games_set1 = forms.IntegerField(label='Set 1 Games (Winner)', min_value=0, max_value=7, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    loser_games_set1 = forms.IntegerField(label='Set 1 Games (Loser)', min_value=0, max_value=7, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    winner_games_set2 = forms.IntegerField(label='Set 2 Games (Winner)', min_value=0, max_value=7, required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    loser_games_set2 = forms.IntegerField(label='Set 2 Games (Loser)', min_value=0, max_value=7, required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    winner_games_set3 = forms.IntegerField(label='Set 3 Games (Winner)', min_value=0, max_value=7, required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    loser_games_set3 = forms.IntegerField(label='Set 3 Games (Loser)', min_value=0, max_value=7, required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    
    # Update the date field to use the mm-dd-yyyy format
    date = forms.DateField(
        label='Match Date',
        widget=DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%m-%d-%Y')
    )
    
    notes = forms.CharField(label='Notes', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)

    class Meta:
        model = Match
        fields = ['winner', 'loser', 'date', 'notes']

    def clean(self):
        cleaned_data = super().clean()
        # Combine set scores into the required format
        set_scores = [
            (cleaned_data.get('winner_games_set1'), cleaned_data.get('loser_games_set1')),
            (cleaned_data.get('winner_games_set2'), cleaned_data.get('loser_games_set2')),
        ]
        if cleaned_data.get('winner_games_set3') is not None and cleaned_data.get('loser_games_set3') is not None:
            set_scores.append((cleaned_data.get('winner_games_set3'), cleaned_data.get('loser_games_set3')))
        cleaned_data['set_scores'] = set_scores
        return cleaned_data

# Helper function to generate floating point range
def frange(start, stop, step):
    while start <= stop:
        yield start
        start += step

class CustomSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    neighborhood = forms.ChoiceField(choices=Player.NEIGHBORHOOD_CHOICES, label="Neighborhood")

    phone_number = forms.CharField(max_length=15, label="Phone Number (US only)", required=False)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # Validate US phone number format (e.g., 123-456-7890 or (123) 456-7890)
            if not re.match(r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$', phone_number):
                raise ValidationError("Please enter a valid US phone number.")
        return phone_number

    # Define USTA rating choices (3.00 to 6.00 in 0.25 increments)
    USTA_RATING_CHOICES = [(round(x, 2), f"{round(x, 2)}") for x in frange(3.00, 6.00, 0.25)]

    usta_rating = forms.ChoiceField(choices=USTA_RATING_CHOICES, required=True, label="USTA Rating")

    # Custom help text for the password fields
    password1 = forms.CharField(
        widget=forms.PasswordInput(),
        help_text="Your password must be at least 8 characters long, contain both letters and numbers, and have at least one special character.",
        label="Password"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(),
        help_text="Enter the same password again for confirmation.",
        label="Confirm password"
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'usta_rating', 'neighborhood', 'phone_number')

