import hashlib

from app.redis_client import get_redirect_key, get_link_key, get_search_key


class TestGetRedirectKey:
    def test_returns_correct_format(self):
        key = get_redirect_key("abc123")
        assert key == "redirect:abc123"

    def test_with_special_characters(self):
        key = get_redirect_key("test-123")
        assert key == "redirect:test-123"


class TestGetLinkKey:
    def test_returns_correct_format(self):
        key = get_link_key("abc123")
        assert key == "link:abc123"


class TestGetSearchKey:
    def test_returns_md5_hash_format(self):
        url = "https://example.com"
        key = get_search_key(url)
        assert key.startswith("search:")
        assert len(key) == len("search:") + 32

    def test_same_url_produces_same_key(self):
        url = "https://example.com"
        key1 = get_search_key(url)
        key2 = get_search_key(url)
        assert key1 == key2

    def test_different_urls_produce_different_keys(self):
        key1 = get_search_key("https://example.com")
        key2 = get_search_key("https://other.com")
        assert key1 != key2

    def test_hash_is_correct(self):
        url = "https://example.com"
        expected_hash = hashlib.md5(url.encode()).hexdigest()
        key = get_search_key(url)
        assert key == f"search:{expected_hash}"
