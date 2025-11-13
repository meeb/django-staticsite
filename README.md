# django-staticsite

A reference implementation of a `staticsite` contrib module for Django.

This module is currently under development but is functional and ready for testing. Django Static Site is a complete
ground up rebuild of `django-distill`.

`django-staticsite` allows you to generate static sites from Django sites. You can generate full sites to a specified
directory or genereate individual pages on demand. You can also optionally automatically publish generated static sites
to a configured remote publishing target, for example, Amazon S3 (or any compatible service).

`django-staticsite` is compatible with on-push CI building of static sites allowing for "serverless" Django static
sites with minimal effort.

This is a reference project designed to show implementation and guage interest. It can be used as a basis for a clean
PR, if deemed appropriate, in the future. Django Distill has been a third party module for many years and proven to be
quite popular, potentially the most widely used static site generator framework for Django. Adding its features as an
optional contrib module would be a logical and useful extension to the "batteries included" available contrib features.

It does not add any excessive complexity, the code should be easily understood and be maintainable.


# Notable changes from Django Distill

* Usage of the Django test framework has been replaced with internal WSGI requests
* Modernisation of the codebase, removal of legacy Python and legacy Django support
* Type hints and linted (with ruff) and packaged via uv
* Improved test coverage
* Broadly compatible with the logic and implementation of Django Distill
* Switch to using patched `URLPattern`s rather than custom `path(...)` overrides
* Consolidation of commands into a single `staticsite` command
* Full support for the same publishing targets as Django Distill
* Full compatability when integrated with other contrib modules, such as `humanize`, `sitemaps`, `flatpages` etc.


# Installation for testing

1. Install via pip, uv, poetry, etc. `uv add django-staticsite git+https://github.com/meeb/django-staticsite.git`
2. Add to `django-staticsite` to `INSTALLED_APPS`
3. Create your static site URL generator functions 
4. Add `staticsite_*` arguments to your URLs in `urls.py`
5. Create your static site with the `manage.py staticsite generate` command


# Steps required for further integration

Django StaticSite, if integrated as a contrib module, would need some minor additional parameters added to `URLPattern`
classes to store some addtional static URL information. Currently, for testing, this is implemented via some monkey
patching to have a working implementation without requiring core Django patches. The suggested additions have no impact
on existing sites, no changes to existing APIs and no impact on performance.
