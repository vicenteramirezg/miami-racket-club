from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
import json

class Player(models.Model):
    NEIGHBORHOOD_CHOICES = sorted([
        ('Downtown', 'Downtown'),
        ('Doral', 'Doral'),
        ('Palmetto Bay', 'Palmetto Bay'),
        ('Brickell', 'Brickell'),
        ('Coconut Grove', 'Coconut Grove'),
        ('Coral Gables', 'Coral Gables'),
        ('Miami Beach', 'Miami Beach'),
        ('Pinecrest', 'Pinecrest'),
        ('Morningside', 'Morningside'),
        ('South Miami', 'South Miami'),
        ('Midtown', 'Midtown'),
        ('Wynwood', 'Wynwood'),
        ('Key Biscayne', 'Key Biscayne'),
        ('Edgewater', 'Edgewater'),
        ('Little Havana', 'Little Havana'),
        ('Design District', 'Design District'),
        ('Kendall', 'Kendall'),
        ('Weston', 'Weston'),
        ('Fort Lauderdale', 'Fort Lauderdale')
    ], key=lambda x: x[1])
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    usta_rating = models.FloatField(default=3.00)
    elo_rating = models.IntegerField(default=1000)
    neighborhood = models.CharField(max_length=50, choices=NEIGHBORHOOD_CHOICES, default='Other')
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # US phone numbers only
    created_at = models.DateTimeField(default=timezone.now)  # Automatically set when the player is created

    def matches_played(self):
        return self.matches_as_winner.count() + self.matches_as_loser.count()

    def matches_won(self):
        return self.matches_as_winner.count()

    def sets_won(self):
        return sum(match.sets_won for match in self.matches_as_winner.all()) + \
               sum(match.sets_lost for match in self.matches_as_loser.all())

    def sets_lost(self):
        return sum(match.sets_lost for match in self.matches_as_winner.all()) + \
               sum(match.sets_won for match in self.matches_as_loser.all())

    def games_won(self):
        return sum(match.games_won for match in self.matches_as_winner.all()) + \
               sum(match.games_lost for match in self.matches_as_loser.all())

    def games_lost(self):
        return sum(match.games_lost for match in self.matches_as_winner.all()) + \
               sum(match.games_won for match in self.matches_as_loser.all())
    
    def save(self, *args, **kwargs):
        # Sync first_name and last_name with the User model
        self.user.first_name = self.first_name
        self.user.last_name = self.last_name
        self.user.last_name = self.last_name
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else self.user.username

class Match(models.Model):
    winner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="won_matches")
    loser = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="lost_matches")
    set_scores = models.JSONField()
    date = models.DateField(auto_now_add=False)  # Allow custom dates
    notes = models.TextField(blank=True, null=True)  # Optional notes

    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_matches")
    submitted_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the match is submitted

    def __str__(self):
        return f"{self.winner} vs {self.loser} ({self.set_scores})"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Validate set scores
            winner_sets = 0
            loser_sets = 0
            for set_score in self.set_scores:
                if set_score[0] > set_score[1]:
                    winner_sets += 1
                else:
                    loser_sets += 1

            if winner_sets <= loser_sets:
                raise ValueError("The winner must win more sets than the loser.")

            # Calculate new ELO ratings
            winner_rating = self.winner.elo_rating
            loser_rating = self.loser.elo_rating

            # Expected scores
            expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
            expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))

            # K-factor (adjustable)
            K = 32

            # New ratings
            new_winner_rating = winner_rating + K * (1 - expected_winner)
            new_loser_rating = loser_rating + K * (0 - expected_loser)

            # Update player ratings
            self.winner.elo_rating = new_winner_rating
            self.loser.elo_rating = new_loser_rating

            # Save the updated player ratings to the database
            self.winner.save()
            self.loser.save()

            # Save the match
            super().save(*args, **kwargs)

            # Log ELO changes using the match date
            match_datetime = timezone.make_aware(timezone.datetime.combine(self.date, timezone.datetime.min.time()))
            
            # Creating ELOHistory and linking to the match
            ELOHistory.objects.create(player=self.winner, elo_rating=new_winner_rating, date=match_datetime, match=self)
            ELOHistory.objects.create(player=self.loser, elo_rating=new_loser_rating, date=match_datetime, match=self)

            

class ELOHistory(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='elo_history')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='elo_history')  # Link to Match
    elo_rating = models.IntegerField()
    date = models.DateTimeField()  # Match date (not auto-updating)
    submitted_at = models.DateTimeField(default=timezone.now)  # Track when the log was recorded

    def __str__(self):
        return f"{self.player.user.username} - {self.elo_rating} on {self.date}"