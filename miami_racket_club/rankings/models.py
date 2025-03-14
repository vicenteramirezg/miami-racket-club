from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from .utils import calculate_dominance_factor, adjust_k_factor
import json

# Define valid set scores
VALID_SET_SCORES = [
    (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (7, 5), (7, 6),
    (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 7), (6, 7)
]

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
        ('Fort Lauderdale', 'Fort Lauderdale'),
        ('Shenandoah', 'Shenandoah')
    ], key=lambda x: x[1])
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    usta_rating = models.FloatField(default=3.00)
    elo_rating = models.IntegerField(default=1000)
    elo_rating_doubles = models.IntegerField(default=1000)
    neighborhood = models.CharField(max_length=50, choices=NEIGHBORHOOD_CHOICES, default='Other')
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # US phone numbers only
    created_at = models.DateTimeField(default=timezone.now)  # Automatically set when the player is created
    is_approved = models.BooleanField(default=False)  # Tracks admin approval
    last_activity = models.DateTimeField(default=timezone.now)

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
        return f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else f"{self.user.username}"

class Match(models.Model):
    winner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="won_matches")
    loser = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="lost_matches")
    winner_elo_before = models.IntegerField(null=True, blank=True)
    loser_elo_before = models.IntegerField(null=True, blank=True)
    winner_elo_after = models.IntegerField(null=True, blank=True)
    loser_elo_after = models.IntegerField(null=True, blank=True)
    set_scores = models.JSONField()
    date = models.DateField(auto_now_add=False)  # Allow custom dates
    notes = models.TextField(blank=True, null=True)  # Optional notes

    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_matches")
    submitted_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the match is submitted

    is_deleted = models.BooleanField(default=False)  # Soft delete field

    def soft_delete(self):
        self.is_deleted = True
        self.save()

    def __str__(self):
        return f"{self.winner} vs {self.loser} ({self.clean_score()})"
    
    def clean_score(self):
        """Formats set_scores into a readable string like '6-1 4-6 6-0'."""
        return "  ".join(f"{set_score[0]}-{set_score[1]}" for set_score in self.set_scores)
    
    def save(self, *args, **kwargs):
        """
        Saves the match and calculates ELO ratings unless skip_validation or skip_elo_calculation is True.
        """
        skip_validation = kwargs.pop('skip_validation', False)  # Skip validation if True
        skip_elo_calculation = kwargs.pop('skip_elo_calculation', False)  # Skip ELO calculation if True

        with transaction.atomic():
            if not skip_validation:
                if self.date > timezone.now().date():
                    raise ValidationError("The match date cannot be in the future.")
                
                if self.winner == self.loser:
                    raise ValidationError("The winner and loser cannot be the same player.")
                
                for index, set_score in enumerate(self.set_scores):
                    if index == 2 and set_score == (1, 0):  # Allow (1,0) only for the third set
                        continue
                    if set_score not in VALID_SET_SCORES:
                        raise ValidationError(f"Invalid set score: {set_score}. Valid scores are: {VALID_SET_SCORES}.")
                
                winner_sets = sum(1 for w, l in self.set_scores if w > l)
                loser_sets = len(self.set_scores) - winner_sets

                if winner_sets <= loser_sets:
                    raise ValidationError("The winner must win more sets than the loser.")
                elif winner_sets == loser_sets:
                    raise ValidationError("The match cannot end in a tie. One player must win more sets than the other.")

            if not skip_elo_calculation:
                # Capture ELO ratings before the match
                self.winner_elo_before = self.winner.elo_rating
                self.loser_elo_before = self.loser.elo_rating

                # Calculate dominance factor
                dominance_factor = calculate_dominance_factor(self.set_scores)

                # Base K-factor
                base_k = 32

                # Adjust K-factor based on dominance
                adjusted_k = adjust_k_factor(base_k, dominance_factor)

                # Calculate new ELO ratings
                winner_rating = self.winner.elo_rating
                loser_rating = self.loser.elo_rating

                # Expected scores
                expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
                expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))

                # New ratings
                new_winner_rating = round(winner_rating + adjusted_k * (1 - expected_winner))
                new_loser_rating = round(loser_rating + adjusted_k * (0 - expected_loser))

                # Update player ratings
                self.winner.elo_rating = new_winner_rating
                self.loser.elo_rating = new_loser_rating

                # Capture ELO ratings after the match
                self.winner_elo_after = new_winner_rating
                self.loser_elo_after = new_loser_rating

                # Update the last_activity field for both players
                self.winner.last_activity = timezone.now()
                self.loser.last_activity = timezone.now()

                # Save the updated player ratings to the database
                self.winner.save()
                self.loser.save()

            # Save the match
            super().save(*args, **kwargs)

            if not skip_elo_calculation:
                # Log ELO changes using the match date
                match_datetime = timezone.make_aware(timezone.datetime.combine(self.date, timezone.datetime.min.time()))
                
                # Creating ELOHistory and linking to the match
                ELOHistory.objects.create(player=self.winner, elo_rating=new_winner_rating, date=match_datetime, match=self, is_valid=True)
                ELOHistory.objects.create(player=self.loser, elo_rating=new_loser_rating, date=match_datetime, match=self, is_valid=True)

    def revert_match(self):
        """
        Reverts the match by restoring the ELO ratings of the winner and loser
        and soft-deleting the match.
        """
        with transaction.atomic():
            print(f"Before Reversion - Winner ELO: {self.winner.elo_rating}, Loser ELO: {self.loser.elo_rating}")  # Debug
            print(f"Reverting to - Winner ELO Before: {self.winner_elo_before}, Loser ELO Before: {self.loser_elo_before}")  # Debug

            # Revert ELO ratings
            self.winner.elo_rating = self.winner_elo_before
            self.loser.elo_rating = self.loser_elo_before

            # Save the updated player ratings
            self.winner.save()
            self.loser.save()

            print(f"After Reversion - Winner ELO: {self.winner.elo_rating}, Loser ELO: {self.loser.elo_rating}")  # Debug

            # Soft delete the match
            self.is_deleted = True

            # Save the match without validation or ELO calculation
            self.save(skip_validation=True, skip_elo_calculation=True)

            # Mark the corresponding EloHistory entries as invalid
            ELOHistory.objects.filter(match=self).update(is_valid=False)

class ELOHistory(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='elo_history')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='elo_history')  # Link to Match
    elo_rating = models.IntegerField()
    date = models.DateTimeField()  # Match date (not auto-updating)
    submitted_at = models.DateTimeField(default=timezone.now)  # Track when the log was recorded
    is_valid = models.BooleanField(default=True)  # Add this field

    def __str__(self):
        return f"{self.player.user.username} - {self.elo_rating} on {self.date}"

class MatchDoubles(models.Model):
    winner1 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="won_doubles_matches1")
    winner2 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="won_doubles_matches2")
    loser1 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="lost_doubles_matches1")
    loser2 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="lost_doubles_matches2")

    winner1_elo_before = models.IntegerField(null=True, blank=True)
    winner2_elo_before = models.IntegerField(null=True, blank=True)
    loser1_elo_before = models.IntegerField(null=True, blank=True)
    loser2_elo_before = models.IntegerField(null=True, blank=True)

    winner1_elo_after = models.IntegerField(null=True, blank=True)
    winner2_elo_after = models.IntegerField(null=True, blank=True)
    loser1_elo_after = models.IntegerField(null=True, blank=True)
    loser2_elo_after = models.IntegerField(null=True, blank=True)

    set_scores = models.JSONField()
    date = models.DateField(auto_now_add=False)
    notes = models.TextField(blank=True, null=True)

    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_doubles_matches")
    submitted_at = models.DateTimeField(auto_now_add=True)

    is_deleted = models.BooleanField(default=False)

    def soft_delete(self):
        self.is_deleted = True
        self.save()

    def __str__(self):
        return f"{self.winner1} & {self.winner2} vs {self.loser1} & {self.loser2} ({self.clean_score()})"
    
    def clean_score(self):
        """Formats set_scores into a readable string like '6-1 4-6 6-0'."""
        return "  ".join(f"{set_score[0]}-{set_score[1]}" for set_score in self.set_scores)
    
    def save(self, *args, **kwargs):
        """
        Saves the match and calculates ELO ratings unless skip_validation or skip_elo_calculation is True.
        """
        skip_validation = kwargs.pop('skip_validation', False)
        skip_elo_calculation = kwargs.pop('skip_elo_calculation', False)

        with transaction.atomic():
            if not skip_validation:
                if self.date > timezone.now().date():
                    raise ValidationError("The match date cannot be in the future.")
                if self.winner1 == self.loser1 or self.winner2 == self.loser2:  # Check if any player is the same
                    raise ValidationError("The winner and loser cannot be the same player.")
                
                for set_score in self.set_scores:
                    if set_score not in VALID_SET_SCORES:
                        raise ValidationError(f"Invalid set score: {set_score}. Valid scores are: {VALID_SET_SCORES}.")
                
                winner_sets = 0
                loser_sets = 0
                for set_score in self.set_scores:
                    if set_score[0] > set_score[1]:
                        winner_sets += 1
                    else:
                        loser_sets += 1

                if winner_sets <= loser_sets:
                    raise ValidationError("The winners must win more sets than the losers.")
                elif winner_sets == loser_sets:
                    raise ValidationError("The match cannot end in a tie. One team must win more sets than the other.")

            if not skip_elo_calculation:
                # Capture ELO ratings before the match
                self.winner1_elo_before = self.winner1.elo_rating_doubles
                self.winner2_elo_before = self.winner2.elo_rating_doubles
                self.loser1_elo_before = self.loser1.elo_rating_doubles
                self.loser2_elo_before = self.loser2.elo_rating_doubles

                # Calculate dominance factor
                dominance_factor = calculate_dominance_factor(self.set_scores)

                # Base K-factor
                base_k = 32

                # Adjust K-factor based on dominance
                adjusted_k = adjust_k_factor(base_k, dominance_factor)

                # Calculate new ELO ratings for doubles
                winner_team_rating = (self.winner1.elo_rating_doubles + self.winner2.elo_rating_doubles) / 2
                loser_team_rating = (self.loser1.elo_rating_doubles + self.loser2.elo_rating_doubles) / 2

                # Expected scores
                expected_winners = 1 / (1 + 10 ** ((loser_team_rating - winner_team_rating) / 400))
                expected_losers = 1 - expected_winners

                # New ratings for both winners and losers
                new_winner1_rating = round(self.winner1.elo_rating_doubles + adjusted_k * (1 - expected_winners))
                new_winner2_rating = round(self.winner2.elo_rating_doubles + adjusted_k * (1 - expected_winners))
                new_loser1_rating = round(self.loser1.elo_rating_doubles + adjusted_k * (0 - expected_losers))
                new_loser2_rating = round(self.loser2.elo_rating_doubles + adjusted_k * (0 - expected_losers))

                # Update player ratings
                self.winner1.elo_rating_doubles = new_winner1_rating
                self.winner2.elo_rating_doubles = new_winner2_rating
                self.loser1.elo_rating_doubles = new_loser1_rating
                self.loser2.elo_rating_doubles = new_loser2_rating

                # Capture ELO ratings after the match
                self.winner1_elo_after = new_winner1_rating
                self.winner2_elo_after = new_winner2_rating
                self.loser1_elo_after = new_loser1_rating
                self.loser2_elo_after = new_loser2_rating

                # Update the last_activity field for all players
                self.winner1.last_activity = timezone.now()
                self.winner2.last_activity = timezone.now()
                self.loser1.last_activity = timezone.now()
                self.loser2.last_activity = timezone.now()

                # Save the updated player ratings
                self.winner1.save()
                self.winner2.save()
                self.loser1.save()
                self.loser2.save()

            # Save the match
            super().save(*args, **kwargs)

            if not skip_elo_calculation:
                # Log ELO changes using the match date
                match_datetime = timezone.make_aware(timezone.datetime.combine(self.date, timezone.datetime.min.time()))
                
                # Creating ELOHistory and linking to the match
                ELOHistoryDoubles.objects.create(player=self.winner1, elo_rating_doubles=new_winner1_rating, date=match_datetime, match=self, is_valid=True)
                ELOHistoryDoubles.objects.create(player=self.winner2, elo_rating_doubles=new_winner2_rating, date=match_datetime, match=self, is_valid=True)
                ELOHistoryDoubles.objects.create(player=self.loser1, elo_rating_doubles=new_loser1_rating, date=match_datetime, match=self, is_valid=True)
                ELOHistoryDoubles.objects.create(player=self.loser2, elo_rating_doubles=new_loser2_rating, date=match_datetime, match=self, is_valid=True)

    def revert_match(self):
        """
        Reverts the match by restoring the ELO ratings of the winners and losers
        and soft-deleting the match.
        """
        with transaction.atomic():
            print(f"Before Reversion - Winner1 ELO: {self.winner1.elo_rating_doubles}, Winner2 ELO: {self.winner2.elo_rating_doubles}, "
                f"Loser1 ELO: {self.loser1.elo_rating_doubles}, Loser2 ELO: {self.loser2.elo_rating_doubles}")  # Debugging

            print(f"Reverting to - Winner1 ELO Before: {self.winner1_elo_before}, Winner2 ELO Before: {self.winner2_elo_before}, "
                f"Loser1 ELO Before: {self.loser1_elo_before}, Loser2 ELO Before: {self.loser2_elo_before}")  # Debugging

            # Revert ELO ratings
            self.winner1.elo_rating_doubles = self.winner1_elo_before
            self.winner2.elo_rating_doubles = self.winner2_elo_before
            self.loser1.elo_rating_doubles = self.loser1_elo_before
            self.loser2.elo_rating_doubles = self.loser2_elo_before

            # Save the updated player ratings
            self.winner1.save()
            self.winner2.save()
            self.loser1.save()
            self.loser2.save()

            print(f"After Reversion - Winner1 ELO: {self.winner1.elo_rating_doubles}, Winner2 ELO: {self.winner2.elo_rating_doubles}, "
                f"Loser1 ELO: {self.loser1.elo_rating_doubles}, Loser2 ELO: {self.loser2.elo_rating_doubles}")  # Debugging

            # Soft delete the match
            self.is_deleted = True

            # Save the match without validation or ELO calculation
            self.save(skip_validation=True, skip_elo_calculation=True)

            # Mark the corresponding EloHistoryDoubles entries as invalid
            ELOHistoryDoubles.objects.filter(match=self).update(is_valid=False)

class ELOHistoryDoubles(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='elo_history_doubles')
    match = models.ForeignKey(MatchDoubles, on_delete=models.CASCADE, related_name='elo_history_doubles')  # Link to MatchDoubles
    elo_rating_doubles = models.IntegerField()  # Correct field name
    date = models.DateTimeField(default=timezone.now)  # Match date (not auto-updating)
    submitted_at = models.DateTimeField(default=timezone.now)  # Track when the log was recorded
    is_valid = models.BooleanField(default=True)  # Validity of this entry

    def __str__(self):
        return f"{self.player.user.username} - {self.elo_rating_doubles} on {self.date}"