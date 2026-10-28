"""
Test dell'app portfolio. Si lanciano con:  python manage.py test portfolio

Le classi basate su TestCase usano il database: Django crea un database temporaneo
(test_<nome del db>) e lo cancella alla fine, quindi l'utente Postgres deve poter
creare database. Il database vero non viene toccato.
"""
import tempfile
from pathlib import Path
from urllib.parse import urljoin

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, SimpleTestCase, TestCase, override_settings

from .embeds import soundcloud_embed_url, youtube_embed_url
from .models import Project, Reference


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
        self.assertIn("<h2>References</h2>", linked)
        self.assertNotIn("<h2>References</h2>", lonely)


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
                self.assertEqual(youtube_embed_url(url), self.YT)

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
        expected = "https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fsome-artist%2Fsome-track"
        for url in [
            "https://soundcloud.com/some-artist/some-track",
            "https://www.soundcloud.com/some-artist/some-track?si=abc123&utm_source=clipboard",
            "https://m.soundcloud.com/some-artist/some-track#t=30",
            "http://soundcloud.com/some-artist/some-track/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(soundcloud_embed_url(url), expected)

    def test_soundcloud_keeps_playlists_and_private_link_tokens(self):
        self.assertTrue(soundcloud_embed_url("https://soundcloud.com/some-artist/sets/some-playlist").endswith(
            "some-artist%2Fsets%2Fsome-playlist"))
        self.assertTrue(soundcloud_embed_url("https://soundcloud.com/some-artist/some-track/s-AbCdEfG").endswith(
            "some-track%2Fs-AbCdEfG"))

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
        self.assertIn('src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"', html)
        self.assertIn("https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fsome-artist%2Fsome-track", html)
        self.assertEqual(html.count("<iframe"), 2)

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
