from django.apps import AppConfig
from django.db.models.signals import post_migrate

# Modelli che gli autori possono gestire dall'admin (tutto tranne utenti, gruppi e impostazioni del sito).
AUTHOR_MODELS = ["project", "projectimage", "projecttype", "contributor", "contributorimage", "event", "reference"]


def ensure_authors_group(sender, **kwargs):
    """Dopo ogni migrate: il gruppo "Authors" esiste e ha i permessi sui contenuti (aggiungere, modificare, cancellare, vedere).

    Si ricrea da solo su qualsiasi database (anche quello online, appena creato). Aggiunge i permessi che mancano ma non
    ne toglie: eventuali modifiche fatte a mano dall'admin al gruppo restano. Un nuovo modello di contenuto va aggiunto
    a AUTHOR_MODELS. Un autore è un utente con "Staff status" acceso e il gruppo Authors: mai superuser.
    """
    from django.contrib.auth.models import Group, Permission

    codenames = [f"{action}_{model}" for model in AUTHOR_MODELS for action in ("add", "change", "delete", "view")]
    permissions = Permission.objects.filter(content_type__app_label="portfolio", codename__in=codenames)
    group, _ = Group.objects.get_or_create(name="Authors")
    group.permissions.add(*permissions)


class PortfolioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portfolio"

    def ready(self):
        # Il gestore dei permessi di Django (app auth) si collega a post_migrate prima del nostro: quando tocca a noi i permessi esistono già.
        post_migrate.connect(ensure_authors_group, sender=self)
