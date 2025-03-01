# Generated by Django 5.1.5 on 2025-02-05 00:53

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rankings", "0010_player_created_at_player_first_name_player_last_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="submitted_at",
            field=models.DateTimeField(
                auto_now_add=True, default="2025-02-04 15:30:25.123456+00:00"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="match",
            name="submitted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="submitted_matches",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
