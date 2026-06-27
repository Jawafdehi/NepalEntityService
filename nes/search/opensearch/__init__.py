"""OpenSearch backend package.

The backend class is imported lazily by the factory to avoid importing the
optional ``opensearch-py`` dependency at module load time.
"""

__all__ = ["OpenSearchBackend"]


def __getattr__(name: str):
    if name == "OpenSearchBackend":
        from nes.search.opensearch.backend import OpenSearchBackend

        return OpenSearchBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
