from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from email.utils import formataddr
from email.header import Header
from .models import Player, Match

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_approved', 'user__first_name', 'user__last_name')
    list_filter = ('is_approved',)
    actions = ['approve_players']

    def approve_players(self, request, queryset):
        for player in queryset:
            player.is_approved = True
            player.save()  # Save the player first

            # Manually refresh the player object after saving to ensure it's up to date
            player.refresh_from_db()

            # Send email to the user when approved
            self.send_approval_email(player.user)

        self.message_user(request, "Selected players have been approved and notified.")

    approve_players.short_description = "Approve selected players"

    def send_approval_email(self, user):
        from_email = formataddr(("Miami Racket Club", settings.DEFAULT_FROM_EMAIL))
        subject = Header("Your account has been approved", "utf-8").encode()
        
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
            <span class="preview-text">Welcome to MRC Rankings.</span>

            <div class="email-container">
                <div class="email-header">
                    <img src="{logo_url}" alt="Miami Racket Club Logo">
                </div>
                <div class="email-content">
                    <h3>Your Account Has Been Approved</h3>
                    <p>Congratulations {user.first_name}! 🎉</p>
                    <p>Your account at MRC Rankings has been approved. You now have access to all the features of the app.</p>
                    <p>We look forward to seeing you on the court!</p>
                    <p style="text-align: center;">
                        <a href="{settings.SITE_URL}/profile/{user.username}" class="profile-button">View Your Profile</a>
                    </p>
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

admin.site.register(Player, PlayerAdmin)
admin.site.register(Match)