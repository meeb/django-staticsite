import os
from io import BytesIO
from pathlib import Path
from types import GeneratorType, FunctionType
from inspect import getfullargspec
from urllib.parse import urlencode
from django.core.wsgi import get_wsgi_application
from django.urls import reverse, NoReverseMatch
from .errors import StaticSiteError


def internal_wsgi_request(
        path: str = '/',
        method: str = 'GET',
        data: str | bytes | None = None,
        query_params: dict[str, str] | list[tuple[str, str]] | tuple[tuple[str, str]] | None = None,
        headers: dict | None = None
) -> tuple[str, list[tuple[str, str]], bytes]:
    """ Create a synthetic WSGI request, make the request internally and return the rendered output. """

    # Default WSGI environment
    env = {
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': 80,
        'REQUEST_METHOD': method.upper(),
        'PATH_INFO': path
    }
    # Handle query strings if provided
    if query_params:
        query_string = urlencode(query_params)
        env['QUERY_STRING'] = query_string
    # Handle headers if provided
    if headers:
        for key, value in headers.items():
            key = key.upper().replace('-', '_')
            env[f'HTTP_{key}'] = value
    # Handle POST data if provided
    if method.upper() == 'POST' and data:
        post_data = urlencode(data).encode('utf-8')
        env['CONTENT_LENGTH'] = str(len(post_data))
        env['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        env['wsgi.input'] = BytesIO(post_data)
    else:
        env['wsgi.input'] = BytesIO()
    # Create a Django WSGI application
    application = get_wsgi_application()
    # Submit the internal request and capture the output
    response_headers = []
    response_body = []
    response_statuses = []

    def start_response(status, headers):
        response_statuses.append(status)
        response_headers.extend(headers)
        def write(data):
            response_body.append(data)
        return write

    response_chunks = application(env, start_response)

    # Collect all response chunks
    for chunk in response_chunks:
        if chunk:
            if isinstance(chunk, str):
                response_body.append(chunk.encode('utf-8'))
            else:
                response_body.append(chunk)

    # Confirm there was a single HTTP status returned
    if len(response_statuses) == 1:
        response_status_code = response_statuses[0]
    else:
        raise StaticSiteError(f'Expected a single HTTP status code, got {response_statuses}')

    # Return the rendered HTML
    response_body_bytes = b''.join(response_body)
    return response_status_code, response_headers, response_body_bytes


def get_uri_values(
    func: FunctionType,
    view_name: str
) -> list[str | int | None]:
    """ Call the staticsite_urls_generator function for a view and normalises the result to be a list. """
    fullargspec = getfullargspec(func)
    try:
        if 'view_name' in fullargspec.args:
            v = func(view_name)
        else:
            v = func()
    except Exception as e:
        raise StaticSiteError(f'Failed to call static site render function: {e}') from e
    if not v:
        return (None,)
    if isinstance(v, (list, tuple)):
        return v
    elif isinstance(v, GeneratorType):
        return list(v)
    else:
        raise StaticSiteError(f'Unable to get staticsite URI values, '
                              f'generator function returned an invalid type: {type(v)}')


def generate_uri(
    namespace: str | None,
    view_name: str,
    param_set: list[str | None] | tuple[str | None] | None
) -> str:
    view_name_ns = namespace + ':' + view_name if namespace else view_name
    if param_set is None:
        param_set = ()
    if isinstance(param_set, (list, tuple)):
        try:
            uri = reverse(view_name, args=param_set)
        except NoReverseMatch:
            uri = reverse(view_name_ns, args=param_set)
    elif isinstance(param_set, dict):
        try:
            uri = reverse(view_name, kwargs=param_set)
        except NoReverseMatch:
            uri = reverse(view_name_ns, kwargs=param_set)
    else:
        raise StaticSiteError(f'Unable to generate staticsite URI, '
                              f'URL generator function returned an invalid type: {type(param_set)}')
    return uri


def get_static_filepath(
        output_dir: Path,
        file_name: str,
        page_uri: str
    ) -> tuple[Path, str]:
    """ Returns the full path and local URI for a static file. """
    if file_name:
        local_uri = file_name
        full_path = output_dir / file_name
    else:
        local_uri = page_uri
        if page_uri.startswith('/'):
            page_uri = page_uri[1:]
        page_path = page_uri.replace('/', os.sep)
        full_path = output_dir / page_path
    return full_path, local_uri


def generate_filename(
    file_name: str,
    uri: str,
    param_set: list[str | None] | tuple[str | None]
) -> str | None:
    if file_name is not None:
        if isinstance(param_set, dict):
            return file_name.format(**param_set)
        else:
            return file_name.format(*param_set)
    elif uri.endswith('/'):
        # rewrite URIs ending with a slash to ../index.html
        if uri.startswith('/'):
            uri = uri[1:]
        return uri + 'index.html'
    else:
        return None
