"""Storage backends for telemetry data.

Supports both local file storage (development) and Cloudflare KV (production).
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from src.telemetry.schema import TelemetryEvent


class TelemetryStorage(ABC):
    """Abstract base class for telemetry storage backends."""

    @abstractmethod
    async def store(self, event: TelemetryEvent) -> None:
        """Store a telemetry event (async).

        Args:
            event: Telemetry event to store
        """
        pass

    @abstractmethod
    def store_sync(self, event: TelemetryEvent) -> None:
        """Store a telemetry event (synchronous).

        Args:
            event: Telemetry event to store
        """
        pass

    @abstractmethod
    def has_input(self, input_hash: str) -> bool:
        """Check if an input hash already exists (for deduplication).

        Args:
            input_hash: SHA-256 hash of input description

        Returns:
            True if input hash exists, False otherwise
        """
        pass


class LocalFileStorage(TelemetryStorage):
    """Local file-based storage for telemetry (development/testing).

    Stores events as JSON files in a directory, with one file per event.
    Also maintains an index of input hashes for fast deduplication checks.
    """

    def __init__(self, storage_dir: Path | str = "/tmp/hedit-telemetry"):
        """Initialize local file storage.

        Args:
            storage_dir: Directory to store telemetry files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Index file for input hashes (for fast deduplication)
        self.index_file = self.storage_dir / "input_hashes.json"
        self._input_hashes = self._load_index()

    def _load_index(self) -> set[str]:
        """Load input hash index from disk.

        Returns:
            Set of input hashes
        """
        if not self.index_file.exists():
            return set()

        try:
            with open(self.index_file) as f:
                data = json.load(f)
                return set(data.get("hashes", []))
        except (json.JSONDecodeError, OSError):
            return set()

    def _save_index(self) -> None:
        """Save input hash index to disk."""
        try:
            with open(self.index_file, "w") as f:
                json.dump({"hashes": list(self._input_hashes)}, f)
        except OSError:
            pass  # Ignore write errors

    async def store(self, event: TelemetryEvent) -> None:
        """Store a telemetry event (async wrapper).

        Args:
            event: Telemetry event to store
        """
        self.store_sync(event)

    def store_sync(self, event: TelemetryEvent) -> None:
        """Store a telemetry event.

        Saves event to JSON file and updates index.

        Args:
            event: Telemetry event to store
        """
        # Save event to file
        event_file = self.storage_dir / f"{event.event_id}.json"
        try:
            with open(event_file, "w") as f:
                json.dump(event.to_dict(), f, indent=2)
        except OSError:
            pass  # Ignore write errors

        # Update index
        self._input_hashes.add(event.input_hash)
        self._save_index()

    def has_input(self, input_hash: str) -> bool:
        """Check if an input hash exists.

        Args:
            input_hash: SHA-256 hash of input description

        Returns:
            True if hash exists in index
        """
        return input_hash in self._input_hashes


class CloudflareKVStorage(TelemetryStorage):
    """Cloudflare Workers KV storage for telemetry (production).

    Stores events in Cloudflare KV with hash-based keys for deduplication.
    """

    def __init__(
        self,
        account_id: str,
        namespace_id: str,
        api_token: str,
    ):
        """Initialize Cloudflare KV storage.

        Args:
            account_id: Cloudflare account ID
            namespace_id: KV namespace ID
            api_token: Cloudflare API token
        """
        self.account_id = account_id
        self.namespace_id = namespace_id
        self.api_token = api_token
        self.base_url = (
            f"https://api.cloudflare.com/client/v4/"
            f"accounts/{account_id}/storage/kv/namespaces/{namespace_id}"
        )

    async def store(self, event: TelemetryEvent) -> None:
        """Store a telemetry event in Cloudflare KV.

        Args:
            event: Telemetry event to store
        """
        import httpx

        headers = {"Authorization": f"Bearer {self.api_token}"}
        key = event.to_kv_key()
        value = json.dumps(event.to_dict())

        async with httpx.AsyncClient() as client:
            await client.put(
                f"{self.base_url}/values/{key}",
                headers=headers,
                content=value,
            )

    def store_sync(self, event: TelemetryEvent) -> None:
        """Store a telemetry event in Cloudflare KV (synchronous).

        Args:
            event: Telemetry event to store
        """
        import httpx

        headers = {"Authorization": f"Bearer {self.api_token}"}
        key = event.to_kv_key()
        value = json.dumps(event.to_dict())

        with httpx.Client() as client:
            client.put(
                f"{self.base_url}/values/{key}",
                headers=headers,
                content=value,
            )

    def has_input(self, input_hash: str) -> bool:
        """Check if an input hash exists in KV.

        Performs a list operation with prefix match.

        Args:
            input_hash: SHA-256 hash of input description

        Returns:
            True if any key with this input hash exists
        """
        import httpx

        headers = {"Authorization": f"Bearer {self.api_token}"}
        prefix = f"telemetry:{input_hash}:"

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.base_url}/keys",
                    headers=headers,
                    params={"prefix": prefix, "limit": 1},
                )
                response.raise_for_status()
                data = response.json()
                return len(data.get("result", [])) > 0
        except (httpx.HTTPError, json.JSONDecodeError):
            return False  # Assume no duplicate on error
