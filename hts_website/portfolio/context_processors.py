from django.conf import settings


def publication(request):
    """Rende PUBLICATION_URL disponibile in tutti i template (serve al link in navbar, base.html).

    Registrato in settings.TEMPLATES. Se la variabile non è impostata il link non compare.
    """
    return {"PUBLICATION_URL": settings.PUBLICATION_URL}
