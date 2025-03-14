from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Match, Player, MatchDoubles
from django.forms import DateInput
import re
from django.utils import timezone
from django.core.exceptions import ValidationError

# Define valid set scores
VALID_SET_SCORES = [
    (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (7, 5), (7, 6),
    (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 7), (6, 7)
]

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Order players alphabetically by first name and last name
        self.fields['winner'].queryset = Player.objects.order_by('first_name', 'last_name')
        self.fields['loser'].queryset = Player.objects.order_by('first_name', 'last_name')

    class Meta:
        model = Match
        fields = ['winner', 'loser', 'date', 'notes']  # Excluding `submitted_by`

    def clean(self):
        cleaned_data = super().clean()

        # Check if the match date is in the future
        match_date = cleaned_data.get('date')
        if match_date and match_date > timezone.now().date():
            raise forms.ValidationError("The match date cannot be in the future.")

        winner = cleaned_data.get('winner')
        loser = cleaned_data.get('loser')

        # Check if winner and loser are the same player
        if winner and loser and winner == loser:
            raise forms.ValidationError("The winner and loser cannot be the same player.")

        set_scores = []
        for i in range(1, 4):  # Loop through possible sets
            winner_score = cleaned_data.get(f'winner_games_set{i}')
            loser_score = cleaned_data.get(f'loser_games_set{i}')
            if winner_score is not None and loser_score is not None:
                set_scores.append((winner_score, loser_score))

        if not set_scores:
            raise forms.ValidationError("At least one set must be recorded.")
        
        # Validate each set score
        for index, set_score in enumerate(set_scores):
            if index == 2 and set_score == (1, 0):  # Third set super tie-break rule
                continue  # Allow (1,0) for third set
            if set_score not in VALID_SET_SCORES:
                raise forms.ValidationError(f"Invalid set score: {set_score}.")

        winner_sets = sum(1 for w, l in set_scores if w > l)
        loser_sets = len(set_scores) - winner_sets

        if winner_sets <= loser_sets:
            raise forms.ValidationError("The winner must win more sets than the loser.")
        elif winner_sets == loser_sets:
            raise forms.ValidationError("The match cannot end in a tie. One player must win more sets than the other.")

        cleaned_data['set_scores'] = set_scores  # Ensure it's stored properly
        return cleaned_data

class MatchDoublesForm(forms.ModelForm):
    winner_games_set1 = forms.IntegerField(label='Set 1 Games (Winners)', min_value=0, max_value=7, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    winner_games_set2 = forms.IntegerField(label='Set 2 Games (Winners)', min_value=0, max_value=7, required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    winner_games_set3 = forms.IntegerField(label='Set 3 Games (Winners)', min_value=0, max_value=7, required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    loser_games_set1 = forms.IntegerField(label='Set 1 Games (Losers)', min_value=0, max_value=7, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    loser_games_set2 = forms.IntegerField(label='Set 2 Games (Losers)', min_value=0, max_value=7, required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    loser_games_set3 = forms.IntegerField(label='Set 3 Games (Losers)', min_value=0, max_value=7, required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    date = forms.DateField(
        label='Match Date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%m-%d-%Y'),
        initial=timezone.now
    )

    notes = forms.CharField(label='Notes', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order players alphabetically by first name and last name
        ordered_players = Player.objects.order_by('first_name', 'last_name')
        self.fields['winner1'].queryset = ordered_players
        self.fields['winner2'].queryset = ordered_players
        self.fields['loser1'].queryset = ordered_players
        self.fields['loser2'].queryset = ordered_players

    class Meta:
        model = MatchDoubles
        fields = ['winner1', 'winner2', 'loser1', 'loser2', 'date', 'notes']  # Exclude `set_scores`

    def clean(self):
        cleaned_data = super().clean()

        # Check if the match date is in the future
        match_date = cleaned_data.get('date')
        if match_date and match_date > timezone.now().date():
            raise forms.ValidationError("The match date cannot be in the future.")

        # Ensure all required fields are filled for Doubles
        winner1 = cleaned_data.get('winner1')
        winner2 = cleaned_data.get('winner2')
        loser1 = cleaned_data.get('loser1')
        loser2 = cleaned_data.get('loser2')

        if not all([winner1, winner2, loser1, loser2]):
            raise forms.ValidationError("All players must be selected for a Doubles match.")

        # Check for duplicate players in the same team
        if winner1 == winner2:
            raise forms.ValidationError("The two winners cannot be the same player.")
        if loser1 == loser2:
            raise forms.ValidationError("The two losers cannot be the same player.")

        # Check for duplicate players across teams
        if winner1 in [loser1, loser2] or winner2 in [loser1, loser2]:
            raise forms.ValidationError("A player cannot be on both the winning and losing teams.")

        # Validate set scores
        set_scores = []
        for i in range(1, 4):  # Loop through possible sets
            winner_score = cleaned_data.get(f'winner_games_set{i}')
            loser_score = cleaned_data.get(f'loser_games_set{i}')
            if winner_score is not None and loser_score is not None:
                set_scores.append((winner_score, loser_score))

        if not set_scores:
            raise forms.ValidationError("At least one set must be recorded.")

        # Validate each set score
        for set_score in set_scores:
            if set_score not in VALID_SET_SCORES:
                raise forms.ValidationError(f"Invalid set score: {set_score}.")

        winner_sets = sum(1 for w, l in set_scores if w > l)
        loser_sets = len(set_scores) - winner_sets

        if winner_sets <= loser_sets:
            raise forms.ValidationError("The winning team must win more sets than the losing team.")
        elif winner_sets == loser_sets:
            raise forms.ValidationError("The match cannot end in a tie. One team must win more sets than the other.")

        cleaned_data['set_scores'] = set_scores  # Ensure it's stored properly
        return cleaned_data

# Helper function to generate floating point range
def frange(start, stop, step):
    while start <= stop:
        yield start
        start += step

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from rankings.models import Player  # Import your Player model
from .models import User  # Import your User model

class CustomSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=50, required=True, label="First Name")
    last_name = forms.CharField(max_length=50, required=True, label="Last Name")
    neighborhood = forms.ChoiceField(choices=Player.NEIGHBORHOOD_CHOICES, label="Neighborhood")
    phone_number = forms.CharField(max_length=15, label="Phone Number", required=False)

    agree_to_terms = forms.BooleanField(
        required=True,
        label='I agree to the <a href="/terms-and-conditions/" target="_blank">Terms and Conditions</a>.',
        error_messages={'required': 'You must agree to the Terms and Conditions to sign up.'}
    )

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
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'usta_rating', 'neighborhood', 'phone_number', 'agree_to_terms')

    def clean_username(self):
        """
        Normalize the username to lowercase to ensure case-insensitive uniqueness.
        """
        username = self.cleaned_data.get('username')
        if username:
            username = username.lower()  # Normalize to lowercase
        return username

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
    
class UsernameRetrievalForm(forms.Form):
    email = forms.EmailField(label="Enter your email address")