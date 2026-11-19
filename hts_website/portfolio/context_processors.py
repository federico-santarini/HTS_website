from django.conf import settings


def publication(request):
    """Rende PUBLICATION_URL (link in navbar, base.html, e cerchio della home) e CONTACT_EMAIL (colophon di about.html)
    disponibili in tutti i template.

    Registrato in settings.TEMPLATES. Se una variabile non è impostata, la voce che la usa non compare.
    """
    return {"PUBLICATION_URL": settings.PUBLICATION_URL, "CONTACT_EMAIL": settings.CONTACT_EMAIL}
