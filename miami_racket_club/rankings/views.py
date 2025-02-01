from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.core.mail import send_mail
from django.conf import settings
from .forms import MatchForm, CustomSignUpForm  # Ensure this import is correct
from .models import Player, Match
from django.contrib.auth.decorators import login_required

@login_required
def submit_match(request):
    if request.method == 'POST':
        form = MatchForm(request.POST)
        if form.is_valid():
            match = form.save()
            send_match_notification(match)
            return redirect('leaderboard')
    else:
        form = MatchForm()
    return render(request, 'rankings/submit_match.html', {'form': form})

def leaderboard(request):
    players = Player.objects.order_by('-elo_rating')
    return render(request, 'rankings/leaderboard.html', {'players': players})

def send_match_notification(match):
    subject = 'New Match Submitted'
    message = f'''
    A new match has been submitted:
    - Winner: {match.winner.user.username}
    - Loser: {match.loser.user.username}
    - Score: {match.set_scores}
    - Date: {match.date}
    '''
    recipient_list = [match.winner.user.email, match.loser.user.email]  # Send to both players
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

def home(request):
    return render(request, 'rankings/home.html')

def profile(request, username):
    player = get_object_or_404(Player, user__username=username)
    matches = Match.objects.filter(winner=player) | Match.objects.filter(loser=player)
    matches = matches.order_by('-date')  # Show most recent matches first
    return render(request, 'rankings/profile.html', {'player': player, 'matches': matches})

class SignUpView(CreateView):
    form_class = CustomSignUpForm  # Use the custom form
    success_url = reverse_lazy('home')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        user = form.save()
        usta_rating = form.cleaned_data.get('usta_rating')

        # Save USTA Rating in Player model
        Player.objects.create(user=user, usta_rating=float(usta_rating))

        login(self.request, user)
        return redirect(self.success_url)