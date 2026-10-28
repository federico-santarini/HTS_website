"""
Da un link normale di YouTube o SoundCloud all'indirizzo da mettere in un <iframe>.

Gli autori incollano nell'admin il link che copiano dal browser o da "Condividi"; qui si
riconosce il servizio, si ricava l'indirizzo di embed e si rifiuta tutto il resto. Il
controllo sull'host è anche una difesa: l'indirizzo finisce in un <iframe src="...">,
quindi non deve poter puntare a un sito qualsiasi.

Le funzioni *_embed_url restituiscono None se il link non è riconosciuto. I validator
servono ai campi del modello (vengono usati dalle migration: non rinominare né spostare).
"""
import re
from urllib.parse import parse_qs, quote, urlparse

from django.core.exceptions import ValidationError

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com"}
SOUNDCLOUD_HOSTS = {"soundcloud.com", "www.soundcloud.com", "m.soundcloud.com"}

YOUTUBE_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def _parse(url):
    """Restituisce (host, segmenti del percorso, query) se il link è http/https, altrimenti None."""
    parts = urlparse(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    segments = [s for s in parts.path.split("/") if s]
    return parts.hostname.lower(), segments, parse_qs(parts.query)


def youtube_embed_url(url):
    """https://www.youtube.com/watch?v=ID, https://youtu.be/ID, .../shorts/ID, .../embed/ID -> embed."""
    parsed = _parse(url or "")
    if not parsed or parsed[0] not in YOUTUBE_HOSTS:
        return None
    host, segments, query = parsed

    video_id = None
    if host == "youtu.be":
        video_id = segments[0] if segments else None
    elif segments[:1] == ["watch"]:
        video_id = (query.get("v") or [None])[0]
    elif segments[:1] in (["embed"], ["shorts"], ["live"], ["v"]) and len(segments) > 1:
        video_id = segments[1]

    if not video_id or not YOUTUBE_ID.fullmatch(video_id):
        return None
    # youtube-nocookie.com: il player non imposta cookie finché non si preme play.
    return f"https://www.youtube-nocookie.com/embed/{video_id}"


def soundcloud_embed_url(url):
    """Link a un brano o a una playlist (soundcloud.com/artista/titolo) -> player di SoundCloud."""
    parsed = _parse(url or "")
    if not parsed or parsed[0] not in SOUNDCLOUD_HOSTS:
        return None
    _, segments, _ = parsed
    # Servono almeno "artista/titolo": il solo profilo non è un brano. Query e frammento si
    # scartano (i link di "Condividi" portano parametri di tracciamento); il percorso resta
    # intero perché i link privati hanno il token nel percorso (.../s-XXXX).
    if len(segments) < 2:
        return None
    clean = "https://soundcloud.com/" + "/".join(segments)
    return "https://w.soundcloud.com/player/?url=" + quote(clean, safe="")


def validate_youtube_url(value):
    if value and youtube_embed_url(value) is None:
        raise ValidationError(
            "Enter the link of a YouTube video, e.g. https://www.youtube.com/watch?v=… or https://youtu.be/…"
        )


def validate_soundcloud_url(value):
    if value and soundcloud_embed_url(value) is None:
        raise ValidationError(
            "Enter the link of a SoundCloud track or playlist, e.g. https://soundcloud.com/artist/track"
        )
