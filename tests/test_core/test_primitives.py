from pathlib import Path
from michigram.core.primitives import atomic_write, now_iso, estimate_tokens, sha256_short


def test_atomic_write(tmp_path):
    p = tmp_path / "test.txt"
    atomic_write(p, "hello")
    assert p.read_text() == "hello"


def test_atomic_write_overwrites(tmp_path):
    p = tmp_path / "test.txt"
    atomic_write(p, "first")
    atomic_write(p, "second")
    assert p.read_text() == "second"


def test_atomic_write_creates_parents(tmp_path):
    p = tmp_path / "a" / "b" / "c.txt"
    atomic_write(p, "deep")
    assert p.read_text() == "deep"


def test_now_iso():
    ts = now_iso()
    assert "T" in ts
    assert ts.endswith("Z") or "+" in ts


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 100) == 25


def test_estimate_tokens_word_bound():
    assert estimate_tokens("hello world foo bar") == 4
    assert estimate_tokens("/usr/local/bin/python /tmp/test.py") >= 2


def test_estimate_tokens_uses_max():
    long_words = "superlongword anotherlongword"
    result = estimate_tokens(long_words)
    assert result == max(len(long_words.split()), len(long_words) // 4)


def test_sha256_short():
    h = sha256_short("hello")
    assert len(h) == 12
    assert sha256_short("hello") == sha256_short("hello")
    assert sha256_short("hello") != sha256_short("world")


def test_sha256_short_custom_length():
    assert len(sha256_short("test", length=8)) == 8
