# Generated by Django 5.1.5 on 2025-02-03 21:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rankings', '0006_match_notes_alter_match_date_alter_match_set_scores'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='neighborhood',
            field=models.CharField(choices=[('Downtown', 'Downtown'), ('Doral', 'Doral'), ('Palmetto Bay', 'Palmetto Bay'), ('Brickell', 'Brickell'), ('Coconut Grove', 'Coconut Grove'), ('Coral Gables', 'Coral Gables'), ('South Beach', 'South Beach'), ('Pinecrest', 'Pinecrest'), ('South Miami', 'South Miami'), ('Midtown', 'Midtown'), ('Wynwood', 'Wynwood'), ('Key Biscayne', 'Key Biscayne'), ('Edgewater', 'Edgewater'), ('Little Havana', 'Little Havana'), ('Design District', 'Design District'), ('Kendall', 'Kendall'), ('Weston', 'Weston'), ('Fort Lauderdale', 'Fort Lauderdale'), ('Other', 'Other')], default='Other', max_length=50),
        ),
        migrations.AddField(
            model_name='player',
            name='phone_number',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]
