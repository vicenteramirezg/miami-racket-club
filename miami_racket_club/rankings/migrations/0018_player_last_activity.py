# Generated by Django 5.1.5 on 2025-02-12 17:03

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rankings', '0017_elohistory_is_valid_match_is_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='last_activity',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
