from django.urls import path

from . import views

# Pagine pubbliche. I nomi (name=...) sono quelli usati nei template con {% url '...' %}:
# se ne cambi uno, aggiorna anche i template che lo usano.
urlpatterns = [
    path("", views.home, name="home"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),  # redirect al feed
    path("projects/feed/", views.project_feed, name="project_feed"),
    path("contributors/", views.contributor_list, name="contributor_list"),
    path("contributors/<int:pk>/", views.contributor_detail, name="contributor_detail"),
    path("events/", views.event_list, name="event_list"),
    path("references/", views.reference_list, name="reference_list"),
    path("about/", views.about, name="about"),
]
