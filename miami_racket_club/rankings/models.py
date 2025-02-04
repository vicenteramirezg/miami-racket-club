from django.db import models
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
    usta_rating = models.FloatField(default=3.00)
    elo_rating = models.IntegerField(default=1000)
    neighborhood = models.CharField(max_length=50, choices=NEIGHBORHOOD_CHOICES, default='Other')
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # US phone numbers only

    def __str__(self):
        return self.user.username

class Match(models.Model):
    winner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="won_matches")
    loser = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="lost_matches")
    set_scores = models.JSONField()
    date = models.DateField(auto_now_add=False)  # Allow custom dates
    notes = models.TextField(blank=True, null=True)  # Optional notes

    def __str__(self):
        return f"{self.winner} vs {self.loser} ({self.set_scores})"

    def save(self, *args, **kwargs):
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

        # Log ELO changes using the match date
        match_datetime = timezone.make_aware(timezone.datetime.combine(self.date, timezone.datetime.min.time()))
        ELOHistory.objects.create(player=self.winner, elo_rating=new_winner_rating, date=match_datetime)
        ELOHistory.objects.create(player=self.loser, elo_rating=new_loser_rating, date=match_datetime)

        # Save the match
        super().save(*args, **kwargs)

class ELOHistory(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='elo_history')
    elo_rating = models.IntegerField()
    date = models.DateTimeField()  # Remove auto_now_add=True

    def __str__(self):
        return f"{self.player.user.username} - {self.elo_rating} on {self.date}"