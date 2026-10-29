"""
Modelli del portfolio e relazioni tra loro (schema completo nel README):

- Project <-> Contributor: M2M, si modifica dall'admin del progetto.
- Project <-> ProjectType: M2M, le tipologie le crea l'admin.
- Project <-> Reference: M2M, si modifica dall'admin della referenza.
- ProjectImage / ContributorImage: immagini multiple, ForeignKey con related_name="images".
- Event: indipendente, nessuna relazione con gli altri modelli.
"""
from django.db import models
from django.utils import timezone

from . import embeds


class ProjectType(models.Model):
    """Tipologia di progetto (es. "event", "radio show"), creata dall'admin.

    Sostituisce il vecchio campo Project.project_type a scelte fisse.
    Lo slug è il valore usato nell'indirizzo del filtro dell'archivio (?type=<slug>).
    Una tipologia in uso non si può cancellare dall'admin: vedi ProjectTypeAdmin.
    """

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    """Un progetto del collettivo (evento, puntata radio, ecc.). Compare in Archive e nel feed."""

    # I valori salvati nel database sono quelli a sinistra: se cambi un valore
    # servirà una data migration per aggiornare i progetti già salvati.
    CATEGORIES = [
        ("cogniton", "cogniton"),
        ("perception", "perception"),
        ("relationality", "relationality"),
    ]

    title = models.CharField(max_length=255)
    date = models.DateField(default=timezone.localdate)
    # Una o più tipologie. Dalla tipologia si risale ai progetti con project_type.projects.
    project_types = models.ManyToManyField(ProjectType, related_name="projects", blank=True)
    # Non è usata nelle pagine pubbliche (filtro e colonna tolti dall'archivio): tenuta per usi futuri.
    project_category = models.CharField(max_length=255, choices=CATEGORIES, default=CATEGORIES[0][0])
    project_url = models.URLField(blank=True, null=True)
    description = models.TextField()
    # Si incolla il link normale (quello della barra del browser o di "Condividi"): l'indirizzo
    # di embed lo ricava portfolio/embeds.py, che accetta solo YouTube e SoundCloud.
    youtube_url = models.URLField(
        blank=True,
        validators=[embeds.validate_youtube_url],
        help_text="Link of a YouTube video, e.g. https://www.youtube.com/watch?v=… It is shown as an embedded player.",
    )
    soundcloud_url = models.URLField(
        blank=True,
        validators=[embeds.validate_soundcloud_url],
        help_text="Link of a SoundCloud track or playlist, e.g. https://soundcloud.com/artist/track. It is shown as an embedded player.",
    )
    # Dal contributor si risale ai progetti con contributor.projects.
    contributors = models.ManyToManyField("Contributor", related_name="projects", blank=True)


    def __str__(self):
        return self.title

    @property
    def youtube_embed_url(self):
        """Indirizzo per l'<iframe> di YouTube, o None se il campo è vuoto."""
        return embeds.youtube_embed_url(self.youtube_url)

    @property
    def soundcloud_embed_url(self):
        """Indirizzo per l'<iframe> di SoundCloud, o None se il campo è vuoto."""
        return embeds.soundcloud_embed_url(self.soundcloud_url)


class Contributor(models.Model):
    """Persona che partecipa ai progetti. Nell'admin mostra (in sola lettura) i suoi progetti."""

    name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255)
    affiliation = models.CharField(max_length=255,blank=True, null=True)
    bio = models.TextField()

    def __str__(self):
        return f"{self.name} {self.surname}"



class ProjectImage(models.Model):
    """Una riga per immagine, così un progetto può averne quante vuole (project.images.all)."""

    project = models.ForeignKey(Project, related_name="images", on_delete=models.CASCADE)
    # width_field/height_field: Django salva da solo le dimensioni dell'immagine quando la si carica. Il template le mette
    # negli attributi width/height dell'<img>, così il browser riserva lo spazio prima che l'immagine sia scaricata
    # (senza, il feed "salta" quando le immagini si caricano e l'ancora di un progetto finisce fuori posto).
    image = models.ImageField(upload_to="projects/", width_field="image_width", height_field="image_height")
    image_width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    image_height = models.PositiveIntegerField(null=True, blank=True, editable=False)

    def __str__(self):
        return f"Image for {self.project.title}"


class ContributorImage(models.Model):
    """Come ProjectImage, ma per i contributor (contributor.images.all)."""

    contributor = models.ForeignKey(Contributor, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="contributors/")

    def __str__(self):
        return f"Image for {self.contributor.name} {self.contributor.surname}"


class Event(models.Model):
    """Evento, futuro o passato. Non c'è un campo per distinguerli: lo decide event_list confrontando la data con oggi."""

    title = models.CharField(max_length=255)
    date = models.DateField()
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    event_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title


class Reference(models.Model):
    """Voce della pagina bibliografia/ispirazioni (libro, video, immagine o link).

    `kind` serve oggi solo come etichetta e per il filtro; l'immagine, se caricata,
    viene mostrata qualunque sia il tipo. Tutti i campi sono facoltativi tranne titolo e tipo.
    """

    KINDS = [
        ("book", "book"),
        ("video", "video"),
        ("image", "image"),
        ("link", "link"),
    ]

    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=KINDS, default=KINDS[0][0])
    author = models.CharField(max_length=255, blank=True)
    year = models.PositiveSmallIntegerField(blank=True, null=True)
    url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    image = models.ImageField(upload_to="references/", blank=True)
    # La relazione si modifica da questo lato (admin della referenza); dal progetto
    # si legge con project.references (nell'admin del progetto è in sola lettura).
    projects = models.ManyToManyField(Project, related_name="references", blank=True)

    class Meta:
        # Ordine alfabetico, vale anche per project.references.all()
        ordering = ["title"]

    def __str__(self):
        return self.title
