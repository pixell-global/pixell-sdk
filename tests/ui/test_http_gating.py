from pixell.ui import ClientCapabilities
from pixell.ui.capabilities import http_method_allowed


def test_http_extended_methods_require_feature() -> None:
    caps = ClientCapabilities(components=["page"])  # no http.extended
    assert http_method_allowed("GET", caps) is True
    assert http_method_allowed("POST", caps) is True
    assert http_method_allowed("PUT", caps) is False
    assert http_method_allowed("PATCH", caps) is False
    assert http_method_allowed("DELETE", caps) is False

    caps2 = ClientCapabilities(components=["page"], features=["http.extended"])  # has extended
    assert http_method_allowed("PUT", caps2) is True
    assert http_method_allowed("PATCH", caps2) is True
    assert http_method_allowed("DELETE", caps2) is True
