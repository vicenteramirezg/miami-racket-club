from django.contrib import admin
from .models import Player, Match

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('user__first_name', 'user__last_name', 'user', 'is_approved')  # Added first_name and last_name
    list_filter = ('is_approved',)
    actions = ['approve_players']

    def approve_players(self, request, queryset):
        queryset.update(is_approved=True)
    approve_players.short_description = "Approve selected players"

admin.site.register(Player, PlayerAdmin)
admin.site.register(Match)