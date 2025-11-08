import os
import warnings
import tempfile
from sys import stderr
from binascii import hexlify
from types import ModuleType, FunctionType
from importlib import import_module
from pathlib import Path
from hashlib import md5
from mimetypes import guess_file_type
from urllib.parse import urlsplit, urlunsplit
from http.client import HTTPConnection, HTTPSConnection
from django.conf import settings
from .errors import StaticSitePublishError
from .static import filter_static_dirs


def check_publisher_dependencies(
    required_by: str, module_name: str, package_name: str = None
) -> ModuleType:
    try:
        return import_module(module_name, package_name)
    except ImportError:
        stderr.write(
            f'Static site backend "{required_by}" requires module "{module_name}" to be installed'
        )
        raise


def get_publisher(engine_name: str) -> ModuleType:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return import_module(engine_name, "backend_class")
        except ImportError as e:
            stderr.write(
                f'Static site backend "{engine_name}" not found or failed to import: {e}'
            )
            raise


def get_publisher_from_options(options: dict) -> ModuleType:
    engine_name = options.get("ENGINE")
    if not engine_name:
        raise StaticSitePublishError(
            "Static site publishing target does not have an ENGINE defined"
        )
    return get_publisher(engine_name)


"""
class Command(BaseCommand):

    help = 'Tests a distill publishing target'

    def add_arguments(self, parser):
        parser.add_argument('publish_target_name', nargs='?', type=str)

    def handle(self, *args, **options):
        publish_target_name = options.get('publish_target_name')
        if not publish_target_name:
            publish_target_name = 'default'
        publish_targets = getattr(settings, 'DISTILL_PUBLISH', {})
        publish_target = publish_targets.get(publish_target_name)
        if type(publish_target) != dict:
            e = 'Invalid publish target name: "{}"'.format(publish_target_name)
            e += ', check your settings.DISTILL_PUBLISH values'
            raise CommandError(e)
        publish_engine = publish_target.get('ENGINE')
        if not publish_engine:
            e = 'Publish target {} has no ENGINE'.format(publish_target_name)
            raise CommandError(e)
        self.stdout.write('')
        self.stdout.write('You have requested to test a publishing target:')
        self.stdout.write('')
        self.stdout.write('    Name:   {}'.format(publish_target_name))
        self.stdout.write('    Engine: {}'.format(publish_engine))
        self.stdout.write('')
        ans = input('Type \'yes\' to continue, or \'no\' to cancel: ')
        if ans.lower() == 'yes':
            self.stdout.write('')
            self.stdout.write('Testing publishing target...')
        else:
            raise CommandError('Testing publishing target cancelled.')
        self.stdout.write('')
        self.stdout.write('Connecting to backend engine')
        backend_class = get_backend(publish_engine)
        random_file = NamedTemporaryFile(delete=False)
        random_str = hexlify(os.urandom(16))
        random_file.write(random_str)
        random_file.close()
        backend = backend_class(os.path.dirname(random_file.name),
                                publish_target)
        self.stdout.write('Authenticating')
        backend.authenticate()
        remote_file_name = os.path.basename(random_file.name)
        self.stdout.write('Uploading test file: {}'.format(random_file.name))
        backend.upload_file(random_file.name, remote_file_name)
        url = backend.remote_url(random_file.name)
        self.stdout.write('Verifying remote test file: {}'.format(url))
        if backend.check_file(random_file.name, url):
            self.stdout.write('File uploaded correctly, file hash is correct')
        else:
            msg = 'File error, remote file hash differs from local hash'
            self.stderr.write(msg)
        self.stdout.write('Final checks')
        backend.final_checks()
        self.stdout.write('Deleting remote test file')
        backend.delete_remote_file(remote_file_name)
        if os.path.exists(random_file.name):
            self.stdout.write('Deleting local test file')
            os.unlink(random_file.name)
        self.stdout.write('')
        self.stdout.write('Backend testing complete.')
"""


def get_publishing_targets() -> dict:
    return getattr(settings, "STATICSITE_PUBLISHING_TARGETS", {})


def get_publishing_target(target_name: str) -> dict:
    try:
        return get_publishing_targets()[target_name]
    except KeyError:
        raise StaticSitePublishError(
            f'Static stite publishing target "{target_name}" not defined, '
            f"check your settings.STATICSITE_PUBLISHING_TARGETS"
        )


class PublisherBackendBase(object):
    """Generic base class for all backends, mostly an interface / template."""

    REQUIRED_OPTIONS = ("PUBLIC_URL",)
    HTTP_TIMEOUT = 10

    def __init__(self, source_dir: Path | str, options: dict) -> None:
        if isinstance(source_dir, str):
            source_dir = Path(source_dir)
        if not isinstance(source_dir, Path):
            raise StaticSitePublishError(
                f"Publishing source directory must be a str or Path, got: {type(source_dir)}"
            )
        if not source_dir.is_dir():
            raise StaticSitePublishError(
                f"Publishing source directory does not exist: {source_dir}"
            )
        self.source_dir = source_dir
        self.options = options
        self.local_files = set()
        self.local_dirs = set()
        self.remote_files = set()
        self.remote_url_parts = urlsplit(options.get("PUBLIC_URL", ""))
        self.d = {}
        self.validate_options()

    def validate_options(self) -> None:
        for o in self.REQUIRED_OPTIONS:
            if o not in self.options:
                raise StaticSitePublishError(
                    f"Missing required settings value for the specified "
                    f"static site publishing backend: {o}"
                )

    def index_local_files(self) -> None:
        for root, dirs, files in self.source_dir.walk():
            dirs[:] = filter_static_dirs(dirs)
            for d in dirs:
                self.local_dirs.add(root / d)
            for f in files:
                self.local_files.add(root / f)

    def get_local_file_hash(
        self,
        file_path: Path | str,
        digest_func: FunctionType = md5,
        chunk: int = 1048576,
    ) -> bool | str:
        if not self.file_exists(file_path):
            raise StaticSitePublishError(
                f"Local static site file does not exist: {file_path}"
            )
        # md5 is used by Amazon S3 and Google Storage
        digest = digest_func()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                digest.update(data)
        return digest.hexdigest()

    def get_url_hash(
        self, url: str, digest_func: FunctionType = md5, chunk: int = 1024
    ) -> bool | str:
        # CDN cache buster
        url += "?" + hexlify(os.urandom(16)).decode("utf-8")
        url_parts = urlsplit(url)
        protocol = url_parts.scheme.strip().lower()
        if protocol == "http":
            http_connector, http_port = HTTPConnection, 80
        elif protocol == "https":
            http_connector, http_port = HTTPSConnection, 443
        else:
            raise StaticSitePublishError(f'Unsupported URL protocol "{protocol}"')
        connection = http_connector(url, http_port, self.HTTP_TIMEOUT)
        connection.request("GET", url_parts.path, headers={"Host": url_parts.netloc})
        response = connection.getresponse()
        if response.status == 404:
            return False
        digest = digest_func()
        while block := response.read(4096):
            if block:
                digest.update(block)
        return digest.hexdigest()

    def file_exists(self, file_path: Path | str) -> bool:
        if isinstance(file_path, str):
            file_path = Path(file_path)
        if not isinstance(file_path, Path):
            raise StaticSitePublishError(
                f"File path must be a str or Path, got: {type(file_path)}"
            )
        return file_path.is_file()

    def detect_local_file_mimetype(
        self, local_name: Path | str, default_mimetype: str = "application/octet-stream"
    ) -> str:
        if isinstance(local_name, str):
            local_name = Path(local_name)
        try:
            mimetype = guess_file_type(local_name)[0]
        except Exception as e:
            raise StaticSitePublishError(
                f"Failed to guess mimetype for {local_name}: {e}"
            ) from e
        return mimetype if mimetype is not None else default_mimetype

    def generate_remote_url(self, local_name: Path | str):
        if isinstance(local_name, str):
            local_name = Path(local_name)
        if not isinstance(local_name, Path):
            raise StaticSitePublishError(
                f"File path must be a str or Path, got: {type(local_name)}"
            )
        if not local_name.is_relative_to(self.source_dir):
            raise StaticSitePublishError(
                f'Local static site file "{local_name}" is not '
                f'in source dir "{self.source_dir}"'
            )
        remote_path_prefix = self.remote_url_parts.path
        if remote_path_prefix.startswith("/"):
            remote_path_prefix = remote_path_prefix[1:]
        remote_uri = remote_path_prefix + self.remote_path(local_name)
        return urlunsplit(
            (
                self.remote_url_parts.scheme,
                self.remote_url_parts.netloc,
                remote_uri,
                "",
                "",
            )
        )

    def get_local_dirs(self) -> set[str]:
        return self.local_dirs

    def get_local_files(self) -> set[str]:
        return self.local_files

    def check_file(self, local_name: Path | None, url: str) -> bool:
        if not self.file_exists(local_name):
            raise StaticSitePublishError(
                f"Local static site file does not exist: {local_name}"
            )
        local_hash = self.get_local_file_hash(local_name)
        remote_hash = self.get_url_hash(url)
        return local_hash == remote_hash

    def final_checks(self) -> None:
        pass

    def remote_path(self, local_name: Path | str) -> str:
        if isinstance(local_name, str):
            local_name = Path(local_name)
        remote_path = Path("/") / local_name.relative_to(self.source_dir)
        return str(remote_path).replace(os.sep, "/")

    def account_username(self) -> str:
        raise NotImplementedError("account_username must be implemented")

    def account_container(self) -> str:
        raise NotImplementedError("account_container must be implemented")

    def authenticate(self) -> bool:
        raise NotImplementedError("authenticate must be implemented")

    def list_remote_files(self) -> set[str]:
        raise NotImplementedError("list_remote_files must be implemented")

    def delete_remote_file(self, remote_name: str) -> bool:
        raise NotImplementedError("delete_remote_file must be implemented")

    def compare_file(self, local_name: Path | str, remote_name: str) -> bool:
        raise NotImplementedError("compare_file must be implemented")

    def upload_file(self, local_name: Path | str, remote_name: str) -> bool:
        raise NotImplementedError("upload_file must be implemented")

    def create_remote_dir(self, remote_dir_name: str) -> bool:
        raise NotImplementedError("create_remote_dir must be implemented")
