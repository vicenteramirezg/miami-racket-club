from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib import messages
from django.db.models import Q, F, Count, Sum, Case, When
from django.db.models.functions import Coalesce
from django.db import models
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth.models import User  # Add this import
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from .forms import MatchForm, CustomSignUpForm, UsernameRetrievalForm, MatchDoublesForm
from .models import Player, Match, ELOHistory, MatchDoubles, ELOHistoryDoubles
from .decorators import approved_required
from django.contrib.auth.decorators import login_required
from email.header import Header
from email.utils import formataddr
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils.html import strip_tags

USTA_TO_UTR = {
    3: 4,
    3.25: 4.5,
    3.5: 5,
    3.75: 5.5,
    4: 6,
    4.25: 7,
    4.5: 8,
    4.75: 9,
    5: 10,
    5.25: 10.5,
    5.5: 11,
    5.75: 11.5,
    6: 12
}

@login_required
@approved_required
def submit_doubles_match(request):
    if request.method == 'POST':
        form = MatchDoublesForm(request.POST)
        if form.is_valid():
            match = form.save(commit=False)
            match.submitted_by = request.user
            match.set_scores = form.cleaned_data['set_scores']  # Ensure set_scores is set
            match.save()

            # Create ELOHistoryDoubles records for the two winners and two losers
            winner1 = form.cleaned_data['winner1']
            winner2 = form.cleaned_data['winner2']
            loser1 = form.cleaned_data['loser1']
            loser2 = form.cleaned_data['loser2']

            # Save ELOHistoryDoubles for the winners and losers
            for player in [winner1, winner2]:
                ELOHistoryDoubles.objects.create(
                    player=player,
                    match=match,
                    elo_rating_doubles=player.elo_rating_doubles,  # Adjust based on how you calculate the rating
                    date=match.date,
                )

            for player in [loser1, loser2]:
                ELOHistoryDoubles.objects.create(
                    player=player,
                    match=match,
                    elo_rating_doubles=player.elo_rating_doubles,  # Adjust based on how you calculate the rating
                    date=match.date,
                )

            # Generate a spicy notification message
            winner1_name = f"{winner1.user.first_name} {winner1.user.last_name}"
            winner2_name = f"{winner2.user.first_name} {winner2.user.last_name}"
            loser1_name = f"{loser1.user.first_name} {loser1.user.last_name}"
            loser2_name = f"{loser2.user.first_name} {loser2.user.last_name}"
            match_score = " - ".join([f"{w}-{l}" for w, l in match.set_scores])
            match_date = match.date.strftime("%Y-%m-%d")

            notification_message = (
                f"🎾 New Doubles Match Submitted:\n\n"
                f"{winner1_name} and {winner2_name} took the win on {match_date} against {loser1_name} and {loser2_name} by {match_score}."
            )

            # Add the message to Django's messaging framework
            messages.success(request, notification_message)

            send_doubles_match_notification(match)  # Use the new function
            return redirect('leaderboard')
    else:
        form = MatchDoublesForm()

    return render(request, 'rankings/submit_doubles_match.html', {'form': form})

@login_required
@approved_required
def submit_match(request):
    if request.method == 'POST':
        form = MatchForm(request.POST)
        if form.is_valid():
            match = form.save(commit=False)
            match.set_scores = form.cleaned_data['set_scores']
            match.submitted_by = request.user  # Set the user who submitted the match
            match.save()

            # Generate a spicy notification message
            winner_name = f"{match.winner.user.first_name} {match.winner.user.last_name}"
            loser_name = f"{match.loser.user.first_name} {match.loser.user.last_name}"
            match_score = " - ".join([f"{w}-{l}" for w, l in match.set_scores])
            match_date = match.date.strftime("%Y-%m-%d")

            notification_message = (
                f"🎾 New Singles Match Submitted:\n\n"
                f"{winner_name} took the win on {match_date} against {loser_name} by {match_score}."
            )

            # Send the notification (if you have a function for this)
            send_match_notification(match)

            # Add the message to Django's messaging framework
            messages.success(request, notification_message)

            return redirect('leaderboard')
    else:
        form = MatchForm()
    return render(request, 'rankings/submit_match.html', {'form': form})

@login_required
@approved_required
def leaderboard(request):
    # Fetch only necessary fields for singles and doubles leaderboards
    singles_players = Player.objects.order_by('-elo_rating').only('first_name', 'last_name', 'elo_rating')
    doubles_players = Player.objects.order_by('-elo_rating_doubles').only('first_name', 'last_name', 'elo_rating_doubles')

    # Paginate singles players
    singles_paginator = Paginator(singles_players, 25)  # 25 players per page
    singles_page_number = request.GET.get('singles_page')
    singles_page = singles_paginator.get_page(singles_page_number)

    # Paginate doubles players
    doubles_paginator = Paginator(doubles_players, 25)  # 25 players per page
    doubles_page_number = request.GET.get('doubles_page')
    doubles_page = doubles_paginator.get_page(doubles_page_number)

    context = {
        'singles_page': singles_page,
        'doubles_page': doubles_page,
    }
    return render(request, 'rankings/leaderboard.html', context)

def terms_and_conditions(request):
    return render(request, 'registration/terms_and_conditions.html')

def send_match_notification(match):
    from_email = formataddr(("Miami Racket Club", settings.DEFAULT_FROM_EMAIL))
    subject = Header("New Match Submitted", "utf-8").encode()
    
    # Hosted/static image URL (update if necessary)
    logo_url = "https://miami-racket-club-496610aca6a3.herokuapp.com/static/rankings/logo-color.png"

    # Font URL (import Google Font)
    font_url = "https://fonts.googleapis.com/css2?family=Alegreya:wght@400;700&display=swap"

    for player in [match.winner, match.loser]:
        opponent = match.loser.user.first_name + ' ' + match.loser.user.last_name if player == match.winner else match.winner.user.first_name + ' ' + match.winner.user.last_name
        result = "✅ Win" if player == match.winner else "❌ Lose"

        # Create the profile URL
        profile_url = f"{settings.SITE_URL}/profile/{player.user.username}"

        # Replace double spaces with &nbsp;
        formatted_score = match.clean_score().replace("  ", "&nbsp;&nbsp;")

        # Plain text version (fallback)
        plain_message = f'''
        🎉 A new match has been submitted!

        - 🏆 Result: {result}
        - 🆚 Opponent: {opponent}
        - 📊 Score: {formatted_score}
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

                /* Hidden preview text */
                .preview-text {{
                    display: none;
                    font-size: 0;
                    color: transparent;
                    line-height: 0;
                    max-height: 0;
                    mso-hide: all; /* Hide in Outlook */
                }}
            </style>
        </head>
        <body>
            <!-- Hidden preview text -->
            <span class="preview-text">A new match has been submitted. Check the details.</span>

            <div class="email-container">
                <div class="email-header">
                    <img src="{logo_url}" alt="Miami Racket Club Logo">
                </div>
                <div class="email-content">
                    <h3>New Match Submitted</h3>
                    <p><strong>🏆 Result:</strong> {result}</p>
                    <p><strong>🆚 Opponent:</strong> {opponent}</p>
                    <p><strong>📊 Score:</strong> {formatted_score}</p>
                    <p><strong>📅 Date:</strong> {match.date}</p>
                    <p><strong>📝 Notes:</strong> {match.notes}</p>
                    <p style="text-align: center;">
                        <a href="{profile_url}" class="profile-button">View Profile</a>
                        <a href="https://docs.google.com/forms/d/e/1FAIpQLSfSGy5zy6x8zSiVnA5s2a7ImnUOgiP3hN4rbmecO_RYJWRu6Q/viewform?usp=sharing" class="profile-button">Fill Out Survey</a>
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

def send_doubles_match_notification(match):
    from_email = formataddr(("Miami Racket Club", settings.DEFAULT_FROM_EMAIL))
    subject = Header("New Doubles Match Submitted", "utf-8").encode()
    
    # Hosted/static image URL (update if necessary)
    logo_url = "https://miami-racket-club-496610aca6a3.herokuapp.com/static/rankings/logo-color.png"

    # Font URL (import Google Font)
    font_url = "https://fonts.googleapis.com/css2?family=Alegreya:wght@400;700&display=swap"

    # Get all players involved in the match
    players = [match.winner1, match.winner2, match.loser1, match.loser2]

    for player in players:
        # Determine the player's team and result
        if player in [match.winner1, match.winner2]:
            result = "✅ Win"
            teammate = match.winner2 if player == match.winner1 else match.winner1
            opponents = f"{match.loser1.user.first_name} {match.loser1.user.last_name} & {match.loser2.user.first_name} {match.loser2.user.last_name}"
        else:
            result = "❌ Lose"
            teammate = match.loser2 if player == match.loser1 else match.loser1
            opponents = f"{match.winner1.user.first_name} {match.winner1.user.last_name} & {match.winner2.user.first_name} {match.winner2.user.last_name}"

        # Create the profile URL
        profile_url = f"{settings.SITE_URL}/profile/{player.user.username}"

        # Replace double spaces with &nbsp;
        formatted_score = match.clean_score().replace("  ", "&nbsp;&nbsp;")

        # Plain text version (fallback)
        plain_message = f'''
        🎉 A new doubles match has been submitted!

        - 🏆 Result: {result}
        - 🤝 Teammate: {teammate.user.first_name} {teammate.user.last_name}
        - 🆚 Opponents: {opponents}
        - 📊 Score: {formatted_score}
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

                /* Hidden preview text */
                .preview-text {{
                    display: none;
                    font-size: 0;
                    color: transparent;
                    line-height: 0;
                    max-height: 0;
                    mso-hide: all; /* Hide in Outlook */
                }}
            </style>
        </head>
        <body>
            <!-- Hidden preview text -->
            <span class="preview-text">A new doubles match has been submitted. Check the details.</span>

            <div class="email-container">
                <div class="email-header">
                    <img src="{logo_url}" alt="Miami Racket Club Logo">
                </div>
                <div class="email-content">
                    <h3>New Doubles Match Submitted</h3>
                    <p><strong>🏆 Result:</strong> {result}</p>
                    <p><strong>🤝 Teammate:</strong> {teammate.user.first_name} {teammate.user.last_name}</p>
                    <p><strong>🆚 Opponents:</strong> {opponents}</p>
                    <p><strong>📊 Score:</strong> {formatted_score}</p>
                    <p><strong>📅 Date:</strong> {match.date}</p>
                    <p><strong>📝 Notes:</strong> {match.notes}</p>
                    <p style="text-align: center;">
                        <a href="{profile_url}" class="profile-button">View Profile</a>
                        <a href="https://docs.google.com/forms/d/e/1FAIpQLSfSGy5zy6x8zSiVnA5s2a7ImnUOgiP3hN4rbmecO_RYJWRu6Q/viewform?usp=sharing" class="profile-button">Fill Out Survey</a>
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

@approved_required
def home(request):
    # Get recent singles matches (last 5 matches) with related fields optimized
    recent_singles_matches = (
        Match.objects
        .select_related('winner', 'loser')  # Optimize foreign key lookups
        .only('date', 'winner__first_name', 'winner__last_name', 'loser__first_name', 'loser__last_name', 'set_scores')  # Fetch only necessary fields
        .order_by('-date')[:5]
    )

    # Get recent doubles matches (last 5 matches) with related fields optimized
    recent_doubles_matches = (
        MatchDoubles.objects
        .select_related('winner1', 'winner2', 'loser1', 'loser2')  # Optimize foreign key lookups
        .only('date', 'winner1__first_name', 'winner1__last_name', 'winner2__first_name', 'winner2__last_name', 'loser1__first_name', 'loser1__last_name', 'loser2__first_name', 'loser2__last_name', 'set_scores')  # Fetch only necessary fields
        .order_by('-date')[:5]
    )

    context = {
        'recent_singles_matches': recent_singles_matches,
        'recent_doubles_matches': recent_doubles_matches,
    }
    return render(request, 'rankings/home.html', context)

def calculate_longest_streak(matches, player, is_singles=True):
    """
    Calculate the longest streak of wins for a player.
    """
    longest_streak = 0
    current_streak = 0

    for match in matches:
        if is_singles:
            if match.winner == player:
                current_streak += 1
            else:
                if current_streak > longest_streak:
                    longest_streak = current_streak
                current_streak = 0
        else:
            if match.winner1 == player or match.winner2 == player:
                current_streak += 1
            else:
                if current_streak > longest_streak:
                    longest_streak = current_streak
                current_streak = 0

    # Check if the last match was part of the longest streak
    if current_streak > longest_streak:
        longest_streak = current_streak

    return longest_streak

@login_required
@approved_required
def profile(request, username):
    player = get_object_or_404(
        Player.objects.select_related('user'),  # Optimize user lookup
        user__username=username
    )

    # Fetch singles matches with related players
    singles_matches = Match.objects.filter(
        (Q(winner=player) | Q(loser=player)) & Q(is_deleted=False)
    ).select_related('winner', 'loser').order_by('-date')

    # Fetch doubles matches with related players
    doubles_matches = MatchDoubles.objects.filter(
        (Q(winner1=player) | Q(winner2=player) | Q(loser1=player) | Q(loser2=player)) & Q(is_deleted=False)
    ).select_related('winner1', 'winner2', 'loser1', 'loser2').order_by('-date')

    # Fetch ELO history
    elo_history = ELOHistory.objects.filter(player=player, is_valid=True).select_related('player').order_by('submitted_at')
    elo_history_doubles = ELOHistoryDoubles.objects.filter(player=player, is_valid=True).select_related('player').order_by('submitted_at')

    # Calculate singles statistics
    singles_stats = {
        'matches_played': singles_matches.count(),
        'matches_won': singles_matches.filter(winner=player).count(),
        'sets_won': 0,
        'sets_lost': 0,
        'games_won': 0,
        'games_lost': 0,
    }

    for match in singles_matches:
        for set_score in match.set_scores:
            if match.winner == player:
                singles_stats['sets_won'] += 1 if set_score[0] > set_score[1] else 0
                singles_stats['sets_lost'] += 1 if set_score[0] < set_score[1] else 0
                singles_stats['games_won'] += set_score[0]
                singles_stats['games_lost'] += set_score[1]
            else:
                singles_stats['sets_won'] += 1 if set_score[1] > set_score[0] else 0
                singles_stats['sets_lost'] += 1 if set_score[1] < set_score[0] else 0
                singles_stats['games_won'] += set_score[1]
                singles_stats['games_lost'] += set_score[0]

    # Calculate doubles statistics
    doubles_stats = {
        'matches_played': doubles_matches.count(),
        'matches_won': doubles_matches.filter(Q(winner1=player) | Q(winner2=player)).count(),
        'sets_won': 0,
        'sets_lost': 0,
        'games_won': 0,
        'games_lost': 0,
    }

    for match in doubles_matches:
        for set_score in match.set_scores:
            if match.winner1 == player or match.winner2 == player:
                doubles_stats['sets_won'] += 1 if set_score[0] > set_score[1] else 0
                doubles_stats['sets_lost'] += 1 if set_score[0] < set_score[1] else 0
                doubles_stats['games_won'] += set_score[0]
                doubles_stats['games_lost'] += set_score[1]
            else:
                doubles_stats['sets_won'] += 1 if set_score[1] > set_score[0] else 0
                doubles_stats['sets_lost'] += 1 if set_score[1] < set_score[0] else 0
                doubles_stats['games_won'] += set_score[1]
                doubles_stats['games_lost'] += set_score[0]

    # Calculate streaks
    singles_current_streak = singles_matches.filter(winner=player).count()
    doubles_current_streak = doubles_matches.filter(Q(winner1=player) | Q(winner2=player)).count()

    # Calculate longest streaks
    singles_longest_streak = calculate_longest_streak(singles_matches, player, is_singles=True)
    doubles_longest_streak = calculate_longest_streak(doubles_matches, player, is_singles=False)

    # Calculate percentages
    singles_match_win_percentage = round((singles_stats['matches_won'] / singles_stats['matches_played'] * 100), 1) if singles_stats['matches_played'] > 0 else 0
    singles_set_win_percentage = round((singles_stats['sets_won'] / (singles_stats['sets_won'] + singles_stats['sets_lost']) * 100), 1) if (singles_stats['sets_won'] + singles_stats['sets_lost']) > 0 else 0
    singles_game_win_percentage = round((singles_stats['games_won'] / (singles_stats['games_won'] + singles_stats['games_lost']) * 100), 1) if (singles_stats['games_won'] + singles_stats['games_lost']) > 0 else 0

    doubles_match_win_percentage = round((doubles_stats['matches_won'] / doubles_stats['matches_played'] * 100), 1) if doubles_stats['matches_played'] > 0 else 0
    doubles_set_win_percentage = round((doubles_stats['sets_won'] / (doubles_stats['sets_won'] + doubles_stats['sets_lost']) * 100), 1) if (doubles_stats['sets_won'] + doubles_stats['sets_lost']) > 0 else 0
    doubles_game_win_percentage = round((doubles_stats['games_won'] / (doubles_stats['games_won'] + doubles_stats['games_lost']) * 100), 1) if (doubles_stats['games_won'] + doubles_stats['games_lost']) > 0 else 0

    context = {
        'player': player,
        'singles_matches': singles_matches,
        'doubles_matches': doubles_matches,
        'elo_history': elo_history,
        'elo_history_doubles': elo_history_doubles,
        'singles_stats': singles_stats,
        'doubles_stats': doubles_stats,
        'singles_match_win_percentage': singles_match_win_percentage,
        'singles_set_win_percentage': singles_set_win_percentage,
        'singles_game_win_percentage': singles_game_win_percentage,
        'singles_matches_played': singles_stats['matches_played'],
        'singles_sets_played': singles_stats['sets_won'] + singles_stats['sets_lost'],
        'singles_games_played': singles_stats['games_won'] + singles_stats['games_lost'],
        'singles_current_streak': singles_current_streak,
        'singles_longest_streak': singles_longest_streak,
        'doubles_match_win_percentage': doubles_match_win_percentage,
        'doubles_set_win_percentage': doubles_set_win_percentage,
        'doubles_game_win_percentage': doubles_game_win_percentage,
        'doubles_matches_played': doubles_stats['matches_played'],
        'doubles_sets_played': doubles_stats['sets_won'] + doubles_stats['sets_lost'],
        'doubles_games_played': doubles_stats['games_won'] + doubles_stats['games_lost'],
        'doubles_current_streak': doubles_current_streak,
        'doubles_longest_streak': doubles_longest_streak,
    }
    return render(request, 'rankings/profile.html', context)

class SignUpView(CreateView):
    form_class = CustomSignUpForm
    success_url = reverse_lazy('home')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        # Save the User instance
        user = form.save(commit=False)
        user.is_approved = False  # Ensure new users require admin approval
        user.backend = 'django.contrib.auth.backends.ModelBackend'  # Set the backend here
        user.save()

        # Ensure a Player instance is created only if one doesn't already exist
        player, created = Player.objects.get_or_create(
            user=user,
            defaults={
                "first_name": form.cleaned_data.get("first_name", ""),
                "last_name": form.cleaned_data.get("last_name", ""),
                "usta_rating": float(form.cleaned_data.get("usta_rating", 3.00)),
                "neighborhood": form.cleaned_data.get("neighborhood", "Other"),
                "phone_number": form.cleaned_data.get("phone_number", ""),
            }
        )

        # Send the welcome email (only if the player was just created)
        if created:
            usta_rating = player.usta_rating
            player.elo_rating = (USTA_TO_UTR.get(usta_rating, 3) * 100)
            player.elo_rating_doubles = (USTA_TO_UTR.get(usta_rating, 3) * 100)
            player.save()  # Save the updated ELO rating

            self.send_welcome_email(user)  # Pass the user object here

        # Don't log the user in if they are pending approval
        if user.is_approved:
            login(self.request, user)

        # Redirect to a custom page indicating that approval is pending
        return redirect('pending_approval')  # Redirect to the pending approval page
    
    def send_welcome_email(self, user):
        from_email = formataddr(("Miami Racket Club", settings.DEFAULT_FROM_EMAIL))
        subject = Header("Your account has been submitted for approval", "utf-8").encode()
        
        # Hosted/static image URL (update if necessary)
        logo_url = "https://miami-racket-club-496610aca6a3.herokuapp.com/static/rankings/logo-color.png"

        # Font URL (import Google Font)
        font_url = "https://fonts.googleapis.com/css2?family=Alegreya:wght@400;700&display=swap"

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

                /* Hidden preview text */
                .preview-text {{
                    display: none;
                    font-size: 0;
                    color: transparent;
                    line-height: 0;
                    max-height: 0;
                    mso-hide: all; /* Hide in Outlook */
                }}
            </style>
        </head>
        <body>
            <!-- Hidden preview text -->
            <span class="preview-text">We shouldn't take long.</span>

            <div class="email-container">
                <div class="email-header">
                    <img src="{logo_url}" alt="Miami Racket Club Logo">
                </div>
                <div class="email-content">
                    <h3>Your Account has been submitted</h3>
                    <p>Hi, {user.first_name}</p>
                    <p>Your account submission has been sent and is now being reviewed.</p>
                </div>
                <div class="footer">
                    <p>See you on court!</p>
                </div>
            </div>
        </body>
        </html>
        '''

        # Send the email
        recipient_list = [user.email, 'vicente.ramirezg@gmail.com']
        send_mail(subject, subject, from_email, recipient_list, html_message=html_message)

# You can use this for login to also handle redirecting users who are not approved
class CustomLoginView(LoginView):
    form_class = AuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        
        # Check if the user is approved
        if user.player.is_approved:
            return super().form_valid(form)  # Allow the login to proceed
        else:
            # Redirect unapproved users to the 'pending_approval' page
            return redirect('pending_approval')

@login_required
@approved_required
def player_directory(request):
    # Get all approved players ordered alphabetically by default
    players = Player.objects.filter(is_approved=True).order_by('first_name', 'last_name')

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

    # Paginate the filtered players
    paginator = Paginator(players, 25)  # Show 25 players per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Clean phone numbers for paginated players
    for player in page_obj:
        player.cleaned_phone = player.phone_number.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')

    # Get unique neighborhoods for the filter dropdown
    unique_neighborhoods = Player.objects.values_list('neighborhood', flat=True).distinct().order_by('neighborhood')

    context = {
        'page_obj': page_obj,  # Pass the paginated players
        'unique_neighborhoods': unique_neighborhoods,
        'selected_neighborhoods': neighborhoods,
        'min_rating': float(min_rating),
        'max_rating': float(max_rating),
    }
    return render(request, 'rankings/player_directory.html', context)

def pending_approval(request):
    return render(request, 'registration/pending_approval.html')

def username_retrieval(request):
    if request.method == 'POST':
        form = UsernameRetrievalForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                send_username_email(user)  # Send the styled email
                return redirect('username_retrieval_done')
            except User.DoesNotExist:
                form.add_error('email', 'No user found with this email address.')
    else:
        form = UsernameRetrievalForm()
    return render(request, 'registration/username_retrieval.html', {'form': form})

def send_username_email(user):
    from_email = formataddr(("Miami Racket Club", settings.DEFAULT_FROM_EMAIL))
    subject = Header("Your Miami Racket Club Username", "utf-8").encode()

    # Hosted/static image URL (update if necessary)
    logo_url = "https://miami-racket-club-496610aca6a3.herokuapp.com/static/rankings/logo-color.png"

    # Font URL (import Google Font)
    font_url = "https://fonts.googleapis.com/css2?family=Alegreya:wght@400;700&display=swap"

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

            /* Hidden preview text */
            .preview-text {{
                display: none;
                font-size: 0;
                color: transparent;
                line-height: 0;
                max-height: 0;
                mso-hide: all; /* Hide in Outlook */
            }}
        </style>
    </head>
    <body>
        <!-- Hidden preview text -->
        <span class="preview-text">Here's your Miami Racket Club username.</span>

        <div class="email-container">
            <div class="email-header">
                <img src="{logo_url}" alt="Miami Racket Club Logo">
            </div>
            <div class="email-content">
                <h3>Miami Racket Club</h3>
                <p>Hi, {user.first_name or 'there'},</p>
                <p>Your username is: <strong>{user.username}</strong></p>
                <p>If you did not request this information, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>See you on court!</p>
            </div>
        </div>
    </body>
    </html>
    '''

    # Send the email
    recipient_list = [user.email]
    send_mail(subject, subject, from_email, recipient_list, html_message=html_message)

def username_retrieval_done(request):
    return render(request, 'registration/username_retrieval_done.html')

class CustomPasswordResetView(PasswordResetView):
    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())  # Remove any newlines
        body = render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name:
            html_email = render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')

        email_message.send()

def faq(request):
    return render(request, 'registration/faq.html')