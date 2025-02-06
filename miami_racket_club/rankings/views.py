from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.db.models import Q
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
from django.core.paginator import Paginator

@login_required
def submit_match(request):
    if request.method == 'POST':
        form = MatchForm(request.POST)
        if form.is_valid():
            match = form.save(commit=False)
            match.set_scores = form.cleaned_data['set_scores']
            match.submitted_by = request.user  # Set the user who submitted the match
            match.save()
            send_match_notification(match)  # Send notification
            return redirect('leaderboard')
    else:
        form = MatchForm()
    return render(request, 'rankings/submit_match.html', {'form': form})

def leaderboard(request):
    players = Player.objects.order_by('-elo_rating')
    return render(request, 'rankings/leaderboard.html', {'players': players})

def terms_and_conditions(request):
    return render(request, 'registration/terms_and_conditions.html')

def send_match_notification(match):
    from_email = formataddr(("Miami Racket Club", settings.DEFAULT_FROM_EMAIL))
    subject = Header("New Match Submitted!", "utf-8").encode()
    
    # Hosted/static image URL (update if necessary)
    logo_url = "https://miami-racket-club-496610aca6a3.herokuapp.com/static/rankings/logo-color.png"

    # Font URL (import Google Font)
    font_url = "https://fonts.googleapis.com/css2?family=Alegreya:wght@400;700&display=swap"

    for player in [match.winner, match.loser]:
        opponent = match.loser.user.first_name + ' ' + match.loser.user.last_name if player == match.winner else match.winner.user.first_name + ' ' + match.winner.user.last_name
        result = "✅ Win" if player == match.winner else "❌ Lose"

        # Create the profile URL
        profile_url = f"{settings.SITE_URL}/profile/{player.user.username}"

        # Plain text version (fallback)
        plain_message = f'''
        🎉 A new match has been submitted!

        - 🏆 Result: {result}
        - 🆚 Opponent: {opponent}
        - 📊 Score: {match.clean_score}
        - 📅 Date: {match.date}
        - 📝 Notes: {match.notes}

        Visit your profile: {profile_url}

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
                    color: #c8c097; /* Light beige text color */
                    text-decoration: none; /* Remove underline */
                }}
                a:hover {{
                    text-decoration: none; /* Ensure no underline on hover */
                }}

                .profile-button {{
                    display: inline-block;
                    background-color: #c8c097; /* Light beige background */
                    color: #c8c097; /* Light beige text color */
                    padding: 12px 20px;
                    font-size: 16px;
                    font-weight: bold;
                    text-decoration: none;
                    border-radius: 8px;
                    text-align: center;
                    transition: background-color 0.3s ease;
                }}

                .profile-button:hover {{
                    background-color: #9c9572; /* Darker green on hover */
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <img src="{logo_url}" alt="Miami Racket Club Logo">
                </div>
                <div class="email-content">
                    <h3>New Match Submitted</h3>
                    <p><strong>🏆 Result:</strong> {result}</p>
                    <p><strong>🆚 Opponent:</strong> {opponent}</p>
                    <p><strong>📊 Score:</strong> {match.clean_score}</p>
                    <p><strong>📅 Date:</strong> {match.date}</p>
                    <p><strong>📝 Notes:</strong> {match.notes}</p>
                    <p style="text-align: center;">
                        <a href="{profile_url}" class="profile-button">View Profile</a>
                    </p>
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

    sets_won = 0
    sets_lost = 0
    games_won = 0
    games_lost = 0

    for match in matches:
        for set_score in match.set_scores:
            if match.winner == player:  # If player won the match
                sets_won += 1 if set_score[0] > set_score[1] else 0
                sets_lost += 1 if set_score[0] < set_score[1] else 0
                games_won += set_score[0]
                games_lost += set_score[1]
            else:  # If player lost the match
                sets_won += 1 if set_score[1] > set_score[0] else 0
                sets_lost += 1 if set_score[1] < set_score[0] else 0
                games_won += set_score[1]
                games_lost += set_score[0]

    # Calculate totals
    sets_played = sets_won + sets_lost
    games_played = games_won + games_lost

    # Calculate percentages
    match_win_percentage = (matches_won / matches_played * 100) if matches_played > 0 else 0
    set_win_percentage = (sets_won / sets_played * 100) if sets_played > 0 else 0
    game_win_percentage = (games_won / games_played * 100) if games_played > 0 else 0

    # Get ELO history
    elo_history = player.elo_history.order_by('date')

    # Calculate Current Streak (most recent wins until a loss)
    current_streak = 0
    for match in matches:
        if match.winner == player:
            current_streak += 1
        else:
            break  # Stop when the first loss is encountered

    # Calculate Longest Streak Ever (longest sequence of wins in history)
    longest_streak = 0
    current_streak_temp = 0
    for match in matches:
        if match.winner == player:
            current_streak_temp += 1
        else:
            longest_streak = max(longest_streak, current_streak_temp)
            current_streak_temp = 0  # Reset streak after a loss
    longest_streak = max(longest_streak, current_streak_temp)  # Check in case the longest streak ends with wins

    context = {
        'player': player,
        'matches': matches,
        'matches_played': matches_played,
        'matches_won': matches_won,
        'matches_lost': matches_lost,
        'sets_won': sets_won,
        'sets_lost': sets_lost,
        'sets_played': sets_played,  # Pass the calculated total
        'games_won': games_won,
        'games_lost': games_lost,
        'games_played': games_played,  # Pass the calculated total
        'match_win_percentage': round(match_win_percentage, 1),
        'set_win_percentage': round(set_win_percentage, 1),
        'game_win_percentage': round(game_win_percentage, 1),
        'elo_history': elo_history,  # Pass ELO history to the template
        'current_streak': current_streak,  # Add current streak to context
        'longest_streak': longest_streak  # Add longest streak to context
    }

    return render(request, 'rankings/profile.html', context)

class SignUpView(CreateView):
    form_class = CustomSignUpForm
    success_url = reverse_lazy('home')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        # Save the User instance
        user = form.save()

        # Ensure a Player instance is created only if one doesn't already exist
        player, created = Player.objects.get_or_create(
            user=user,
            defaults={
                "first_name": form.cleaned_data.get("first_name", ""),
                "last_name": form.cleaned_data.get("last_name", ""),
                "usta_rating": form.cleaned_data.get("usta_rating", 3.00),
                "neighborhood": form.cleaned_data.get("neighborhood", "Other"),
                "phone_number": form.cleaned_data.get("phone_number", ""),
            }
        )

        # Log the user in
        login(self.request, user)
        return redirect(self.success_url)
    
def player_directory(request):
    # Get all players ordered alphabetically by default
    players = Player.objects.order_by('first_name', 'last_name')

    # Initialize filter variables
    neighborhoods = request.GET.getlist('neighborhood')  # Multiple neighborhoods can be selected
    min_rating = request.GET.get('min_rating', 3.0)  # Default min rating if not provided
    max_rating = request.GET.get('max_rating', 6.0)  # Default max rating if not provided

    # Apply filters if provided
    if neighborhoods:
        players = players.filter(neighborhood__in=neighborhoods)
    if min_rating:
        players = players.filter(usta_rating__gte=float(min_rating))
    if max_rating:
        players = players.filter(usta_rating__lte=float(max_rating))

    paginator = Paginator(players, 25)  # Show 25 players per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Clean phone numbers for paginated players
    for player in page_obj:
        player.cleaned_phone = player.phone_number.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')

    # Get unique neighborhoods for the filter dropdown
    unique_neighborhoods = Player.objects.values_list('neighborhood', flat=True).distinct().order_by('neighborhood')

    context = {
        'players': players,
        'page_obj': page_obj,
        'unique_neighborhoods': unique_neighborhoods,
        'selected_neighborhoods': neighborhoods,
        'min_rating': float(min_rating),
        'max_rating': float(max_rating),
    }
    return render(request, 'rankings/player_directory.html', context)