from pathlib import Path

from mac_cleaner.domain.sizes import CancellationToken, SizeCache, path_size, size_many


def test_size_cache_hits(tmp_path: Path):
    cache = SizeCache()
    f = tmp_path / "a.bin"
    f.write_bytes(b"hello")
    assert path_size(f, cache=cache) == 5
    assert cache.get(f) == 5
    # Second call uses cache
    assert path_size(f, cache=cache) == 5


def test_size_many_and_cancel(tmp_path: Path):
    paths = []
    for i in range(5):
        p = tmp_path / f"d{i}"
        p.mkdir()
        (p / "f").write_bytes(b"x" * 10)
        paths.append(p)
    token = CancellationToken()
    results = size_many(paths, cancel=token.as_check(), cache=SizeCache(), max_workers=2)
    assert len(results) == 5
    assert all(v == 10 for v in results.values())
