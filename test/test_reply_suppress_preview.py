import pytest

from process_reply import suppress_url

URLS = [
    "http://a/",
    "https://aa",
    "http://aaa.aaa.aaa/aaa/aaa",
    "https://www.google.com/",
    "https://github.com",
    "https://aaa>",
]

NOT_URLS = [
    "https://",
    "http://a",
    "www.google.com",
    "google.com",
    "<https://www.google.com/>",
]


@pytest.mark.parametrize("url", URLS)
def test_suppress_url(url: str) -> None:
    assert suppress_url(url) == f"<{url}>"


@pytest.mark.parametrize("not_url", NOT_URLS)
def test_dont_suppress_not_url(not_url: str) -> None:
    assert suppress_url(not_url) == not_url


@pytest.mark.parametrize("url", URLS)
def test_suppress_url_in_msg(url: str) -> None:
    message = f"aaa {url} aaa"
    assert suppress_url(message) == f"aaa <{url}> aaa"


@pytest.mark.parametrize("url", URLS)
def test_suppress_url_adjacent_to_text(url: str) -> None:
    message = f"aaa{url}aaa"
    expected = f"aaa<{url}aaa>"
    assert suppress_url(message) == expected


@pytest.mark.parametrize("not_url", NOT_URLS)
def test_dont_suppress_url_in_msg(not_url: str) -> None:
    message = f"aaa {not_url} aaa"
    assert suppress_url(message) == message


def test_open_lbracket() -> None:
    message = "<https://www.google.com"
    expected = "<<https://www.google.com>"
    assert suppress_url(message) == expected


def test_multiple_urls() -> None:
    message = " aaa ".join(URLS)
    expected = f"<{'> aaa <'.join(URLS)}>"
    assert suppress_url(message) == expected


@pytest.mark.parametrize("url", URLS)
@pytest.mark.parametrize("not_url", NOT_URLS)
def test_mix_urls_not_urls(url: str, not_url: str) -> None:
    message = f"aaa {url} aaa {not_url}"
    expected = f"aaa <{url}> aaa {not_url}"
    assert suppress_url(message) == expected
