from django.conf import settings
from django.http import HttpResponseNotFound
from whitenoise import WhiteNoise
from whitenoise.middleware import WhiteNoiseMiddleware


class PublicationMiddleware:
    """Serve la pubblicazione statica sul sottodominio dedicato.

    Se la richiesta arriva da <PUBLICATION_SUBDOMAIN>.qualcosa (in produzione es.
    publication.tuodominio.it, in locale publication.localhost:8000) risponde con i file
    della cartella PUBLICATION_DIR, e con 404 per qualsiasi altro percorso: su quel
    sottodominio il sito Django (compreso /admin/) non è raggiungibile.

    Per gli altri host non fa nulla e passa la richiesta alle view normali.

    Posizione in MIDDLEWARE: subito dopo WhiteNoise e prima di sessioni e CSRF,
    che per dei file statici non servono.

    I file li gestisce WhiteNoise (index.html nelle cartelle, content-type, cache,
    protezione dai percorsi tipo ../). Con DEBUG=True il disco viene riletto a ogni
    richiesta, quindi le modifiche si vedono subito; con DEBUG=False l'elenco dei file
    è costruito all'avvio, e dopo una modifica serve un nuovo deploy.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.publication = WhiteNoise(
            None,
            autorefresh=settings.DEBUG,
            max_age=0 if settings.DEBUG else 60,
            index_file=True,
        )
        self.publication.add_files(settings.PUBLICATION_DIR)

    def __call__(self, request):
        # Primo pezzo dell'host: "publication.localhost:8000" -> "publication".
        # get_host() controlla anche ALLOWED_HOSTS (quando sarà ristretto, includere il sottodominio).
        if request.get_host().split(".")[0] != settings.PUBLICATION_SUBDOMAIN:
            return self.get_response(request)

        if self.publication.autorefresh:
            static_file = self.publication.find_file(request.path_info)
        else:
            static_file = self.publication.files.get(request.path_info)
        if static_file is None:
            return HttpResponseNotFound("Not found")
        return WhiteNoiseMiddleware.serve(static_file, request)
