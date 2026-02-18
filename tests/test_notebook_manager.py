"""Tests for NotebookManager — persistent notebook workspaces."""

import json
import os
import shutil

import pytest

from local_notebooklm.notebook_manager import NotebookManager, _DEFAULT_SETTINGS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mgr(tmp_path):
    """Return a NotebookManager rooted in a fresh temp directory."""
    import local_notebooklm.notebook_manager as mod
    original = mod._LEGACY_OUTPUT
    # Point legacy output at a non-existent path so bootstrap creates a default
    mod._LEGACY_OUTPUT = str(tmp_path / "no_legacy_here")
    try:
        yield NotebookManager(base_dir=str(tmp_path / "notebooks"))
    finally:
        mod._LEGACY_OUTPUT = original


@pytest.fixture
def mgr_with_legacy(tmp_path):
    """Set up a fake legacy output dir, then create a manager that should migrate it."""
    legacy = tmp_path / "local_notebooklm" / "web_ui" / "output"
    legacy.mkdir(parents=True)

    # Simulate some legacy pipeline outputs
    step1 = legacy / "step1"
    step1.mkdir()
    (step1 / "extracted_text.txt").write_text("legacy text content")
    (legacy / "podcast.wav").write_bytes(b"RIFF fake wav")

    # We need to monkey-patch _LEGACY_OUTPUT so the manager picks it up
    import local_notebooklm.notebook_manager as mod
    original = mod._LEGACY_OUTPUT
    mod._LEGACY_OUTPUT = str(legacy)
    try:
        manager = NotebookManager(base_dir=str(tmp_path / "notebooks"))
        yield manager, legacy
    finally:
        mod._LEGACY_OUTPUT = original


# ---------------------------------------------------------------------------
# TestNotebookCRUD
# ---------------------------------------------------------------------------


class TestNotebookCRUD:
    def test_bootstrap_creates_default(self, mgr):
        notebooks = mgr.list_notebooks()
        assert len(notebooks) == 1
        assert notebooks[0]["name"] == "My Notebook"
        assert mgr.get_default_notebook_id() == notebooks[0]["id"]

    def test_create_notebook(self, mgr):
        nb_id = mgr.create_notebook("Research Notes")
        notebooks = mgr.list_notebooks()
        assert len(notebooks) == 2
        names = [n["name"] for n in notebooks]
        assert "Research Notes" in names
        # Newly created notebook becomes default
        assert mgr.get_default_notebook_id() == nb_id

    def test_create_notebook_empty_name(self, mgr):
        nb_id = mgr.create_notebook("")
        meta = mgr.get_notebook(nb_id)
        assert meta["name"] == "Untitled Notebook"

    def test_create_notebook_whitespace_name(self, mgr):
        nb_id = mgr.create_notebook("   ")
        meta = mgr.get_notebook(nb_id)
        assert meta["name"] == "Untitled Notebook"

    def test_get_notebook(self, mgr):
        nb_id = mgr.create_notebook("Test NB")
        meta = mgr.get_notebook(nb_id)
        assert meta["name"] == "Test NB"
        assert "created_at" in meta
        assert "settings" in meta
        assert meta["sources"] == []

    def test_get_notebook_nonexistent(self, mgr):
        with pytest.raises(KeyError):
            mgr.get_notebook("nonexistent-id")

    def test_rename_notebook(self, mgr):
        nb_id = mgr.create_notebook("Old Name")
        mgr.rename_notebook(nb_id, "New Name")
        meta = mgr.get_notebook(nb_id)
        assert meta["name"] == "New Name"
        # Registry also updated
        names = [n["name"] for n in mgr.list_notebooks()]
        assert "New Name" in names
        assert "Old Name" not in names

    def test_rename_empty_raises(self, mgr):
        nb_id = mgr.create_notebook("Test")
        with pytest.raises(ValueError):
            mgr.rename_notebook(nb_id, "")

    def test_rename_nonexistent_raises(self, mgr):
        with pytest.raises(KeyError):
            mgr.rename_notebook("bad-id", "New Name")

    def test_delete_notebook(self, mgr):
        nb1_id = mgr.list_notebooks()[0]["id"]
        nb2_id = mgr.create_notebook("Second")
        mgr.delete_notebook(nb2_id)
        notebooks = mgr.list_notebooks()
        assert len(notebooks) == 1
        assert notebooks[0]["id"] == nb1_id

    def test_delete_last_notebook_creates_fresh(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        fresh_id = mgr.delete_notebook(nb_id)
        notebooks = mgr.list_notebooks()
        assert len(notebooks) == 1
        assert notebooks[0]["id"] == fresh_id
        assert notebooks[0]["name"] == "My Notebook"
        assert fresh_id != nb_id

    def test_delete_default_switches(self, mgr):
        first_id = mgr.list_notebooks()[0]["id"]
        second_id = mgr.create_notebook("Second")
        # Default is now second_id
        assert mgr.get_default_notebook_id() == second_id
        next_id = mgr.delete_notebook(second_id)
        assert mgr.get_default_notebook_id() == next_id

    def test_delete_nonexistent_raises(self, mgr):
        with pytest.raises(KeyError):
            mgr.delete_notebook("bad-id")

    def test_set_default_notebook_id(self, mgr):
        first_id = mgr.list_notebooks()[0]["id"]
        second_id = mgr.create_notebook("Second")
        mgr.set_default_notebook_id(first_id)
        assert mgr.get_default_notebook_id() == first_id

    def test_set_default_nonexistent_raises(self, mgr):
        with pytest.raises(KeyError):
            mgr.set_default_notebook_id("bad-id")

    def test_get_notebook_dir(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        d = mgr.get_notebook_dir(nb_id)
        assert os.path.isdir(d)
        assert nb_id in d


# ---------------------------------------------------------------------------
# TestSourceManagement
# ---------------------------------------------------------------------------


class TestSourceManagement:
    def test_add_file_source(self, mgr, tmp_path):
        nb_id = mgr.list_notebooks()[0]["id"]
        # Create a fake file to upload
        fake_file = tmp_path / "report.pdf"
        fake_file.write_bytes(b"%PDF-1.4 fake")
        dest = mgr.add_file_source(nb_id, str(fake_file), "report.pdf")
        assert os.path.exists(dest)
        sources = mgr.get_sources(nb_id)
        assert len(sources) == 1
        assert sources[0]["type"] == "file"
        assert sources[0]["filename"] == "report.pdf"

    def test_add_file_duplicate_name(self, mgr, tmp_path):
        nb_id = mgr.list_notebooks()[0]["id"]
        fake = tmp_path / "doc.pdf"
        fake.write_bytes(b"content1")
        mgr.add_file_source(nb_id, str(fake), "doc.pdf")
        # Add a second file with the same name
        fake2 = tmp_path / "doc2.pdf"
        fake2.write_bytes(b"content2")
        dest2 = mgr.add_file_source(nb_id, str(fake2), "doc.pdf")
        # Should have a unique suffix
        assert "doc_" in os.path.basename(dest2)
        sources = mgr.get_sources(nb_id)
        assert len(sources) == 2

    def test_add_url_source(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        mgr.add_url_source(nb_id, "https://example.com/article")
        sources = mgr.get_sources(nb_id)
        assert len(sources) == 1
        assert sources[0]["type"] == "url"
        assert sources[0]["url"] == "https://example.com/article"

    def test_add_url_duplicate_ignored(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        mgr.add_url_source(nb_id, "https://example.com")
        mgr.add_url_source(nb_id, "https://example.com")
        sources = mgr.get_sources(nb_id)
        assert len(sources) == 1

    def test_remove_file_source(self, mgr, tmp_path):
        nb_id = mgr.list_notebooks()[0]["id"]
        fake = tmp_path / "doc.pdf"
        fake.write_bytes(b"data")
        dest = mgr.add_file_source(nb_id, str(fake), "doc.pdf")
        assert os.path.exists(dest)
        mgr.remove_source(nb_id, 0)
        sources = mgr.get_sources(nb_id)
        assert len(sources) == 0
        assert not os.path.exists(dest)

    def test_remove_url_source(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        mgr.add_url_source(nb_id, "https://example.com")
        mgr.remove_source(nb_id, 0)
        assert len(mgr.get_sources(nb_id)) == 0

    def test_remove_source_out_of_range(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        with pytest.raises(IndexError):
            mgr.remove_source(nb_id, 0)

    def test_remove_source_negative_index(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        mgr.add_url_source(nb_id, "https://example.com")
        with pytest.raises(IndexError):
            mgr.remove_source(nb_id, -1)

    def test_get_sources_empty(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        assert mgr.get_sources(nb_id) == []


# ---------------------------------------------------------------------------
# TestSettingsPersistence
# ---------------------------------------------------------------------------


class TestSettingsPersistence:
    def test_default_settings(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        settings = mgr.get_settings(nb_id)
        assert settings == _DEFAULT_SETTINGS

    def test_save_and_load_settings(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        custom = {
            "format": "interview",
            "length": "long",
            "style": "academic",
            "language": "german",
            "outputs_to_generate": ["Podcast Audio"],
        }
        mgr.save_settings(nb_id, custom)
        loaded = mgr.get_settings(nb_id)
        assert loaded == custom

    def test_settings_per_notebook(self, mgr):
        nb1 = mgr.list_notebooks()[0]["id"]
        nb2 = mgr.create_notebook("Second")
        mgr.save_settings(nb1, {"format": "debate", "length": "short", "style": "funny", "language": "french", "outputs_to_generate": []})
        mgr.save_settings(nb2, {"format": "lecture", "length": "very-long", "style": "technical", "language": "spanish", "outputs_to_generate": ["PPTX Slides"]})
        assert mgr.get_settings(nb1)["format"] == "debate"
        assert mgr.get_settings(nb2)["format"] == "lecture"

    def test_settings_survive_reopen(self, tmp_path):
        base = str(tmp_path / "notebooks")
        mgr1 = NotebookManager(base_dir=base)
        nb_id = mgr1.list_notebooks()[0]["id"]
        mgr1.save_settings(nb_id, {"format": "summary", "length": "short", "style": "casual", "language": "italian", "outputs_to_generate": []})
        # Re-open manager (simulates server restart)
        mgr2 = NotebookManager(base_dir=base)
        assert mgr2.get_settings(nb_id)["format"] == "summary"


# ---------------------------------------------------------------------------
# TestLegacyMigration
# ---------------------------------------------------------------------------


class TestLegacyMigration:
    def test_legacy_output_migrated(self, mgr_with_legacy):
        mgr, legacy_dir = mgr_with_legacy
        notebooks = mgr.list_notebooks()
        assert len(notebooks) == 1
        assert notebooks[0]["name"] == "Legacy Notebook"

        nb_dir = mgr.get_notebook_dir(notebooks[0]["id"])
        # Files should have been copied
        assert os.path.exists(os.path.join(nb_dir, "podcast.wav"))
        assert os.path.exists(os.path.join(nb_dir, "step1", "extracted_text.txt"))

    def test_no_legacy_gets_default(self, tmp_path):
        # No legacy dir at all — should get "My Notebook"
        import local_notebooklm.notebook_manager as mod
        original = mod._LEGACY_OUTPUT
        mod._LEGACY_OUTPUT = str(tmp_path / "nonexistent")
        try:
            mgr = NotebookManager(base_dir=str(tmp_path / "notebooks"))
            notebooks = mgr.list_notebooks()
            assert notebooks[0]["name"] == "My Notebook"
        finally:
            mod._LEGACY_OUTPUT = original


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_multiple_creates(self, mgr):
        ids = [mgr.create_notebook(f"NB {i}") for i in range(5)]
        assert len(set(ids)) == 5  # All unique
        assert len(mgr.list_notebooks()) == 6  # 5 + initial default

    def test_create_delete_create(self, mgr):
        nb_id = mgr.create_notebook("Temp")
        mgr.delete_notebook(nb_id)
        nb_id2 = mgr.create_notebook("Temp")
        assert nb_id != nb_id2

    def test_metadata_updated_at_changes(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        meta1 = mgr.get_notebook(nb_id)
        mgr.rename_notebook(nb_id, "Renamed")
        meta2 = mgr.get_notebook(nb_id)
        assert meta2["updated_at"] >= meta1["updated_at"]

    def test_sources_dir_exists(self, mgr):
        nb_id = mgr.list_notebooks()[0]["id"]
        sources_dir = os.path.join(mgr.get_notebook_dir(nb_id), "sources")
        assert os.path.isdir(sources_dir)

    def test_concurrent_read_safe(self, tmp_path):
        """Two managers pointing at the same directory can read without error."""
        base = str(tmp_path / "notebooks")
        mgr1 = NotebookManager(base_dir=base)
        mgr2 = NotebookManager(base_dir=base)
        assert mgr1.list_notebooks() == mgr2.list_notebooks()

    def test_registry_persists_across_instances(self, tmp_path):
        base = str(tmp_path / "notebooks")
        mgr1 = NotebookManager(base_dir=base)
        mgr1.create_notebook("Persisted")
        mgr2 = NotebookManager(base_dir=base)
        names = [n["name"] for n in mgr2.list_notebooks()]
        assert "Persisted" in names
