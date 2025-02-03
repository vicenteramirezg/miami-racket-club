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
from email.header import Header
from email.utils import formataddr

@login_required
def submit_match(request):
    if request.method == 'POST':
        form = MatchForm(request.POST)
        if form.is_valid():
            match = form.save(commit=False)
            match.set_scores = form.cleaned_data['set_scores']  # Save set scores
            match.save()
            send_match_notification(match)  # Send notification
            return redirect('leaderboard')
    else:
        form = MatchForm()
    return render(request, 'rankings/submit_match.html', {'form': form})

def leaderboard(request):
    players = Player.objects.order_by('-elo_rating')
    return render(request, 'rankings/leaderboard.html', {'players': players})

def send_match_notification(match):
    from_email = formataddr(("🎾 Miami Racket Club", settings.DEFAULT_FROM_EMAIL))
    subject = Header("New Match Submitted!", "utf-8").encode()
    
    # Hosted/static image URL (update if necessary)
    logo_url = "https://themiamiracketclub.com/static/rankings/logo.png"

    # Font URL (import Google Font)
    font_url = "https://fonts.googleapis.com/css2?family=Alegreya:wght@400;700&display=swap"

    for player in [match.winner, match.loser]:
        opponent = match.loser.user.username if player == match.winner else match.winner.user.username
        result = "✅ Win" if player == match.winner else "❌ Lose"

        # Plain text version (fallback)
        plain_message = f'''
        🎉 A new match has been submitted!

        - 🏆 Result: {result}
        - 🆚 Opponent: {opponent}
        - 📊 Score: {match.set_scores}
        - 📅 Date: {match.date}
        - 📝 Notes: {match.notes}

        See you on court!
        '''

        # HTML version with logo and styles
        html_message = f'''
        <html>
        <head>
            <style>
                /* Import Alegreya font */
                @import url('{font_url}');

                /* Apply custom styles */
                body {{
                    font-family: 'Alegreya', serif;
                    color: #104730; /* Dark green text */
                    background-color: #ffffff; /* White background */
                    margin: 0;
                    padding: 20px;
                }}

                .email-container {{
                    max-width: 500px;
                    margin: auto;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    background-color: #f9f9f9;
                }}

                .email-header {{
                    text-align: center;
                }}

                .email-header img {{
                    max-width: 150px;
                    margin-bottom: 10px;
                }}

                .email-content {{
                    text-align: center;
                }}

                h3 {{
                    color: #104730; /* Dark green for the header */
                }}

                p {{
                    font-size: 16px;
                    margin: 10px 0;
                }}

                .footer {{
                    margin-top: 20px;
                    text-align: center;
                    font-size: 14px;
                }}

                a {{
                    color: #104730;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <img src="{logo_url}" alt="Miami Racket Club Logo">
                </div>
                <div class="email-content">
                    <h3>New Match Submitted! 🎉</h3>
                    <p><strong>🏆 Result:</strong> {result}</p>
                    <p><strong>🆚 Opponent:</strong> {opponent}</p>
                    <p><strong>📊 Score:</strong> {match.set_scores}</p>
                    <p><strong>📅 Date:</strong> {match.date}</p>
                    <p><strong>📝 Notes:</strong> {match.notes}</p>
                </div>
                <div class="footer">
                    <p>See you on court!</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        recipient_list = [player.user.email]
        send_mail(subject, plain_message, from_email, recipient_list, html_message=html_message)

def home(request):
    recent_matches = Match.objects.order_by('-date')[:5]  # Get the 5 most recent matches
    context = {
        'recent_matches': recent_matches,
    }
    return render(request, 'rankings/home.html', context)

def profile(request, username):
    player = get_object_or_404(Player, user__username=username)
    matches = Match.objects.filter(winner=player) | Match.objects.filter(loser=player)
    matches = matches.order_by('-date')  # Show most recent matches first

    # Calculate statistics
    matches_played = matches.count()
    matches_won = matches.filter(winner=player).count()
    matches_lost = matches_played - matches_won
    match_win_percentage = (matches_won / matches_played) * 100 if matches_played > 0 else 0

    sets_won = 0
    sets_lost = 0
    games_won = 0
    games_lost = 0

    for match in matches:
        for set_score in match.set_scores:
            if match.winner == player:
                sets_won += 1
                games_won += set_score[0]
                games_lost += set_score[1]
            else:
                sets_lost += 1
                games_won += set_score[1]
                games_lost += set_score[0]

    game_win_percentage = (games_won / (games_won + games_lost)) * 100 if (games_won + games_lost) > 0 else 0

    context = {
        'player': player,
        'matches': matches,
        'matches_played': matches_played,
        'matches_won': matches_won,
        'matches_lost': matches_lost,
        'match_win_percentage': round(match_win_percentage, 1),  # Round to 2 decimal places
        'sets_won': sets_won,
        'sets_lost': sets_lost,
        'games_won': games_won,
        'games_lost': games_lost,
        'game_win_percentage': round(game_win_percentage, 1),  # Round to 2 decimal places
    }

    return render(request, 'rankings/profile.html', context)

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
