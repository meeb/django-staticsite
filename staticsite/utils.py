from collections.abc import Generator
from django.conf import settings, global_settings
from django.urls import URLPattern, URLResolver, get_resolver


def set_func_attr(name, value):
    """Decorator for setting an arbitrary function attribute."""

    def decorator(func):
        setattr(func, name, value)
        return func

    return decorator


def iter_url_patterns(
    url_patterns: list | None = None, namespace: str = "", depth: int = 0
) -> Generator[tuple[URLPattern, str | None, int]]:
    """
    Yield tuples of (URLPattern, namespace) for all URLPattern objects in the
    provided Django URLconf, or the default one if none is provided.
    """
    if url_patterns is None:
        url_patterns = get_resolver().url_patterns
    for pattern in url_patterns:
        if isinstance(pattern, URLPattern):
            if depth == 0:
                namespace = None
            yield pattern, namespace, 1
        elif isinstance(pattern, URLResolver):
            if pattern.namespace:
                if namespace:
                    namespace = f"{namespace}:{pattern.namespace}"
                else:
                    namespace = pattern.namespace
            else:
                namespace = None
            yield from iter_url_patterns(pattern.url_patterns, namespace, depth + 1)
        else:
            raise TypeError(f"Unexpected pattern type: {type(pattern)} in {namespace}")


def get_header(headers: list[tuple[str, str]], name: str) -> str | None:
    """Returns the value of a header by name from a list of headers. If multiple headers with the same name exist,
    then return the first one."""
    lower_name = name.lower()
    for header_name, header_value in headers:
        if header_name.lower() == lower_name:
            return header_value
    return None


def get_langs() -> list[str]:
    langs = []
    LANGUAGE_CODE = str(getattr(settings, "LANGUAGE_CODE", "en"))
    GLOBAL_LANGUAGES = list(getattr(global_settings, "LANGUAGES", []))
    try:
        LANGUAGES = list(getattr(settings, "LANGUAGES", []))
    except (ValueError, TypeError, AttributeError):
        LANGUAGES = []
    try:
        STATICSITE_LANGUAGES = list(getattr(settings, "STATICSITE_LANGUAGES", []))
    except (ValueError, TypeError, AttributeError):
        STATICSITE_LANGUAGES = []
    if LANGUAGES != GLOBAL_LANGUAGES:
        for lang_code, lang_name in LANGUAGES:
            langs.append(lang_code)
    if LANGUAGE_CODE not in STATICSITE_LANGUAGES and LANGUAGE_CODE not in langs:
        langs.append(LANGUAGE_CODE)
    for lang in STATICSITE_LANGUAGES:
        langs.append(lang)
    return langs
