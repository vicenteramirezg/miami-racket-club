from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth.models import User  # Add this import
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from .forms import MatchForm, CustomSignUpForm, UsernameRetrievalForm  # Ensure this import is correct
from .models import Player, Match, ELOHistory
from .decorators import approved_required
from django.contrib.auth.decorators import login_required
from email.header import Header
from email.utils import formataddr
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils.html import strip_tags

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
            send_match_notification(match)  # Send notification
            return redirect('leaderboard')
    else:
        form = MatchForm()
    return render(request, 'rankings/submit_match.html', {'form': form})

@login_required
@approved_required
def leaderboard(request):
    players = Player.objects.order_by('-elo_rating')
    return render(request, 'rankings/leaderboard.html', {'players': players})

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

@approved_required
def home(request):
    # Fetch recent matches that are not soft-deleted
    recent_matches = Match.objects.filter(is_deleted=False).order_by('-date')[:10]  # Adjust the number as needed
    context = {
        'recent_matches': recent_matches,
    }
    return render(request, 'rankings/home.html', context)

@login_required
@approved_required
def profile(request, username):
    player = get_object_or_404(Player, user__username=username)
    matches = Match.objects.filter((Q(winner=player) | Q(loser=player)) & Q(is_deleted=False)).order_by('-date')  # Order by date (most recent first)
    matches = matches.order_by('-date')  # Show most recent matches first

    # Fetch ELO history and ensure only the latest entry for each submitted_at date is included
    elo_history = player.elo_history.order_by('submitted_at')

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
    elo_history = player.elo_history.order_by('submitted_at')

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
                "usta_rating": form.cleaned_data.get("usta_rating", 3.00),
                "neighborhood": form.cleaned_data.get("neighborhood", "Other"),
                "phone_number": form.cleaned_data.get("phone_number", ""),
            }
        )

        # Send the welcome email (only if the player was just created)
        if created:
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
    # Get all players ordered alphabetically by default
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