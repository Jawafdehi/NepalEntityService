"""Unit tests for OpenSearchBackend behaviors that don't need a live engine.

These use lightweight fakes to exercise the review-driven hardening: URL-embedded
credentials, concurrent-creation tolerance in ensure_index, the ICU fallback,
and the short write timeout on single-document writes.
"""

import pytest

from nes.search.opensearch.backend import (
    OpenSearchBackend,
    _is_already_exists_error,
    _is_missing_icu_error,
)
from nes.search.opensearch.client import resolve_connection_params


class _FakeIndices:
    def __init__(self, exists=False, create_error=None):
        self._exists = exists
        self._create_error = create_error
        self.create_calls = 0

    async def exists(self, index):
        return self._exists

    async def create(self, index, body):
        self.create_calls += 1
        if self._create_error is not None:
            err = self._create_error
            # Raise the first error once, then succeed on retry.
            self._create_error = None
            raise err


class _FakeClient:
    def __init__(self, indices):
        self.indices = indices
        self.index_calls = []
        self.delete_calls = []

    async def index(self, **kwargs):
        self.index_calls.append(kwargs)

    async def delete(self, **kwargs):
        self.delete_calls.append(kwargs)
        return {"result": "deleted"}


class TestUrlEmbeddedCredentials:
    def test_credentials_in_url_used(self):
        params = resolve_connection_params("http://admin:secret@os-host:9200")
        assert params.host == "os-host"
        assert params.port == 9200
        assert params.http_auth == ("admin", "secret")

    def test_explicit_args_win_over_url(self):
        params = resolve_connection_params(
            "http://urluser:urlpass@os-host:9200",
            user="explicit",
            password="explicitpass",
        )
        assert params.http_auth == ("explicit", "explicitpass")

    def test_no_credentials_means_no_auth(self):
        params = resolve_connection_params("http://os-host:9200")
        assert params.http_auth is None

    def test_https_defaults_to_ssl_and_443(self):
        params = resolve_connection_params("https://os-host")
        assert params.use_ssl is True
        assert params.port == 443


class TestErrorClassifiers:
    def test_missing_icu_detected(self):
        exc = Exception(
            "Custom Analyzer [ne_text] failed to find tokenizer [icu_tokenizer]"
        )
        assert _is_missing_icu_error(exc) is True

    def test_non_icu_error_not_detected(self):
        assert _is_missing_icu_error(Exception("permission denied")) is False

    def test_already_exists_detected(self):
        exc = Exception("resource_already_exists_exception: index [nes-entities]")
        assert _is_already_exists_error(exc) is True

    def test_unrelated_error_not_already_exists(self):
        assert _is_already_exists_error(Exception("network timeout")) is False


@pytest.mark.asyncio
class TestEnsureIndexConcurrency:
    async def test_already_exists_is_tolerated(self):
        indices = _FakeIndices(
            exists=False,
            create_error=Exception("resource_already_exists_exception"),
        )
        backend = OpenSearchBackend(client=_FakeClient(indices), index="x")
        # Must not raise: a concurrent creator winning the race is fine.
        await backend.ensure_index()
        assert indices.create_calls == 1

    async def test_other_create_error_propagates(self):
        indices = _FakeIndices(
            exists=False, create_error=Exception("permission denied")
        )
        backend = OpenSearchBackend(
            client=_FakeClient(indices), index="x", use_icu=False
        )
        with pytest.raises(Exception, match="permission denied"):
            await backend.ensure_index()

    async def test_icu_fallback_retries_without_icu(self):
        indices = _FakeIndices(
            exists=False,
            create_error=Exception("failed to find tokenizer [icu_tokenizer]"),
        )
        backend = OpenSearchBackend(
            client=_FakeClient(indices), index="x", use_icu=True
        )
        await backend.ensure_index()
        assert backend.use_icu is False
        assert indices.create_calls == 2  # initial + retry


@pytest.mark.asyncio
class TestWriteTimeout:
    async def test_index_passes_write_timeout(self):
        client = _FakeClient(_FakeIndices())
        backend = OpenSearchBackend(client=client, index="x", write_timeout=1.5)
        await backend.index({"id": "entity:person/a"})
        assert client.index_calls[0]["request_timeout"] == 1.5

    async def test_delete_passes_write_timeout(self):
        client = _FakeClient(_FakeIndices())
        backend = OpenSearchBackend(client=client, index="x", write_timeout=1.5)
        await backend.delete("entity:person/a")
        assert client.delete_calls[0]["request_timeout"] == 1.5

    async def test_index_requires_id(self):
        backend = OpenSearchBackend(client=_FakeClient(_FakeIndices()), index="x")
        with pytest.raises(ValueError, match="missing required 'id'"):
            await backend.index({"type": "person"})
