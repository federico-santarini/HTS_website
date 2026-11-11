from django.db import migrations


def fix_typo(apps, schema_editor):
    """I progetti salvati con il vecchio valore "cogniton" (refuso) passano a "cognition"."""
    Project = apps.get_model("portfolio", "Project")
    Project.objects.filter(project_category="cogniton").update(project_category="cognition")


def restore_typo(apps, schema_editor):
    """Al contrario (migrate indietro): "cognition" torna "cogniton", il valore che il modello aveva allora."""
    Project = apps.get_model("portfolio", "Project")
    Project.objects.filter(project_category="cognition").update(project_category="cogniton")


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0020_project_category_cognition"),
    ]

    operations = [
        migrations.RunPython(fix_typo, restore_typo),
    ]
