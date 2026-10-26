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
from django.test import Client, SimpleTestCase, TestCase, override_settings

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
