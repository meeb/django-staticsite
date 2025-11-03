from django.core.exceptions import ImproperlyConfigured
from django.urls import URLPattern


staticsite_urls = []
staticsite_urls_by_name = {}


def add_staticsite_url(
        pattern: URLPattern
    ) -> None:
    """ Register a URLPattern as a static site pattern. """
    staticsite_urls.append(pattern)
    staticsite_urls_by_name.setdefault(pattern.staticsite_namespace, {})[pattern.name] = pattern


def get_staticsite_urls() -> list[URLPattern]:
    """ Return a list of all URLPattern objects which have been registered as a static site pattern. """
    return staticsite_urls


def get_staticsite_url_by_name(
        name: str,
        namespace: str | None = None
    ) -> URLPattern:
    """ Return a URLPattern object which has been registered as a static site pattern by name. """
    try:
        return staticsite_urls_by_name[namespace][name]
    except KeyError:
        view_name = f'{namespace}:{name}' if namespace else name
        raise ImproperlyConfigured(f'The view "{view_name}" is not registered as a static site path')
