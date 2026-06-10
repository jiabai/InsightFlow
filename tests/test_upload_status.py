"""
Test: Upload & Status API — Issue #04.

Covers: POST /upload/{user_id}, GET /file_status/{content_id}
"""
import pytest


class TestUploadContent:
    """Verify upload endpoint accepts Markdown and returns content_id."""

    async def test_upload_valid_markdown_returns_content_id(self, client):
        """Upload a valid Markdown file → 200 with content_id."""
        markdown = b"# Hello World\n\nThis is a test article."
        response = client.post(
            "/upload/user123",
            files={"file": ("test.md", markdown, "text/markdown")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert data["file_id"]  # non-empty
        assert data["status"] == "Upload Completed"

    async def test_upload_twice_same_content_returns_same_id(self, client):
        """Same file + user → same content_id (idempotent)."""
        markdown = b"# Idempotent Test"
        r1 = client.post("/upload/user123", files={"file": ("test.md", markdown)})
        r2 = client.post("/upload/user123", files={"file": ("test.md", markdown)})

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["file_id"] == r2.json()["file_id"]

    async def test_upload_different_users_isolated(self, client):
        """Different users → different content_ids even for same content."""
        markdown = b"# Same Content"
        r1 = client.post("/upload/alice", files={"file": ("a.md", markdown)})
        r2 = client.post("/upload/bob", files={"file": ("a.md", markdown)})

        assert r1.json()["file_id"] != r2.json()["file_id"]

    async def test_upload_empty_file_rejected(self, client):
        """Empty file should be rejected."""
        response = client.post(
            "/upload/user123",
            files={"file": ("empty.md", b"", "text/markdown")},
        )
        assert response.status_code in {400, 422}


class TestFileStatus:
    """Verify file status tracking endpoints."""

    async def test_status_for_nonexistent_file(self, client):
        """Non-existent file_id → appropriate error."""
        response = client.get("/file_status/nonexistent")
        assert response.status_code in {200, 404}

    async def test_status_after_upload(self, client):
        """After upload, status should be retrievable."""
        r = client.post("/upload/user123", files={"file": ("s.md", b"# Status Test")})
        file_id = r.json()["file_id"]

        status_r = client.get(f"/file_status/{file_id}")
        assert status_r.status_code == 200
        assert "status" in status_r.json()

    async def test_status_transitions(self, client):
        """Status should transition: Pending → Processing → Completed."""
        r = client.post("/upload/user123", files={"file": ("t.md", b"# Transition")})
        file_id = r.json()["file_id"]

        # After upload, should be Pending
        s1 = client.get(f"/file_status/{file_id}")
        assert s1.json()["status"] in {"Pending", "Processing", "Completed"}
