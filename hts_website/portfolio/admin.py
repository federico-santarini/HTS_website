from django.contrib import admin
from .models import Contributor, ContributorImage, Event, Project, ProjectImage, ProjectType, Reference


# Inline: le immagini si caricano dalla stessa pagina del progetto/contributor,
# una riga per immagine ("extra" = righe vuote offerte in più).
class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


class ContributorImageInline(admin.TabularInline):
    model = ContributorImage
    extra = 1


@admin.action(description="Duplicate selected listings")
def duplicate_listings(modeladmin, request, queryset):
    """Azione admin: duplica le righe selezionate, prefissando il titolo con "Copy of".

    Funziona solo per modelli con un campo `title` e NON copia le relazioni
    many-to-many. Oggi è collegata solo a EventAdmin.
    """
    for object in queryset:
        # Clear the primary key so Django creates a new record
        object.pk = None  
        
        # Optional: Alter specific data to indicate it's a copy
        object.title = f"Copy of {object.title}" 
        
        object.save()
        
    modeladmin.message_user(request, f"Successfully duplicated {queryset.count()} listings.")

@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}  # lo slug si compila da solo dal nome

    def get_deleted_objects(self, objs, request):
        # Blocca la cancellazione di tipologie ancora in uso. Per una many-to-many non
        # esiste on_delete=PROTECT (Django toglierebbe i collegamenti in silenzio), quindi
        # i progetti collegati vengono aggiunti alla lista "protected" di Django: la pagina
        # di conferma li elenca e non mostra il pulsante di conferma. Vale sia per la
        # cancellazione singola sia per l'azione "delete selected" (se una sola delle
        # tipologie selezionate è in uso, non si cancella nessuna delle selezionate).
        # Non protegge da cancellazioni fatte da codice o da `manage.py shell`.
        deletable, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        in_use = Project.objects.filter(project_types__in=objs).distinct()
        protected = list(protected) + [f"Project: {project.title}" for project in in_use]
        return deletable, model_count, perms_needed, protected


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title"]
    filter_horizontal = ["contributors", "project_types"]
    readonly_fields = ["related_references"]
    inlines = [ProjectImageInline]

    # Campo di sola lettura: la relazione con le referenze si modifica dall'admin della Reference.
    @admin.display(description="References")
    def related_references(self, project):
        if not project.pk:  # nella pagina "add" il progetto non esiste ancora, niente relazioni da leggere
            return "—"
        return ", ".join(project.references.values_list("title", flat=True)) or "—"



@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
    list_display = ["name", "surname", "affiliation"]
    readonly_fields = ["related_projects"]
    fields = ["name", "surname", "affiliation", "bio", "related_projects"]
    inlines = [ContributorImageInline]

    # Sola lettura: la relazione si modifica dall'admin del Project (dove sta la M2M).
    @admin.display(description="Projects")
    def related_projects(self, contributor):
        if not contributor.pk:  # pagina "add": il contributor non esiste ancora
            return "—"
        return ", ".join(contributor.projects.values_list("title", flat=True)) or "—"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "date", "location"]
    ordering = ["date"]
    actions = [duplicate_listings]


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "author", "year"]
    list_filter = ["kind"]
    search_fields = ["title", "author", "notes"]
    filter_horizontal = ["projects"]  # widget a due colonne per scegliere i progetti collegati
