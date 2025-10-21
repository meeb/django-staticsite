import errno
from pathlib import Path
from types import TracebackType
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings, global_settings

from django.urls import reverse, NoReverseMatch, URLPattern
from django.utils.translation import activate as activate_lang
from django.db import connection, close_old_connections
#from .logging import get_logger
from .errors import StaticSiteError
from .request import internal_wsgi_request, generate_uri, get_uri_values, get_static_filepath, generate_filename
from .utils import get_header, get_langs


import logging
log = logging.getLogger('main')


def render_uri(
    uri: str,
    status_codes: tuple[int] | list[int]
) -> tuple[int, list[tuple[str, str]], bytes]:
    if not isinstance(status_codes, (tuple, list)):
        status_codes = (200,)
    status, headers, body = internal_wsgi_request(path=uri, method='GET')
    status_parts = status.split(' ', 1)
    try:
        status_code = int(status_parts[0])
    except ValueError:
        raise StaticSiteError(f'Invalid HTTP status: {status} for URI: {uri}')
    if status_code not in status_codes:
        raise StaticSiteError(f'Unexpected HTTP status: {status} for URI: {uri}')
    return status_code, headers, body


def render_pattern(
    pattern: URLPattern,
    param_set: list[str | None] | tuple[str | None],
    uri: str,
    language_code: str | None
) -> tuple[URLPattern, str, str, int, list, bytes]:
    close_old_connections()
    connection.ensure_connection()
    if language_code:
        activate_lang(language_code)
    generated_uri = generate_uri(pattern.staticsite_namespace, pattern.name, param_set)
    status, headers, body = render_uri(uri, pattern.staticsite_status_codes)
    generated_filename = generate_filename(pattern.staticsite_filename, uri, param_set)
    return pattern, generated_uri, generated_filename, status, headers, body


def write_file(
    full_path: Path,
    content: bytes
) -> None:
    try:
        if not full_path.parent.is_dir():
            full_path.parent.mkdir(parents=True)
        with open(full_path, 'wb') as f:
            f.write(content)
    except IOError as e:
        if e.errno == errno.EISDIR:
            err = ('Output path: {} is a directory! Try adding a '
                   '"distill_file" arg to your distill_url()')
            raise StaticSiteError(f'Output path "{full_path}" is a directory. '
                                   'Try adding a "distill_file" arg to your path(...)')
        else:
            raise


class StaticSiteRenderer:

    def __init__(
            self,
            urls_to_render: list[URLPattern],
            hostname: str | None = None,
            enable_debug: bool = True,
            concurrency: int = 1
        ) -> None:
        self._site_debug = settings.DEBUG
        self._site_allowed_hosts = settings.ALLOWED_HOSTS
        self._application = None
        self.urls_to_render = urls_to_render
        self.hostname = hostname
        self.enable_debug = enable_debug
        self.concurrency = concurrency

    def __enter__(
        self
    ) -> StaticSiteRenderer:
        if self.hostname:
            settings.ALLOWED_HOSTS = [self.hostname]
        else:
            # Static sites generally want to ignore hostnames
            settings.ALLOWED_HOSTS = ['*']
        if self.enable_debug:
            settings.DEBUG = True
        return self

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        # Restore any modified settings
        settings.ALLOWED_HOSTS = self._site_allowed_hosts
        settings.DEBUG = self._site_debug

    def get_urls_to_render(
        self
    ) -> list[tuple[URLPattern, list[str | None] | tuple[str | None], str]]:
        to_render = []
        for url in self.urls_to_render:
            for param_set in get_uri_values(url.staticsite_urls_generator, url.name):
                if not param_set:
                    param_set = ()
                elif isinstance(param_set, str):
                    param_set = (param_set,)
                uri = generate_uri(url.staticsite_namespace, url.name, param_set)
                to_render.append((url, param_set, uri))
        return to_render


    def render_all_urls(
        self,
    ) -> Generator[tuple[URLPattern, str, str, int, dict, bytes]]:

        def _render(item):
            rtn = []
            pattern, param_set, uri = item
            for lang in get_langs():
                rtn.append(render_pattern(pattern, param_set, uri, lang))
            return rtn

        if self.concurrency == 1:
            results = map(_render, self.get_urls_to_render())
            for result in results:
                for render in result:
                    # render = (pattern, generated_uri, generated_filename, status, headers, body)
                    yield render
        else:

            with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                results = executor.map(_render, self.get_urls_to_render())
                for result in results:
                    for render in result:
                        # render = (pattern, generated_uri, generated_filename, status, headers, body)
                        yield render

    def render_to_directory(
        self,
        output_dir: Path | str
    ) -> None:
        log.info(f'Rendering static site to directory: {output_dir}')
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)
        if not isinstance(output_dir, Path):
            raise StaticSiteError(f'Invalid output directory: {output_dir}')
        for render in self.render_all_urls():
            pattern, generated_uri, generated_filename, status, headers, body = render
            mime = get_header(headers, 'Content-Type')
            full_path, local_uri = get_static_filepath(output_dir, generated_filename, generated_uri)
            log.info(f'Rendering static page: {local_uri} -> {full_path} ["{mime}", {len(body)} bytes]')
            write_file(Path(full_path), body)
        log.info(f'Rendering static site to directory complete')


'''
def render_to_dir(output_dir, urls_to_distill, stdout, parallel_render=1):
    load_urls(stdout)
    renderer = get_renderer(urls_to_distill, parallel_render)
    for page_uri, file_name, http_response in renderer.render():
        full_path, local_uri = get_filepath(output_dir, file_name, page_uri)
        content = http_response.content
        mime = http_response.get('Content-Type')
        renamed = ' (renamed from "{}")'.format(page_uri) if file_name else ''
        msg = 'Rendering page: {} -> {} ["{}", {} bytes] {}'
        stdout(msg.format(local_uri, full_path, mime, len(content), renamed))
        write_file(full_path, content)
    return True
'''