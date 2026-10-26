from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Contributor, Event, Project, ProjectType, Reference


def home(request):
    return render(request, "portfolio/home.html")


def project_list(request):
    """Archivio: tabella dei progetti con ordinamento e filtro per tipologia.

    Parametri nell'indirizzo:
    - ?sort=title|date, con "-" davanti per l'ordine decrescente (default "-date").
    - ?type=<slug di una ProjectType>; uno slug inesistente dà una tabella vuota.
    La colonna Type non è ordinabile: con più tipologie per progetto l'ordine non
    avrebbe senso e le righe si duplicherebbero.
    """
    # Lista bianca: il valore arriva dall'utente e finisce in order_by().
    sortable_fields = ["title", "date"]
    sort = request.GET.get("sort", "-date")
    if sort.lstrip("-") not in sortable_fields:
        sort = "-date"

    project_type = request.GET.get("type", "")

    projects = Project.objects.prefetch_related("project_types")
    if project_type:
        projects = projects.filter(project_types__slug=project_type)
    projects = projects.order_by(sort)

    return render(request, "portfolio/project_list.html", {
        "projects": projects,
        "current_sort": sort,
        "current_type": project_type,
        "types": ProjectType.objects.all(),
    })


def project_detail(request, pk):
    """Non ha una pagina propria: porta al feed, già scrollato sul progetto richiesto.

    Il redirect aggiunge l'ancora #project-<pk> e il browser fa lo scroll da solo.
    L'indirizzo /projects/<pk>/ resta perché {% url 'project_detail' pk %} è usato
    nell'archivio, nella pagina dei contributor e in quella delle referenze.
    """
    get_object_or_404(Project, pk=pk)  # pk inesistente -> 404 invece di un'ancora a vuoto
    return redirect(f"{reverse('project_feed')}#project-{pk}")


def project_feed(request):
    """Tutti i progetti uno dopo l'altro in un'unica pagina (non paginata), dal più recente.

    Ogni progetto è un <section id="project-<pk>">: è il bersaglio dell'ancora di project_detail.
    """
    projects = Project.objects.prefetch_related("references").order_by("-date")
    return render(request, "portfolio/project_feed.html", {"projects": projects})


def contributor_list(request):
    contributors = Contributor.objects.all()
    return render(request, "portfolio/contributor_list.html", {"contributors": contributors})


def contributor_detail(request, pk):
    contributor = get_object_or_404(Contributor, pk=pk)
    return render(request, "portfolio/contributor_detail.html", {"contributor": contributor})


def event_list(request):
    """Due liste separate: eventi futuri (dal più vicino) e passati (dal più recente).

    La divisione si fa qui con due query, non nel template, così ordine e filtro
    li esegue il database. "Oggi" conta come futuro.
    """
    today = timezone.localdate()
    upcoming_events = Event.objects.filter(date__gte=today).order_by("date")
    past_events = Event.objects.filter(date__lt=today).order_by("-date")
    return render(request, "portfolio/event_list.html", {
        "upcoming_events": upcoming_events,
        "past_events": past_events,
    })


def reference_list(request):
    """Pagina References, in ordine alfabetico, con filtro opzionale ?kind=book|video|image|link.

    Un valore di kind non valido viene ignorato (si vedono tutte le referenze).
    """
    kind = request.GET.get("kind", "")
    # Prefetch con ordine esplicito: i progetti collegati compaiono dal più recente.
    references = Reference.objects.prefetch_related(
        Prefetch("projects", queryset=Project.objects.order_by("-date"))
    )
    if kind in dict(Reference.KINDS):
        references = references.filter(kind=kind)
    else:
        kind = ""
    return render(request, "portfolio/reference_list.html", {
        "references": references,
        "current_kind": kind,
        "kinds": Reference.KINDS,
    })


def about(request):
    return render(request, "portfolio/about.html")
