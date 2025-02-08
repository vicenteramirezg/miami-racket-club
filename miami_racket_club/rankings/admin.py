from django.contrib import admin
from .models import Player, Match

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_approved')  # Use 'is_approved' instead of 'approved'
    list_filter = ('is_approved',)  # Use 'is_approved' here too
    actions = ['approve_players']

    def approve_players(self, request, queryset):
        queryset.update(is_approved=True)
    approve_players.short_description = "Approve selected players"

admin.site.register(Player, PlayerAdmin)
admin.site.register(Match)
