from types import FunctionType
from functools import partial
from django import urls
from django.urls.resolvers import RegexPattern, RoutePattern
from django.apps import AppConfig
from django.urls import conf, resolvers, URLPattern, URLResolver
from django.core.exceptions import ImproperlyConfigured
from staticsite.utils import iter_url_patterns
from staticsite.urls import add_staticsite_url


class StaticSiteConfig(AppConfig):

    name = 'staticsite'

    def ready(self) -> None:

        """
        Monkeypatch path and re_path, currently this patches _path. This needs a "clean" upstream implementation. This
        is only as a functional demonstration without patching the upstream codebase.

        This also adds new attributes to the URLPattern objects to store the required data for static site generation.
        """

        def _staticsite_path(route: str, view: FunctionType, kwargs: dict | None = None, name: str =None,
                             staticsite_path: str = False, staticsite_urls_generator: FunctionType = None,
                             staticsite_filename: str = None, staticsite_status_codes: tuple[int] | None = None,
                             Pattern: RegexPattern | RoutePattern | None = None) -> URLResolver | URLPattern:
            pattern_or_resolver = conf._path(route, view, kwargs, name, Pattern=Pattern)
            if staticsite_path and isinstance(pattern_or_resolver, resolvers.URLPattern):
                if not staticsite_urls_generator:
                    staticsite_urls_generator = lambda: None
                if not staticsite_status_codes:
                    staticsite_status_codes = (200,)
                if not callable(staticsite_urls_generator):
                    raise ImproperlyConfigured('When registering a static site path the URLs generator argument "staticsite_urls_generator" must be None or a callable')
                if not name:
                    raise ImproperlyConfigured('When registering a static site path the "name" argument must be provided')
                if not staticsite_filename is None and not isinstance(staticsite_filename, str):
                    raise ImproperlyConfigured('When registering a static site path the "staticsite_filename" argument must None or a string')
                if not all(isinstance(status_code, int) for status_code in staticsite_status_codes):
                    raise ImproperlyConfigured('When registering a static site path the "staticsite_status_codes" argument must None or an iterable of integers')
                # resolvers.URLPattern needs some additional attributes to store the staticsite details
                setattr(pattern_or_resolver, 'is_static', True)
                setattr(pattern_or_resolver, 'staticsite_namespace', None)
                setattr(pattern_or_resolver, 'staticsite_urls_generator', staticsite_urls_generator)
                setattr(pattern_or_resolver, 'staticsite_filename', staticsite_filename)
                setattr(pattern_or_resolver, 'staticsite_status_codes', staticsite_status_codes)
            return pattern_or_resolver

        urls.conf.path = partial(_staticsite_path, Pattern=RoutePattern)
        urls.conf.re_path = partial(_staticsite_path, Pattern=RegexPattern)
        urls.path = urls.conf.path
        urls.re_path = urls.conf.re_path

        """
        Iterate all loaded URLs and store any URLs defined as a staticsite path.
        """

        for pattern, namespace in iter_url_patterns():
            if pattern.is_static:
                # Make sure the staticsite path knows its namespace
                pattern.staticsite_namespace = namespace
                add_staticsite_url(pattern)
