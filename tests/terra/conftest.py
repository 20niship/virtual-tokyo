import importlib.util

# terra の追加依存(uv sync --extra terra)が無い環境ではテストを収集しない
if any(importlib.util.find_spec(m) is None for m in ("numba", "rasterio", "yaml")):
    collect_ignore_glob = ["test_*.py"]
