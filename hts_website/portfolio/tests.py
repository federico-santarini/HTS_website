"""
Test dell'app portfolio. Si lanciano con:  python manage.py test portfolio

Le classi basate su TestCase usano il database: Django crea un database temporaneo
(test_<nome del db>) e lo cancella alla fine, quindi l'utente Postgres deve poter
creare database. Il database vero non viene toccato.
"""
import os
import re
import tempfile
from io import StringIO
from unittest import mock
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import Client, SimpleTestCase, TestCase, override_settings

from .embeds import soundcloud_embed_url, youtube_embed_url, youtube_thumbnail_url
from .models import Contributor, Project, Reference, SiteSettings


class PublicationMiddlewareTests(SimpleTestCase):
    """Sottodominio della pubblicazione. Usa una cartella temporanea al posto di publication/
    e host finti (publication.localhost / localhost); nessun database."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "index.html").write_text("<h1>Publication home</h1>")
        (root / "style.css").write_text("body { color: red; }")
        (root / "chapter").mkdir()
        (root / "chapter" / "index.html").write_text("<h1>Chapter</h1>")

        override = override_settings(PUBLICATION_DIR=root)
        override.enable()
        self.addCleanup(override.disable)

        self.publication = Client(HTTP_HOST="publication.localhost")
        self.main = Client(HTTP_HOST="localhost")

    def test_subdomain_serves_index(self):
        response = self.publication.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Publication home", b"".join(response.streaming_content))

    def test_subdomain_serves_assets_with_content_type(self):
        response = self.publication.get("/style.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response["Content-Type"])

    def test_subdomain_serves_nested_index(self):
        response = self.publication.get("/chapter/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Chapter", b"".join(response.streaming_content))

    def test_subdomain_redirects_directory_without_slash(self):
        response = self.publication.get("/chapter")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urljoin("/chapter", response["Location"]), "/chapter/")

    def test_subdomain_unknown_path_is_404(self):
        self.assertEqual(self.publication.get("/missing.html").status_code, 404)

    def test_subdomain_does_not_expose_main_site(self):
        self.assertEqual(self.publication.get("/about/").status_code, 404)

    def test_subdomain_blocks_path_traversal(self):
        for path in ["/../manage.py", "/%2e%2e/manage.py", "/..%2fmanage.py"]:
            with self.subTest(path=path):
                self.assertEqual(self.publication.get(path).status_code, 404)

    def test_main_host_is_untouched(self):
        response = self.main.get("/about/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Publication home", response.content)


class ReferenceListTests(TestCase):
    """Pagina References (ordine, filtro) e collegamento referenze <-> progetti nelle pagine pubbliche."""

    @classmethod
    def setUpTestData(cls):
        cls.book = Reference.objects.create(title="Book one", kind="book", author="A. Author", year=2020)
        cls.project = Project.objects.create(title="Linked project", description="d")
        cls.other_project = Project.objects.create(title="Lonely project", description="d")
        cls.book.projects.add(cls.project)
        Reference.objects.create(title="Video one", kind="video", url="https://example.com/v")
        Reference.objects.create(title="Link one", kind="link", url="https://example.com/l")

    def titles(self, response):
        return [reference.title for reference in response.context["references"]]

    def test_lists_all_references_alphabetically(self):
        response = self.client.get("/references/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.titles(response), ["Book one", "Link one", "Video one"])

    def test_filters_by_kind(self):
        response = self.client.get("/references/", {"kind": "book"})
        self.assertEqual(self.titles(response), ["Book one"])
        self.assertEqual(response.context["current_kind"], "book")

    def test_unknown_kind_is_ignored(self):
        response = self.client.get("/references/", {"kind": "nope"})
        self.assertEqual(len(self.titles(response)), 3)
        self.assertEqual(response.context["current_kind"], "")

    def test_renders_author_year_and_link(self):
        html = self.client.get("/references/").content.decode()
        self.assertIn("A. Author, 2020", html)
        self.assertIn('<a href="https://example.com/v">Video one</a>', html)

    def test_page_is_linked_from_navbar(self):
        html = self.client.get("/about/").content.decode()
        self.assertIn('href="/references/"', html)

    def test_reference_list_links_to_its_projects(self):
        html = self.client.get("/references/").content.decode()
        self.assertIn(f'<a href="/projects/{self.project.pk}/">Linked project</a>', html)
        self.assertNotIn("Lonely project", html)

    def test_project_feed_shows_its_references(self):
        html = self.client.get("/projects/feed/").content.decode()
        linked = html.split('id="project-%d"' % self.project.pk)[1].split("</section>")[0]
        lonely = html.split('id="project-%d"' % self.other_project.pk)[1].split("</section>")[0]
        self.assertIn("Book one", linked)
        self.assertIn('<h3 class="section-label">references</h3>', linked)
        self.assertNotIn('<h3 class="section-label">references</h3>', lonely)


class FeedReferenceFormatTests(TestCase):
    """Come una reference appare nel feed: titolo in corsivo con la sola iniziale maiuscola, autore solo se c'è."""

    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(title="P", description="d")
        Reference.objects.create(title="THE Cyborg MANIFESTO", author="donna haraway", kind="book").projects.add(cls.project)
        Reference.objects.create(title="anonymous zine", kind="link", url="https://example.com/z").projects.add(cls.project)

    def feed(self):
        return self.client.get("/projects/feed/").content.decode()

    def test_title_is_italic_with_only_the_first_letter_capitalised(self):
        self.assertIn("<em>The cyborg manifesto&nbsp;", self.feed())

    def test_link_is_on_the_kind_label_not_on_the_title(self):
        html = self.feed()
        self.assertIn("<em>Anonymous zine&nbsp;", html)
        self.assertIn('(<a href="https://example.com/z">link</a>)', html)

    def test_author_is_marked_for_capitalisation_and_missing_author_leaves_no_comma(self):
        html = self.feed()
        self.assertIn('<span class="reference-author">donna haraway</span>, ', html)
        self.assertNotIn("<li>, ", html)
        self.assertNotIn('<li><span class="reference-author"></span>', html)


class NavbarActiveLinkTests(TestCase):
    """La voce della navbar che corrisponde alla pagina corrente (e solo quella) è evidenziata."""

    @classmethod
    def setUpTestData(cls):
        cls.contributor = Contributor.objects.create(name="Ada", surname="Lovelace")

    def active_labels(self, path):
        html = self.client.get(path).content.decode()
        return re.findall(r'<a class="nav-link active"[^>]*>(.*?)</a>', html)

    def test_each_page_highlights_its_own_entry(self):
        for path, label in [
            ("/", "Home"),
            ("/projects/", "Archive"),
            ("/projects/feed/", "Archive"),  # il feed fa parte dell'archivio
            ("/contributors/", "Contributors"),
            (f"/contributors/{self.contributor.pk}/", "Contributors"),
            ("/events/", "Events"),
            ("/references/", "References"),
            ("/about/", "About"),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.active_labels(path), [label])

    def test_active_entry_is_marked_for_screen_readers(self):
        html = self.client.get("/references/").content.decode()
        self.assertEqual(html.count('aria-current="page"'), 1)

    def test_unknown_page_highlights_nothing(self):
        self.assertEqual(self.active_labels("/does-not-exist/"), [])


class ProjectAdminReferencesTests(TestCase):
    """Campo di sola lettura "References" nell'admin dei progetti (si entra come superuser di prova)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("admin_user", password="x")
        cls.project = Project.objects.create(title="With refs", description="d")
        cls.empty_project = Project.objects.create(title="No refs", description="d")
        for title in ["Zeta book", "Alpha video"]:
            Reference.objects.create(title=title).projects.add(cls.project)

    def setUp(self):
        self.client.force_login(self.user)

    def test_change_page_lists_references_alphabetically(self):
        html = self.client.get(f"/admin/portfolio/project/{self.project.pk}/change/").content.decode()
        self.assertIn("Alpha video, Zeta book", html)

    def test_change_page_without_references_shows_dash(self):
        response = self.client.get(f"/admin/portfolio/project/{self.empty_project.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Zeta book", response.content.decode())

    def test_add_page_renders(self):
        self.assertEqual(self.client.get("/admin/portfolio/project/add/").status_code, 200)


class EmbedUrlTests(SimpleTestCase):
    """Conversione dei link di YouTube e SoundCloud in indirizzi di embed (nessun database)."""

    YT = "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"

    @staticmethod
    def without_query(url):
        """L'indirizzo di embed senza i parametri di aspetto (?rel=0&...)."""
        return url.split("?")[0]

    @staticmethod
    def soundcloud_target(url):
        """Il link al brano che il player di SoundCloud riceve nel parametro url=."""
        return parse_qs(urlparse(url).query)["url"][0]

    def test_youtube_accepts_the_common_link_forms(self):
        for url in [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PL123",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?si=trackingparam",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            "  https://youtu.be/dQw4w9WgXcQ  ",
            "http://youtu.be/dQw4w9WgXcQ",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.without_query(youtube_embed_url(url)), self.YT)

    def test_youtube_embed_carries_the_appearance_parameters(self):
        query = parse_qs(urlparse(youtube_embed_url("https://youtu.be/dQw4w9WgXcQ")).query)
        self.assertEqual(query["rel"], ["0"])
        self.assertEqual(query["color"], ["white"])
        self.assertEqual(query["iv_load_policy"], ["3"])

    def test_youtube_thumbnail_comes_from_the_same_video_id(self):
        expected = "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
        for url in ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ?si=x"]:
            with self.subTest(url=url):
                self.assertEqual(youtube_thumbnail_url(url), expected)
        for bad in ["", None, "https://vimeo.com/123456", "https://www.youtube.com/watch?v=short"]:
            with self.subTest(bad=bad):
                self.assertIsNone(youtube_thumbnail_url(bad))

    def test_youtube_rejects_everything_else(self):
        for url in [
            "",
            None,
            "https://www.youtube.com/",
            "https://www.youtube.com/watch",
            "https://www.youtube.com/watch?v=short",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ%22onload=%22x",
            "https://www.youtube.com/@somechannel",
            "https://vimeo.com/123456789",
            "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
            "https://evil.example/youtube.com/watch?v=dQw4w9WgXcQ",
            "https://evil.example/?next=https://youtu.be/dQw4w9WgXcQ",
            "javascript:alert(1)",
            "ftp://youtu.be/dQw4w9WgXcQ",
            '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>',
        ]:
            with self.subTest(url=url):
                self.assertIsNone(youtube_embed_url(url))

    def test_soundcloud_builds_the_player_url_and_drops_tracking_parameters(self):
        expected = "https://soundcloud.com/some-artist/some-track"
        for url in [
            "https://soundcloud.com/some-artist/some-track",
            "https://www.soundcloud.com/some-artist/some-track?si=abc123&utm_source=clipboard",
            "https://m.soundcloud.com/some-artist/some-track#t=30",
            "http://soundcloud.com/some-artist/some-track/",
        ]:
            with self.subTest(url=url):
                embed = soundcloud_embed_url(url)
                self.assertTrue(embed.startswith("https://w.soundcloud.com/player/?"))
                self.assertEqual(self.soundcloud_target(embed), expected)

    def test_soundcloud_embed_carries_the_appearance_parameters(self):
        query = parse_qs(urlparse(soundcloud_embed_url("https://soundcloud.com/some-artist/some-track")).query)
        self.assertEqual(query["color"], ["#b026ff"])
        self.assertEqual(query["visual"], ["false"])
        self.assertEqual(query["show_comments"], ["false"])
        self.assertNotIn("show_user", query)  # il nome dell'artista resta visibile

    def test_soundcloud_keeps_playlists_and_private_link_tokens(self):
        self.assertEqual(
            self.soundcloud_target(soundcloud_embed_url("https://soundcloud.com/some-artist/sets/some-playlist")),
            "https://soundcloud.com/some-artist/sets/some-playlist")
        self.assertEqual(
            self.soundcloud_target(soundcloud_embed_url("https://soundcloud.com/some-artist/some-track/s-AbCdEfG")),
            "https://soundcloud.com/some-artist/some-track/s-AbCdEfG")

    def test_soundcloud_rejects_everything_else(self):
        for url in [
            "",
            None,
            "https://soundcloud.com/",
            "https://soundcloud.com/some-artist",
            "https://soundcloud.com.evil.example/some-artist/some-track",
            "https://evil.example/soundcloud.com/some-artist/some-track",
            "https://w.soundcloud.com/player/?url=https%3A%2F%2Fevil.example",
            "https://bandcamp.com/some-artist/some-track",
            "javascript:alert(1)",
        ]:
            with self.subTest(url=url):
                self.assertIsNone(soundcloud_embed_url(url))


class ProjectEmbedTests(TestCase):
    """Campi youtube_url / soundcloud_url: validazione nel modello e player nel feed dei progetti."""

    @classmethod
    def setUpTestData(cls):
        cls.with_embeds = Project.objects.create(
            title="With players", description="d",
            youtube_url="https://youtu.be/dQw4w9WgXcQ?si=x",
            soundcloud_url="https://soundcloud.com/some-artist/some-track?si=y",
        )
        cls.plain = Project.objects.create(title="Plain project", description="d")

    def section(self, project):
        html = self.client.get("/projects/feed/").content.decode()
        return html.split('id="project-%d"' % project.pk)[1].split("</section>")[0]

    def test_feed_renders_both_players_for_a_project_that_has_them(self):
        html = self.section(self.with_embeds)
        # YouTube: solo la copertina; l'iframe lo crea players.js al clic, partendo da data-embed-url.
        self.assertIn('data-embed-url="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?', html)
        self.assertIn('src="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"', html)
        # SoundCloud: il widget nascosto ha l'indirizzo in data-src (lo imposta players.js quando serve).
        self.assertIn('data-src="https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fsome-artist%2Fsome-track&amp;', html)
        self.assertEqual(html.count("<iframe"), 1)

    def test_feed_shows_no_player_when_the_fields_are_empty(self):
        self.assertNotIn("<iframe", self.section(self.plain))

    def test_empty_fields_are_valid_and_have_no_embed(self):
        self.plain.full_clean(exclude=["description"])
        self.assertIsNone(self.plain.youtube_embed_url)
        self.assertIsNone(self.plain.soundcloud_embed_url)

    def test_full_clean_rejects_links_from_other_sites(self):
        for field, bad in [("youtube_url", "https://vimeo.com/123456"), ("soundcloud_url", "https://example.com/a/b"),
                           ("youtube_url", "https://soundcloud.com/some-artist/some-track")]:
            with self.subTest(field=field, value=bad):
                project = Project(title="x", description="d", **{field: bad})
                with self.assertRaises(ValidationError) as ctx:
                    project.full_clean()
                self.assertIn(field, ctx.exception.message_dict)


class SiteSettingsTests(TestCase):
    """Intro animato della homepage: interruttore nelle impostazioni del sito (un solo record) e comparsa solo sulla home."""

    def test_load_creates_the_single_record_with_the_intro_off(self):
        settings = SiteSettings.load()
        self.assertFalse(settings.intro_enabled)
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_saving_another_record_overwrites_instead_of_adding(self):
        SiteSettings.load()
        SiteSettings.objects.create(intro_enabled=True)
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertTrue(SiteSettings.load().intro_enabled)

    def test_home_has_the_intro_when_enabled(self):
        SiteSettings.objects.create(intro_enabled=True)
        html = self.client.get("/").content.decode()
        self.assertIn('id="intro"', html)
        self.assertIn('class="intro-enter"', html)  # il bottone d'ingresso (il suo testo si può cambiare liberamente)
        self.assertIn("audio/intro.mp3", html)
        self.assertEqual(html.count("<path pathLength"), 3)

    def test_home_has_no_intro_when_disabled(self):
        SiteSettings.objects.create(intro_enabled=False)
        self.assertNotIn('id="intro"', self.client.get("/").content.decode())

    def test_other_pages_never_have_the_intro(self):
        for path in ["/about/", "/projects/", "/events/", "/contributors/"]:
            with self.subTest(path=path):
                self.assertNotIn('id="intro"', self.client.get(path).content.decode())

    def test_admin_entry_goes_straight_to_the_single_record_and_cannot_add_or_delete(self):
        admin_user = get_user_model().objects.create_superuser("admin_user", password="x")
        self.client.force_login(admin_user)
        response = self.client.get("/admin/portfolio/sitesettings/")
        self.assertRedirects(response, f"/admin/portfolio/sitesettings/{SiteSettings.load().pk}/change/")
        self.assertEqual(self.client.get("/admin/portfolio/sitesettings/add/").status_code, 403)
        self.assertEqual(self.client.get(f"/admin/portfolio/sitesettings/{SiteSettings.load().pk}/delete/").status_code, 403)


class NoIndexTests(TestCase):
    """NOINDEX: l'intestazione che chiede ai motori di ricerca di non indicizzare, su ogni risposta."""

    @override_settings(NOINDEX=True)
    def test_header_is_on_pages_and_static_files_when_enabled(self):
        for path in ["/about/", "/static/css/custom.css"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path)["X-Robots-Tag"], "noindex, nofollow")

    @override_settings(NOINDEX=False)
    def test_no_header_when_disabled(self):
        self.assertNotIn("X-Robots-Tag", self.client.get("/about/"))


class AuthorsGroupTests(TestCase):
    """Il gruppo "Authors" (creato da migrate): gestisce i contenuti, non utenti né impostazioni del sito."""

    @classmethod
    def setUpTestData(cls):
        cls.author = get_user_model().objects.create_user("an_author", password="x", is_staff=True)
        cls.author.groups.add(Group.objects.get(name="Authors"))

    def setUp(self):
        self.client.force_login(self.author)

    def test_author_can_manage_content(self):
        for model in ["project", "contributor", "event", "reference", "projecttype"]:
            with self.subTest(model=model):
                self.assertEqual(self.client.get(f"/admin/portfolio/{model}/").status_code, 200)
                self.assertEqual(self.client.get(f"/admin/portfolio/{model}/add/").status_code, 200)

    def test_author_cannot_touch_site_settings_or_accounts(self):
        for path in ["/admin/portfolio/sitesettings/", "/admin/auth/user/", "/admin/auth/group/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)


class EnsureSuperuserTests(TestCase):
    """Comando ensure_superuser: crea il superuser dall'ambiente se manca, senza mai toccarne uno esistente."""

    ENV = {"DJANGO_SUPERUSER_USERNAME": "boss", "DJANGO_SUPERUSER_PASSWORD": "a-long-test-password"}

    def run_command(self, env):
        with mock.patch.dict(os.environ, env, clear=False):
            call_command("ensure_superuser", stdout=StringIO())

    def test_creates_the_superuser_once(self):
        self.run_command(self.ENV)
        user = get_user_model().objects.get(username="boss")
        self.assertTrue(user.is_superuser and user.is_staff)
        self.assertTrue(user.check_password("a-long-test-password"))

    def test_existing_user_is_left_alone(self):
        get_user_model().objects.create_superuser("boss", password="the-original-password")
        self.run_command({**self.ENV, "DJANGO_SUPERUSER_PASSWORD": "something-else-entirely"})
        self.assertTrue(get_user_model().objects.get(username="boss").check_password("the-original-password"))

    def test_does_nothing_without_the_variables(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            for name in self.ENV:
                os.environ.pop(name, None)
            call_command("ensure_superuser", stdout=StringIO())
        self.assertFalse(get_user_model().objects.filter(username="boss").exists())
