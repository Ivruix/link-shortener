import pytest
import string
from app.utils import generate_short_code


class TestGenerateShortCode:
    def test_default_length_is_six(self):
        code = generate_short_code()
        assert len(code) == 6

    def test_returns_string(self):
        code = generate_short_code()
        assert isinstance(code, str)

    def test_custom_length_three(self):
        code = generate_short_code(length=3)
        assert len(code) == 3

    def test_custom_length_ten(self):
        code = generate_short_code(length=10)
        assert len(code) == 10

    def test_custom_length_twenty(self):
        code = generate_short_code(length=20)
        assert len(code) == 20

    def test_all_characters_alphanumeric(self):
        code = generate_short_code()
        allowed_chars = set(string.ascii_letters + string.digits)
        assert all(c in allowed_chars for c in code)

    def test_uniqueness_across_multiple_generations(self):
        codes = {generate_short_code() for _ in range(100)}
        assert len(codes) > 95

    def test_edge_case_length_one(self):
        code = generate_short_code(length=1)
        assert len(code) == 1
        assert code in string.ascii_letters + string.digits

    def test_edge_case_large_length(self):
        code = generate_short_code(length=100)
        assert len(code) == 100
        assert all(c in string.ascii_letters + string.digits for c in code)
