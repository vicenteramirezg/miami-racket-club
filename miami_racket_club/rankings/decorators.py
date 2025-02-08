from django.shortcuts import redirect
from rankings.models import Player

def approved_required(view_func):
    """
    Decorator to require approval before accessing a view.
    """
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            try:
                player = user.player  # Access the associated Player object
                if not player.is_approved:
                    # If the user is not approved, redirect to the pending approval page
                    return redirect('pending_approval')
            except Player.DoesNotExist:
                # If the user does not have an associated Player, deny access
                return redirect('pending_approval')
        return view_func(request, *args, **kwargs)

    return _wrapped_view
