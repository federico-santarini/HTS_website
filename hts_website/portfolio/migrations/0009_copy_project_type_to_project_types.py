"""
Migration dei dati (scritta a mano): passa da Project.project_type (testo a scelte fisse)
a Project.project_types (many-to-many verso ProjectType).

Fa parte di una sequenza in tre passi, tenuti in file separati perché mescolare modifiche
allo schema e ai dati nella stessa migration può dare errori su Postgres:
  0008  crea ProjectType e il nuovo campo project_types
  0009  (questo file) copia il vecchio valore di ogni progetto nel nuovo campo
  0010  elimina il vecchio campo project_type

restore_types serve per tornare indietro (migrate portfolio 0008): ripristina solo la
prima tipologia di ogni progetto, perché il vecchio campo ne poteva contenere una sola.
"""
from django.db import migrations

# Le due tipologie che esistevano come scelte fisse: slug del vecchio campo -> nome.
OLD_TYPES = {
    "radio_show": "radio show",
    "event": "event",
}


def copy_types(apps, schema_editor):
    Project = apps.get_model("portfolio", "Project")
    ProjectType = apps.get_model("portfolio", "ProjectType")

    for slug, name in OLD_TYPES.items():
        ProjectType.objects.get_or_create(slug=slug, defaults={"name": name})

    for project in Project.objects.all():
        project_type = ProjectType.objects.get(slug=project.project_type)
        project.project_types.add(project_type)


def restore_types(apps, schema_editor):
    Project = apps.get_model("portfolio", "Project")

    for project in Project.objects.all():
        first_type = project.project_types.first()
        if first_type and first_type.slug in OLD_TYPES:
            project.project_type = first_type.slug
            project.save(update_fields=["project_type"])


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0008_projecttype_and_project_types"),
    ]

    operations = [
        migrations.RunPython(copy_types, restore_types),
    ]
