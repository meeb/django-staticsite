from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, quote_plus
from time import sleep
from staticsite.publish import PublisherBackendBase, check_publisher_dependencies
from staticsite.errors import StaticSitePublishError
from binascii import hexlify


BlobServiceClient = check_publisher_dependencies(
    "staticsite.backends.azure_storage", "azure.storage.blob", "BlobServiceClient"
)
BlobClient = check_publisher_dependencies(
    "staticsite.backends.azure_storage", "azure.storage.blob", "BlobClient"
)
ContentSettings = check_publisher_dependencies(
    "staticsite.backends.azure_storage", "azure.storage.blob", "ContentSettings"
)


class AzureBlobStorateBackend(PublisherBackendBase):
    """Publisher for Azure Blob Storage. Azure static websites in containers are relatively
    slow to make the files available via the public URL. To work around this, uploaded files are
    cached and then verified in a loop at the end with up to RETRY_ATTEMPTS attempts with a delay of
    SLEEP_BETWEEN_RETRIES seconds between each attempt."""

    REQUIRED_OPTIONS = ("ENGINE", "CONNECTION_STRING")
    RETRY_ATTEMPTS = 30
    SLEEP_BETWEEN_RETRIES = 3

    def account_username(self) -> str:
        return ""

    def account_container(self) -> str:
        """Azure Blob Storage containers are all named $web for public websites."""
        return "$web"

    def connection_string(self) -> str:
        return self.options.get("CONNECTION_STRING", "")

    def _get_container(self):
        return self.d["connection"].get_container_client(
            container=self.account_container()
        )

    def _get_blob(self, name: str) -> BlobClient:
        return self.d["connection"].get_blob_client(
            container=self.account_container(), blob=name
        )

    def _get_blob_url(self, blob: BlobClient) -> str:
        blob_parts = urlsplit(blob.url)
        prefix = "/{}/".format(quote_plus(self.account_container()))
        path = blob_parts.path
        if path.startswith(prefix):
            path = path[len(prefix) :]
        parts = (
            self.remote_url_parts.scheme,
            self.remote_url_parts.netloc,
            path,
            None,
            None,
        )
        return urlunsplit(parts).decode("utf-8")

    def authenticate(self) -> bool:
        self.d["connection"] = BlobServiceClient.from_connection_string(
            conn_str=self.connection_string()
        )
        return True

    def get_remote_files(self) -> set[str]:
        container = self._get_container()
        rtn = set()
        for obj in container.list_blobs():
            rtn.add(obj.name)
        return rtn

    def delete_remote_file(self, remote_name: str) -> bool:
        container = self._get_container()
        return container.delete_blob(remote_name)

    def check_file(self, local_name: Path | str, url: str) -> bool:
        # Azure uploads are checked in bulk at the end of the uploads, do nothing here
        return True

    def compare_file(self, local_name: Path | str, remote_name: str) -> bool:
        blob = self._get_blob(remote_name)
        properties = blob.get_blob_properties()
        content_md5 = properties.get("content_settings", {}).get("content_md5")
        if not content_md5:
            return False
        local_hash = self._get_local_file_hash(local_name)
        remote_hash = str(hexlify(bytes(content_md5)).decode())
        return local_hash == remote_hash

    def upload_file(self, local_name: Path | str, remote_name: str) -> bool:
        blob = self._get_blob(remote_name)
        mimetype = self.detect_local_file_mimetype(local_name)
        content_settings = ContentSettings(content_type=mimetype)
        with open(local_name, "rb") as data:
            result = blob.upload_blob(
                data, overwrite=True, content_settings=content_settings
            )
            if result:
                actual_url = self._get_blob_url(blob)
                self.d.setdefault("azure_uploads_to_check", []).append(
                    (local_name, remote_name, actual_url)
                )
        return result

    def _check_file(self, local_name: Path | str, actual_url: str) -> bool:
        # Azure specific patched check_file with retries to account for Azure being slow
        local_hash = self._get_local_file_hash(local_name)
        for i in range(self.RETRY_ATTEMPTS):
            remote_hash = self._get_url_hash(actual_url)
            if not remote_hash:
                sleep(self.SLEEP_BETWEEN_RETRIES)
                continue
            if local_hash == remote_hash:
                return True
        raise StaticSitePublishError(
            f'Failed to upload local file "{local_name}" blob to Azure container at '
            f'URL "{actual_url}" not available over the public URL after {i + 1} attempts'
        )

    def final_checks(self) -> bool:
        # Iterate over any cached files to check and verify they have been uploaded correctly.
        to_check = self.d.setdefault("azure_uploads_to_check", [])
        for local_name, remote_name, actual_url in to_check:
            # Verify the upload, this may require retries
            self._check_file(local_name, actual_url)
        # If we reached here, no StaticSitePublishError was raised
        return True

    def create_remote_dir(self, remote_dir_name: str) -> bool:
        # not required for Azure Blob Storage containers
        return True


backend_class = AzureBlobStorateBackend
