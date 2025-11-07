class StaticSiteError(Exception):
    """Base class for all staticsite errors."""

    pass


class StaticSiteWarning(RuntimeWarning):
    """Base class for all staticsite warnings."""

    pass


class StaticSitePublishError(StaticSiteError):
    """Raised when there is an error publishing a static site."""

    pass


class StaticSiteRenderError(StaticSiteError):
    """Raised when there is an error rendering a static site."""

    pass
