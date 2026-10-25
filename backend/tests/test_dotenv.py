from app.config import _clean_value


def test_inline_comment_is_not_part_of_the_value():
    assert _clean_value("abc123 # second key from project B") == "abc123"
    assert _clean_value("abc123\t# note") == "abc123"
    assert _clean_value("  abc123  ") == "abc123"


def test_quotes_are_removed_and_hash_inside_quotes_is_kept():
    assert _clean_value('"abc123"') == "abc123"
    assert _clean_value("'ab#c12'") == "ab#c12"
    assert _clean_value('"abc123" # comment') == "abc123"


def test_plain_values_unchanged():
    assert _clean_value("gemini-2.5-flash") == "gemini-2.5-flash"
    assert _clean_value("http://localhost:5173,http://127.0.0.1:5173") == "http://localhost:5173,http://127.0.0.1:5173"
    assert _clean_value("") == ""
