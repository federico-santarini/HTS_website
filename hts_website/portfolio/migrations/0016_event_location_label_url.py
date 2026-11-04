from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0015_contributor_short_bio"),
    ]

    operations = [
        # RenameField (non remove + add) conserva il testo già inserito: diventa la label.
        migrations.RenameField(
            model_name="event",
            old_name="location",
            new_name="location_label",
        ),
        migrations.AddField(
            model_name="event",
            name="location_url",
            field=models.URLField(blank=True),
        ),
    ]
