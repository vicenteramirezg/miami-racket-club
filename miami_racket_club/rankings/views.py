from django.shortcuts import render, redirect
from .forms import MatchForm
from .models import Player

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