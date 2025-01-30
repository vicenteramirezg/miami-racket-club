from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import MatchForm
from .models import Player
from django.contrib.auth.decorators import login_required

@login_required
def submit_match(request):
    if request.method == 'POST':
        form = MatchForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('leaderboard')
    else:
        form = MatchForm()
    return render(request, 'rankings/submit_match.html', {'form': form})

def leaderboard(request):
    players = Player.objects.order_by('-elo_rating')
    return render(request, 'rankings/leaderboard.html', {'players': players})

def home(request):
    return render(request, 'rankings/home.html')

class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'