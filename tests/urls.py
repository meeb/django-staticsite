from datetime import timedelta
from django.conf import settings
from django.http import HttpResponse
from django.urls import include, path, re_path, reverse
from django.conf.urls.i18n import i18n_patterns
from django.shortcuts import render
from django.utils import timezone
from django.contrib.flatpages.views import flatpage as flatpage_view
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.apps import apps as django_apps
from staticsite.utils import set_func_attr


app_name = 'staticsite-tests'


class TestStaticViewSitemap(Sitemap):

    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return ['path-sitemap']

    def location(self, item):
        return reverse(item)


sitemap_dict = {
    'static': TestStaticViewSitemap,
}


def test_no_param_view(request):
    return HttpResponse(b'test', content_type='application/octet-stream')


def test_positional_param_view(request, param):
    if not isinstance(param, str):
        param = str(param)
    return HttpResponse(b'test' + param.encode(),
                        content_type='application/octet-stream')


def test_named_param_view(request, param=None):
    if not isinstance(param, str):
        param = str(param)
    return HttpResponse(b'test' + param.encode(),
                        content_type='application/octet-stream')


def test_session_view(request):
    request.session['test'] = 'test'
    return HttpResponse(b'test', content_type='application/octet-stream')


@set_func_attr('skip_render_all_tests', True)
def test_broken_view(request):
    # Trigger a normal Python exception when rendering
    a = 1 / 0


@set_func_attr('skip_render_all_tests', True)
def test_http404_view(request):
    response = HttpResponse(b'404', content_type='application/octet-stream')
    response.status_code = 404
    return response


def test_humanize_view(request):
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)
    nineteen_hours_ago = now - timedelta(hours=19)
    return render(request, 'humanize.html', {
        'now': now,
        'one_hour_ago': one_hour_ago,
        'nineteen_hours_ago': nineteen_hours_ago
    })


def test_request_has_resolver_match_view(request):
    return HttpResponse(request.resolver_match.func.__name__)


def test_no_param_func():
    return None


def test_positional_param_func():
    return ('12345', '67890')


def test_named_param_func():
    return [{'param': 'test'}]


def test_flatpages_func():
    site = django_apps.get_model('sites.Site')
    current_site = site.objects.get_current()
    flatpages = current_site.flatpage_set.filter(registration_required=False)
    for flatpage in flatpages:
        yield {'url': flatpage.url}


urlpatterns = [

    path('path/namespace1/', include('tests.namespaced_urls', namespace='test_namespace')),
    path('path/no-namespace/', include('tests.no_namespaced_urls')),

]


urlpatterns += i18n_patterns(
    path('path/i18n/', include('tests.i18n_urls', namespace='test_i18n')),
)


urlpatterns += [

    re_path(r'^re_path/no-param$',
        test_no_param_view,
        name='re_path-no-param',
        staticsite_path=True,
        staticsite_urls_generator=test_no_param_func),
    re_path(r'^re_path/no-func$',
        test_no_param_view,
        name='re_path-no-param-no-func',
        staticsite_path=True),
    re_path(r'^re_path/positional-param/([\d]+)$',
        test_positional_param_view,
        name='re_path-positional-param',
        staticsite_path=True,
        staticsite_urls_generator=test_positional_param_func),
    re_path(r'^re_path/positional-override-filename/([\d]+)$',
        test_positional_param_view,
        name='re_path-positional-param-custom',
        staticsite_path=True,
        staticsite_urls_generator=test_positional_param_func,
        staticsite_filename="re_path/x/{}.html"),
    re_path(r'^re_path/named-override-filename/(?P<param>[\w]+)$',
        test_named_param_view,
        name='re_path-named-param',
        staticsite_path=True,
        staticsite_urls_generator=test_named_param_func),
    re_path(r'^re_path/named-param/(?P<param>[\w]+)$',
        test_named_param_view,
        name='re_path-named-param-custom',
        staticsite_path=True,
        staticsite_urls_generator=test_named_param_func,
        staticsite_filename="re_path/x/{param}.html"),
    re_path(r'^re_path/broken$',
        test_broken_view,
        name='re_path-broken',
        staticsite_path=True,
        staticsite_urls_generator=test_no_param_func),
    re_path(r'^re_path/ignore-sessions$',
        test_session_view,
        name='re_path-ignore-sessions',
        staticsite_path=True,
        staticsite_urls_generator=test_no_param_func),
    re_path(r'^re_path/404$',
        test_http404_view,
        name='re_path-404',
        staticsite_path=True,
        staticsite_status_codes=(404,),
        staticsite_urls_generator=test_no_param_func),
    re_path(r'^re_path/flatpage(?P<url>.+)$',
        flatpage_view,
        name='re_path-flatpage',
        staticsite_path=True,
        staticsite_urls_generator=test_flatpages_func),

]


urlpatterns += [

    path('path/no-param',
        test_no_param_view,
        name='path-no-param',
        staticsite_path=True,
        staticsite_urls_generator=test_no_param_func),
    path('path/no-func',
        test_no_param_view,
        name='path-no-param-no-func',
        staticsite_path=True),
    path('path/positional-param/<param>',
        test_positional_param_view,
        name='path-positional-param',
        staticsite_path=True,
        staticsite_urls_generator=test_positional_param_func),
    path('path/positional-override-filename/<param>',
        test_positional_param_view,
        name='path-positional-param-custom',
        staticsite_path=True,
        staticsite_urls_generator=test_positional_param_func,
        staticsite_filename="path/x/{}.html"),
    path('path/named-param/<str:param>',
        test_named_param_view,
        name='path-named-param',
        staticsite_path=True,
        staticsite_urls_generator=test_named_param_func),
    path('path/named-override-filename/<str:param>',
        test_named_param_view,
        name='path-named-param-custom',
        staticsite_path=True,
        staticsite_urls_generator=test_named_param_func,
        staticsite_filename="path/x/{param}.html"),
    path('path/broken',
        test_broken_view,
        name='path-broken',
        staticsite_path=True,
        staticsite_urls_generator=test_no_param_func),
    path('path/ignore-sessions',
        test_session_view,
        name='path-ignore-sessions',
        staticsite_path=True,
        staticsite_urls_generator=test_no_param_func),
    path('path/404',
        test_http404_view,
        name='path-404',
        staticsite_status_codes=(404,),
        staticsite_path=True,
        staticsite_urls_generator=test_no_param_func),
    path('path/flatpage<path:url>',
        flatpage_view,
        name='path-flatpage',
        staticsite_path=True,
        staticsite_urls_generator=test_flatpages_func),
    path('path/sitemap',
        sitemap,
        {'sitemaps': sitemap_dict},
        name='path-sitemap',
        staticsite_path=True),
    path('path/kwargs',
        view=test_no_param_view,
        name='test-kwargs',
        staticsite_path=True),
    path('path/humanize',
        test_humanize_view,
        name='test-humanize',
        staticsite_path=True),
    path('path/has-resolver-match',
        test_request_has_resolver_match_view,
        name="test-has-resolver-match",
        staticsite_path=True
    ),

]
