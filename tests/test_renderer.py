import os
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.apps import apps as django_apps
from django.db import connection, close_old_connections
from django.db import transaction
from django.utils import timezone
from django.utils.translation import activate as activate_lang
#from django_distill.distill import urls_to_distill
#from django_distill.renderer import DistillRender, render_to_dir, render_single_file, get_renderer
#from django_distill.errors import DistillError
#from django_distill import distilled_urls


from staticsite.urls import get_staticsite_urls, get_staticsite_url_by_name
from staticsite.request import get_uri_values, generate_uri
from staticsite.renderer import StaticSiteRenderer, render_uri
from staticsite.errors import StaticSiteError


test_urls = get_staticsite_urls()
# A list of all the test urls that are not broken views. This is used for "loop all URLs" tests where
# having a view that on purpose throws an exception or raises a 404 is not useful.
test_urls_not_broken = [p for p in test_urls if not getattr(p.callback, 'skip_render_all', False)]


class StaticSiteRendererTestSuite(TestCase):

    def setUp(self):
        # Create a few test flatpages
        site = django_apps.get_model('sites.Site')
        current_site = site.objects.get_current()
        page1 = FlatPage()
        page1.url = '/flat/page1.html'
        page1.title = 'flatpage1'
        page1.content = 'flatpage1'
        page1.template_name = 'flatpage.html'
        page1.save()
        page1.sites.add(current_site)
        page2 = FlatPage()
        page2.url = '/flat/page2.html'
        page2.title = 'flatpage2'
        page2.content = 'flatpage2'
        page2.template_name = 'flatpage.html'
        page2.save()
        page2.sites.add(current_site)

    def test_get_uri_values(self):
        with StaticSiteRenderer(test_urls) as renderer:
            test = ()
            check = get_uri_values(lambda: test, None)
            self.assertEqual(check, (None,))
            test = ('a',)
            check = get_uri_values(lambda: test, None)
            test = (('a',),)
            check = get_uri_values(lambda: test, None)
            self.assertEqual(check, test)
            test = []
            check = get_uri_values(lambda: test, None)
            self.assertEqual(check, (None,))
            test = ['a']
            check = get_uri_values(lambda: test, None)
            self.assertEqual(check, test)
            test = [['a']]
            check = get_uri_values(lambda: test, None)
            self.assertEqual(check, test)
            for invalid in ('a', 1, b'a', {'s'}, {'a':'a'}, object()):
                with self.assertRaises(StaticSiteError):
                    get_uri_values(lambda: invalid, None)

    def test_re_path_no_param(self):
        u = get_staticsite_url_by_name('re_path-no-param')
        self.assertEqual(u.name, 're_path-no-param')
        with StaticSiteRenderer(test_urls) as renderer:
            param_set = get_uri_values(u.staticsite_urls_generator, u.name)[0]
            if not param_set:
                param_set = ()
            uri = generate_uri(u.staticsite_namespace, u.name, param_set)
            self.assertEqual(uri, '/re_path/no-param')
            status, headers, body = render_uri(uri, u.staticsite_status_codes)
            self.assertEqual(status, 200)
            self.assertEqual(body, b'test')

    def test_re_path_positional_param(self):
        u = get_staticsite_url_by_name('re_path-positional-param')
        self.assertEqual(u.name, 're_path-positional-param')
        with StaticSiteRenderer(test_urls) as renderer:
            param_sets = get_uri_values(u.staticsite_urls_generator, u.name)
            for param_set in param_sets:
                param_set = (param_set,)
                first_value = param_set[0]
                uri = generate_uri(u.staticsite_namespace, u.name, param_set)
                self.assertEqual(uri, f'/re_path/positional-param/{first_value}')
                status, headers, body = render_uri(uri, u.staticsite_status_codes)
                self.assertEqual(status, 200)
                self.assertEqual(body, b'test' + first_value.encode())

    def test_re_path_named_param(self):
        u = get_staticsite_url_by_name('re_path-named-param')
        self.assertEqual(u.name, 're_path-named-param')
        with StaticSiteRenderer(test_urls) as renderer:
            param_set = get_uri_values(u.staticsite_urls_generator, u.name)[0]
            uri = generate_uri(u.staticsite_namespace, u.name, param_set)
            self.assertEqual(uri, '/re_path/named-override-filename/test')
            status, headers, body = render_uri(uri, u.staticsite_status_codes)
            self.assertEqual(status, 200)
            self.assertEqual(body, b'testtest')

    def test_re_broken(self):
        u = get_staticsite_url_by_name('re_path-broken')
        self.assertEqual(u.name, 're_path-broken')
        with StaticSiteRenderer(test_urls) as renderer:
            param_set = get_uri_values(u.staticsite_urls_generator, u.name)[0]
            if not param_set:
                param_set = ()
            uri = generate_uri(u.staticsite_namespace, u.name, param_set)
            self.assertEqual(uri, '/re_path/broken')
            with self.assertRaises(StaticSiteError):
                status, headers, body = render_uri(uri, u.staticsite_status_codes)
                self.assertEqual(status, 500)

    def test_path_no_param(self):
        u = get_staticsite_url_by_name('path-no-param')
        self.assertEqual(u.name, 'path-no-param')
        with StaticSiteRenderer(test_urls) as renderer:
            param_set = get_uri_values(u.staticsite_urls_generator, u.name)[0]
            if not param_set:
                param_set = ()
            uri = generate_uri(u.staticsite_namespace, u.name, param_set)
            self.assertEqual(uri, '/path/no-param')
            status, headers, body = render_uri(uri, u.staticsite_status_codes)
            self.assertEqual(status, 200)
            self.assertEqual(body, b'test')

    def test_path_positional_param(self):
        u = get_staticsite_url_by_name('path-positional-param')
        self.assertEqual(u.name, 'path-positional-param')
        with StaticSiteRenderer(test_urls) as renderer:
            param_sets = get_uri_values(u.staticsite_urls_generator, u.name)
            for param_set in param_sets:
                param_set = (param_set,)
                first_value = param_set[0]
                uri = generate_uri(u.staticsite_namespace, u.name, param_set)
                self.assertEqual(uri, f'/path/positional-param/{first_value}')
                status, headers, body = render_uri(uri, u.staticsite_status_codes)
                self.assertEqual(status, 200)
                self.assertEqual(body, b'test' + first_value.encode())

    def test_path_named_param(self):
        u = get_staticsite_url_by_name('path-named-param')
        self.assertEqual(u.name, 'path-named-param')
        with StaticSiteRenderer(test_urls) as renderer:
            param_set = get_uri_values(u.staticsite_urls_generator, u.name)[0]
            uri = generate_uri(u.staticsite_namespace, u.name, param_set)
            self.assertEqual(uri, '/path/named-param/test')
            status, headers, body = render_uri(uri, u.staticsite_status_codes)
            self.assertEqual(status, 200)
            self.assertEqual(body, b'testtest')

    def test_path_broken(self):
        u = get_staticsite_url_by_name('path-broken')
        self.assertEqual(u.name, 'path-broken')
        with StaticSiteRenderer(test_urls) as renderer:
            param_set = get_uri_values(u.staticsite_urls_generator, u.name)[0]
            if not param_set:
                param_set = ()
            uri = generate_uri(u.staticsite_namespace, u.name, param_set)
            self.assertEqual(uri, '/path/broken')
            with self.assertRaises(StaticSiteError):
                status, headers, body = render_uri(uri, u.staticsite_status_codes)
                self.assertEqual(status, 500)

    def test_render_paths(self):
        expected_files = (
            ('test',),
            #('re_path', '12345'),
            #('re_path', 'test'),
            ('re_path', 'x', '12345.html'),
            ('re_path', 'x', 'test.html'),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            with StaticSiteRenderer(test_urls_not_broken) as renderer:
                renderer.render_to_directory(tmpdirname)
            written_files = []
            for (root, dirs, files) in os.walk(tmpdirname):
                for f in files:
                    filepath = os.path.join(root, f)
                    written_files.append(filepath)
            for expected_file in expected_files:
                filepath = os.path.join(tmpdirname, *expected_file)
                self.assertIn(filepath, written_files)

    '''
    @patch.object(CustomRender, "render_view", side_effect=CustomRender.render_view, autospec=True)
    @override_settings(DISTILL_RENDERER="tests.test_renderer.CustomRender")
    def test_render_paths_custom_renderer(self, render_view_spy):
        def _blackhole(_):
            pass
        expected_files = (
            ('test',),
            ('re_path', '12345'),
            ('re_path', 'test'),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            with self.assertRaises(DistillError):
                render_to_dir(tmpdirname, urls_to_distill, _blackhole)
            written_files = []
            for (root, dirs, files) in os.walk(tmpdirname):
                for f in files:
                    filepath = os.path.join(root, f)
                    written_files.append(filepath)
            for expected_file in expected_files:
                filepath = os.path.join(tmpdirname, *expected_file)
                self.assertIn(filepath, written_files)
        #self.assertEqual(render_view_spy.call_count, 34)
    '''

    '''
    def test_sessions_are_ignored(self):
        u = get_staticsite_url_by_name('path-ignore-sessions')
        self.assertEqual(u.name, 'path-ignore-sessions')
        with StaticSiteRenderer(test_urls) as renderer:
            param_set = renderer.get_uri_values(u.urls_generator, u.name)[0]
            if not param_set:
                param_set = ()
            uri = renderer.generate_uri(u.namespace, u.name, param_set)
            self.assertEqual(uri, '/path/ignore-sessions')
            status, headers, body = renderer.render_uri(uri, u.status_codes)
            self.assertEqual(status, 200)
            self.assertEqual(body, b'test')
    '''

    '''
    def test_custom_status_codes(self):
        u = get_staticsite_url_by_name('path-404')
        self.assertEqual(u.name, 'path-404')
        with StaticSiteRenderer(test_urls) as renderer:
            param_set = renderer.get_uri_values(u.urls_generator, u.name)[0]
            if not param_set:
                param_set = ()
            uri = renderer.generate_uri(u.namespace, u.name, param_set)
            self.assertEqual(uri, '/path/404')
            status, headers, body = renderer.render_uri(uri, u.status_codes)
            self.assertEqual(status, 404)
            self.assertEqual(body, b'404')
    '''

    '''
    def test_contrib_flatpages(self):
        u = get_staticsite_url_by_name('path-flatpage')
        self.assertEqual(u.name, 'path-flatpage')
        with StaticSiteRenderer(test_urls) as renderer:
            param_set = renderer.get_uri_values(u.urls_generator, u.name)
            for param in param_set:
                page_url = param['url']
                uri = renderer.generate_uri(u.namespace, u.name, param)
                self.assertEqual(uri, f'/path/flatpage/{page_url}')
                status, headers, body = renderer.render_uri(uri, u.status_codes)
                flatpage = FlatPage.objects.get(url=page_url)
                expected = f'<title>{flatpage.title}</title><body>{flatpage.content}</body>\n'
                self.assertEqual(body, expected.encode())
                self.assertEqual(status, 200)
    '''

'''
class DjangoDistillRendererTestSuite(TestCase):

    def test_contrib_sitemaps(self):
        view = self._get_view('path-sitemap')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/test-sitemap')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        expected_content = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            b'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            b'<url><loc>http://example.com/path/test-sitemap</loc>'
            b'<changefreq>daily</changefreq>'
            b'<priority>0.5</priority></url>\n</urlset>\n'
        )
        self.assertEqual(render.content, expected_content)
        self.assertEqual(render.status_code, 200)

    def test_render_single_file(self):
        expected_files = (
            ('path', '12345'),
            ('path', 'test'),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            render_single_file(tmpdirname, 'path-positional-param', 12345)
            render_single_file(tmpdirname, 'path-named-param', param='test')
            written_files = []
            for (root, dirs, files) in os.walk(tmpdirname):
                for f in files:
                    filepath = os.path.join(root, f)
                    written_files.append(filepath)
            for expected_file in expected_files:
                filepath = os.path.join(tmpdirname, *expected_file)
                self.assertIn(filepath, written_files)

    def test_i18n(self):
        if not settings.USE_I18N:
            self._skip('settings.USE_I18N')
            return
        settings.DISTILL_LANGUAGES = [
            'en',
            'fr',
            'de',
        ]
        expected = {}
        for lang_code, lang_name in settings.DISTILL_LANGUAGES:
            expected[lang_code] = f'/{lang_code}/path/i18n/sub-url-with-i18n-prefix'
        view = self._get_view('test-url-i18n')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        for lang_code, path in expected.items():
            activate_lang(lang_code)
            uri = self.renderer.generate_uri(view_url, view_name, param_set)
            self.assertEqual(uri, path)
            render = self.renderer.render_view(uri, status_codes, param_set, args)
            self.assertEqual(render.content, b'test')
        # Render the test URLs and confirm the expected language URI prefixes are present
        def _blackhole(_):
            pass
        expected_files = (
            ('test',),
            ('re_path', '12345'),
            ('re_path', 'test'),
            ('re_path', 'x', '12345.html'),
            ('re_path', 'x', 'test.html'),
            ('en', 'path', 'i18n', 'sub-url-with-i18n-prefix'),
            ('fr', 'path', 'i18n', 'sub-url-with-i18n-prefix'),
            ('de', 'path', 'i18n', 'sub-url-with-i18n-prefix'),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            with self.assertRaises(DistillError):
                render_to_dir(tmpdirname, urls_to_distill, _blackhole, parallel_render=8)
            written_files = []
            for (root, dirs, files) in os.walk(tmpdirname):
                for f in files:
                    filepath = os.path.join(root, f)
                    written_files.append(filepath)
            for expected_file in expected_files:
                filepath = os.path.join(tmpdirname, *expected_file)
                self.assertIn(filepath, written_files)
        settings.DISTILL_LANGUAGES = []

    def test_kwargs(self):
        if not settings.HAS_PATH:
            self._skip('django.urls.path')
            return
        view = self._get_view('test-kwargs')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/kwargs')
        render = self.renderer.render_view(uri, status_codes, param_set, args, kwargs)
        self.assertEqual(render.content, b'test')

    def test_humanize(self):
        if not settings.HAS_PATH:
            self._skip('django.urls.path')
            return
        view = self._get_view('test-humanize')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/humanize')
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        nineteen_hours_ago = now - timedelta(hours=19)
        render = self.renderer.render_view(uri, status_codes, param_set, args, kwargs)
        content = render.content
        expected = b'\n'.join([
            b'',
            b'<ul>',
            b'<li>test</li>',
            b'<li>one hour ago naturaltime: an hour ago</li>',
            b'<li>nineteen hours ago naturaltime: 19\xc2\xa0hours ago</li>',
            b'</ul>',
            b'',
        ])
        self.assertEqual(render.content, expected)

    def test_request_has_resolver_match(self):
        view = self._get_view('test-has-resolver-match')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        render = self.renderer.render_view(uri, status_codes, param_set, args, kwargs)
        self.assertEqual(render.content, b"test_request_has_resolver_match")

    def test_parallel_rendering(self):
        def _blackhole(_):
            pass
        expected_files = (
            ('test',),
            ('re_path', '12345'),
            ('re_path', 'test'),
            ('re_path', 'x', '12345.html'),
            ('re_path', 'x', 'test.html'),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            with self.assertRaises(DistillError):
                render_to_dir(tmpdirname, urls_to_distill, _blackhole, parallel_render=8)
            written_files = []
            for (root, dirs, files) in os.walk(tmpdirname):
                for f in files:
                    filepath = os.path.join(root, f)
                    written_files.append(filepath)
            for expected_file in expected_files:
                filepath = os.path.join(tmpdirname, *expected_file)
                self.assertIn(filepath, written_files)

    def test_generate_urls(self):
        urls = distilled_urls()
        generated_urls = []
        for url, file_name in urls:
            generated_urls.append(url)
        expected_urls = (
            '/path/namespace1/sub-url-in-namespace',
            '/path/namespace1/path/sub-namespace/sub-url-in-sub-namespace',
            '/path/no-namespace/sub-url-in-no-namespace',
            '/en/path/i18n/sub-url-with-i18n-prefix',
            '/re_path/',
            '/re_path-no-func/',
            '/re_path/12345',
            '/re_path/67890',
            '/re_path/x/12345',
            '/re_path/x/67890',
            '/re_path/test',
            '/re_path/x/test',
            '/re_path/broken',
            '/re_path/ignore-sessions',
            '/re_path/404',
            '/re_path/flatpage/flat/page1.html',
            '/re_path/flatpage/flat/page2.html',
            '/path/',
            '/path-no-func/',
            '/path/12345',
            '/path/67890',
            '/path/x/12345',
            '/path/x/67890',
            '/path/test',
            '/path/x/test',
            '/path/broken',
            '/path/ignore-sessions',
            '/path/404',
            '/path/flatpage/flat/page1.html',
            '/path/flatpage/flat/page2.html',
            '/path/test-sitemap',
            '/path/kwargs',
            '/path/humanize',
            '/path/has-resolver-match'
        )
        self.assertEqual(sorted(generated_urls), sorted(expected_urls))
'''