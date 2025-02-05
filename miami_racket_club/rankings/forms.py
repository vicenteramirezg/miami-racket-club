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

    date = forms.DateField(
        label='Match Date',
        widget=DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%m-%d-%Y')
    )

    notes = forms.CharField(label='Notes', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)

    class Meta:
        model = Match
        fields = ['winner', 'loser', 'date', 'notes']  # Excluding `submitted_by`

    def clean(self):
        cleaned_data = super().clean()

        set_scores = []
        for i in range(1, 4):  # Loop through possible sets
            winner_score = cleaned_data.get(f'winner_games_set{i}')
            loser_score = cleaned_data.get(f'loser_games_set{i}')
            if winner_score is not None and loser_score is not None:
                set_scores.append((winner_score, loser_score))

        if not set_scores:
            raise forms.ValidationError("At least one set must be recorded.")

        winner_sets = sum(1 for w, l in set_scores if w > l)
        loser_sets = len(set_scores) - winner_sets

        if winner_sets <= loser_sets:
            raise forms.ValidationError("The winner must win more sets than the loser.")

        cleaned_data['set_scores'] = set_scores  # Ensure it's stored properly
        return cleaned_data

# Helper function to generate floating point range
def frange(start, stop, step):
    while start <= stop:
        yield start
        start += step

class CustomSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=50, required=True, label="First Name")
    last_name = forms.CharField(max_length=50, required=True, label="Last Name")
    neighborhood = forms.ChoiceField(choices=Player.NEIGHBORHOOD_CHOICES, label="Neighborhood")
    phone_number = forms.CharField(max_length=15, label="Phone Number", required=False)

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
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'usta_rating', 'neighborhood', 'phone_number')

    def save(self, commit=True):
        # Save the User instance first
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()

        # Create the Player instance and link it to the User
        player = Player(
            user=user,
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            usta_rating=self.cleaned_data['usta_rating'],
            neighborhood=self.cleaned_data['neighborhood'],
            phone_number=self.cleaned_data['phone_number']
        )
        if commit:
            player.save()

        return user