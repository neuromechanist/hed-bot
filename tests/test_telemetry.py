"""Tests for telemetry module.

Tests cover:
- Telemetry event creation and schema
- Model blacklist filtering
- Input deduplication
- Storage backends (local file)
"""

import json

from src.telemetry import (
    LocalFileStorage,
    TelemetryCollector,
    TelemetryEvent,
)


class TestTelemetryEvent:
    """Tests for telemetry event creation and schema."""

    def test_create_event(self):
        """Test creating a telemetry event."""
        event = TelemetryEvent.create(
            description="participant pressed button",
            schema_version="8.4.0",
            hed_string="Agent-action, Press",
            iterations=2,
            validation_errors=[],
            model="anthropic/claude-haiku-4.5",
            provider=None,
            temperature=0.1,
            latency_ms=450,
            source="cli",
        )

        assert event.input.description == "participant pressed button"
        assert event.input.schema_version == "8.4.0"
        assert event.output.hed_string == "Agent-action, Press"
        assert event.output.iterations == 2
        assert event.model.model == "anthropic/claude-haiku-4.5"
        assert event.model.temperature == 0.1
        assert event.performance.latency_ms == 450
        assert event.source == "cli"

    def test_input_hash_generation(self):
        """Test input hash generation is consistent."""
        desc = "test description"
        hash1 = TelemetryEvent.hash_input(desc)
        hash2 = TelemetryEvent.hash_input(desc)

        assert hash1 == hash2
        assert len(hash1) == 16
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_input_hash_uniqueness(self):
        """Test different inputs produce different hashes."""
        hash1 = TelemetryEvent.hash_input("description 1")
        hash2 = TelemetryEvent.hash_input("description 2")

        assert hash1 != hash2

    def test_kv_key_generation(self):
        """Test Cloudflare KV key generation."""
        event = TelemetryEvent.create(
            description="test",
            schema_version="8.4.0",
            hed_string="Test",
            iterations=1,
            validation_errors=[],
            model="test/model",
            provider=None,
            temperature=0.1,
            latency_ms=100,
            source="cli",
        )

        kv_key = event.to_kv_key()
        assert kv_key.startswith(f"telemetry:{event.input_hash}:")
        assert event.event_id in kv_key


class TestLocalFileStorage:
    """Tests for local file storage backend."""

    def test_storage_initialization(self, tmp_path):
        """Test storage initialization creates directory."""
        storage_dir = tmp_path / "telemetry"
        storage = LocalFileStorage(storage_dir=storage_dir)

        assert storage.storage_dir.exists()
        # Index file is created on first write, not initialization
        assert storage._input_hashes == set()

    def test_store_event(self, tmp_path):
        """Test storing a telemetry event."""
        storage = LocalFileStorage(storage_dir=tmp_path / "telemetry")
        event = TelemetryEvent.create(
            description="test event",
            schema_version="8.4.0",
            hed_string="Test",
            iterations=1,
            validation_errors=[],
            model="test/model",
            provider=None,
            temperature=0.1,
            latency_ms=100,
            source="cli",
        )

        storage.store_sync(event)

        # Check event file exists
        event_file = storage.storage_dir / f"{event.event_id}.json"
        assert event_file.exists()

        # Check event content
        with open(event_file) as f:
            stored_data = json.load(f)
            assert stored_data["input"]["description"] == "test event"
            assert stored_data["model"]["model"] == "test/model"

    def test_input_hash_indexing(self, tmp_path):
        """Test input hash index is maintained."""
        storage = LocalFileStorage(storage_dir=tmp_path / "telemetry")
        event = TelemetryEvent.create(
            description="indexed event",
            schema_version="8.4.0",
            hed_string="Test",
            iterations=1,
            validation_errors=[],
            model="test/model",
            provider=None,
            temperature=0.1,
            latency_ms=100,
            source="cli",
        )

        storage.store_sync(event)

        # Check hash is in index
        assert storage.has_input(event.input_hash)
        assert not storage.has_input("nonexistent_hash")

    def test_index_persistence(self, tmp_path):
        """Test index persists across storage instances."""
        storage_dir = tmp_path / "telemetry"
        storage1 = LocalFileStorage(storage_dir=storage_dir)

        event = TelemetryEvent.create(
            description="persistent test",
            schema_version="8.4.0",
            hed_string="Test",
            iterations=1,
            validation_errors=[],
            model="test/model",
            provider=None,
            temperature=0.1,
            latency_ms=100,
            source="cli",
        )

        storage1.store_sync(event)
        input_hash = event.input_hash

        # Create new storage instance
        storage2 = LocalFileStorage(storage_dir=storage_dir)
        assert storage2.has_input(input_hash)


class TestTelemetryCollector:
    """Tests for telemetry collector with filtering."""

    def test_collector_initialization(self, tmp_path):
        """Test collector initialization."""
        storage = LocalFileStorage(storage_dir=tmp_path / "telemetry")
        collector = TelemetryCollector(storage=storage, enabled=True)

        assert collector.enabled
        assert "openai/gpt-oss-120b" in collector.model_blacklist

    def test_model_blacklist_filtering(self, tmp_path):
        """Test that blacklisted models are filtered out."""
        storage = LocalFileStorage(storage_dir=tmp_path / "telemetry")
        collector = TelemetryCollector(storage=storage, enabled=True)

        # Blacklisted model
        event1 = TelemetryEvent.create(
            description="test",
            schema_version="8.4.0",
            hed_string="Test",
            iterations=1,
            validation_errors=[],
            model="openai/gpt-oss-120b",  # Blacklisted
            provider=None,
            temperature=0.1,
            latency_ms=100,
            source="cli",
        )

        # Non-blacklisted model
        event2 = TelemetryEvent.create(
            description="test",
            schema_version="8.4.0",
            hed_string="Test",
            iterations=1,
            validation_errors=[],
            model="anthropic/claude-haiku-4.5",  # Not blacklisted
            provider=None,
            temperature=0.1,
            latency_ms=100,
            source="cli",
        )

        assert not collector.should_collect(event1)
        assert collector.should_collect(event2)

    def test_deduplication_filtering(self, tmp_path):
        """Test that duplicate inputs are filtered out."""
        storage = LocalFileStorage(storage_dir=tmp_path / "telemetry")
        collector = TelemetryCollector(storage=storage, enabled=True)

        # First event
        event1 = TelemetryEvent.create(
            description="unique description",
            schema_version="8.4.0",
            hed_string="Test",
            iterations=1,
            validation_errors=[],
            model="anthropic/claude-haiku-4.5",
            provider=None,
            temperature=0.1,
            latency_ms=100,
            source="cli",
        )

        # Second event with same description
        event2 = TelemetryEvent.create(
            description="unique description",  # Same as event1
            schema_version="8.4.0",
            hed_string="Test 2",
            iterations=2,
            validation_errors=[],
            model="anthropic/claude-haiku-4.5",
            provider=None,
            temperature=0.1,
            latency_ms=200,
            source="cli",
        )

        # First event should be collected
        collected1 = collector.collect_sync(event1)
        assert collected1

        # Second event should be filtered (duplicate)
        collected2 = collector.collect_sync(event2)
        assert not collected2

    def test_telemetry_disabled(self, tmp_path):
        """Test that no events are collected when telemetry is disabled."""
        storage = LocalFileStorage(storage_dir=tmp_path / "telemetry")
        collector = TelemetryCollector(storage=storage, enabled=False)

        event = TelemetryEvent.create(
            description="test",
            schema_version="8.4.0",
            hed_string="Test",
            iterations=1,
            validation_errors=[],
            model="anthropic/claude-haiku-4.5",
            provider=None,
            temperature=0.1,
            latency_ms=100,
            source="cli",
        )

        collected = collector.collect_sync(event)
        assert not collected

    def test_custom_model_blacklist(self, tmp_path):
        """Test custom model blacklist."""
        storage = LocalFileStorage(storage_dir=tmp_path / "telemetry")
        custom_blacklist = ["custom/model-1", "custom/model-2"]
        collector = TelemetryCollector(
            storage=storage,
            enabled=True,
            model_blacklist=custom_blacklist,
        )

        event = TelemetryEvent.create(
            description="test",
            schema_version="8.4.0",
            hed_string="Test",
            iterations=1,
            validation_errors=[],
            model="custom/model-1",  # In custom blacklist
            provider=None,
            temperature=0.1,
            latency_ms=100,
            source="cli",
        )

        assert not collector.should_collect(event)


class TestTelemetryIntegration:
    """Integration tests for telemetry system."""

    def test_end_to_end_collection(self, tmp_path):
        """Test complete telemetry flow from creation to storage."""
        storage = LocalFileStorage(storage_dir=tmp_path / "telemetry")
        collector = TelemetryCollector(storage=storage, enabled=True)

        # Collect several events
        events = []
        for i in range(5):
            event = TelemetryEvent.create(
                description=f"event {i}",
                schema_version="8.4.0",
                hed_string=f"Test {i}",
                iterations=1,
                validation_errors=[],
                model="anthropic/claude-haiku-4.5",
                provider=None,
                temperature=0.1,
                latency_ms=100 + i * 10,
                source="cli",
            )
            events.append(event)
            collected = collector.collect_sync(event)
            assert collected

        # Verify all events were stored (excluding index file)
        event_files = [
            f for f in storage.storage_dir.glob("*.json") if f.name != "input_hashes.json"
        ]
        assert len(event_files) == 5

        # Verify all hashes are in index
        for event in events:
            assert storage.has_input(event.input_hash)
