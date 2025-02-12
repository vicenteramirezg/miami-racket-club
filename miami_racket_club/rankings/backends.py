from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from rankings.models import Player  # Import your Player model

User = get_user_model()

class ApprovedUserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Perform a case-insensitive lookup for the username
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        try:
            # Case-insensitive lookup for the username
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            # Run the default password hasher to prevent timing attacks
            User().set_password(password)
            return None

        # Check the password (case-sensitive)
        if not user.check_password(password):
            return None

        # Check if the user exists and if the associated Player instance is approved
        try:
            player = user.player  # Get the Player instance associated with the user
            if not player.is_approved:
                # If not approved, return None to deny login
                return None
        except Player.DoesNotExist:
            # In case the user does not have an associated Player, deny login
            return None

        return user

    def get_user(self, user_id):
        """
        This method ensures the custom logic applies when fetching the user.
        """
        user = super().get_user(user_id)
        if user and hasattr(user, 'player') and not user.player.is_approved:
            return None  # Deny non-approved users at this point as well.
        return user