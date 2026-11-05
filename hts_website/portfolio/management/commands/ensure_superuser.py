import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Crea il superuser dai valori nell'ambiente (DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD, "
        "DJANGO_SUPERUSER_EMAIL facoltativa) se non esiste ancora. Se esiste non fa nulla: non cambia la password. "
        "Serve online, dove non c'è una finestra di terminale: gira a ogni deploy, subito dopo migrate."
    )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD non impostate: niente da creare.")
            return
        User = get_user_model()
        if User.objects.filter(**{User.USERNAME_FIELD: username}).exists():
            self.stdout.write(f"Il superuser '{username}' esiste già: lasciato com'è.")
            return
        User.objects.create_superuser(username, os.environ.get("DJANGO_SUPERUSER_EMAIL", ""), password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' creato."))
