from django.http import HttpResponse
from django.urls import path


app_name = "i18n"


def test_url_i18n_view(request):
    return HttpResponse(b"test", content_type="application/octet-stream")


def test_no_param_func():
    return None


urlpatterns = [
    path(
        "sub-url-with-i18n-prefix",
        test_url_i18n_view,
        name="test-url-i18n",
        staticsite_path=True,
        staticsite_urls_generator=test_no_param_func,
    ),
]
