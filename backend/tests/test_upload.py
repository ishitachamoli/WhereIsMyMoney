"""Integration tests for file upload endpoint with real bank CSV fixtures."""
import os
import pytest
from tests.conftest import get_fixture_path, TEST_SESSION_TOKEN


def _headers():
    return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}


class TestUploadEndpoint:
    """Test the /api/v1/upload endpoint with real bank statement files."""

    def test_upload_hdfc_csv(self, client, test_user):
        """Upload HDFC CSV and verify parsing."""
        filepath = get_fixture_path("hdfc_statement.csv")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("hdfc_statement.csv", f, "text/csv")},
                headers=_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_transactions"] == 8

    def test_upload_icici_csv(self, client, test_user):
        """Upload ICICI CSV and verify parsing."""
        filepath = get_fixture_path("icici_statement.csv")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("icici_statement.csv", f, "text/csv")},
                headers=_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_transactions"] == 9

    def test_upload_sbi_csv(self, client, test_user):
        """Upload SBI CSV and verify parsing."""
        filepath = get_fixture_path("sbi_statement.csv")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("sbi_statement.csv", f, "text/csv")},
                headers=_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_transactions"] == 8

    def test_upload_axis_csv(self, client, test_user):
        """Upload Axis CSV and verify parsing."""
        filepath = get_fixture_path("axis_statement.csv")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("axis_statement.csv", f, "text/csv")},
                headers=_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_transactions"] == 8

    def test_upload_kotak_csv(self, client, test_user):
        """Upload Kotak CSV and verify parsing."""
        filepath = get_fixture_path("kotak_statement.csv")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("kotak_statement.csv", f, "text/csv")},
                headers=_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_transactions"] == 8

    def test_upload_idfc_csv(self, client, test_user):
        """Upload IDFC CSV and verify parsing."""
        filepath = get_fixture_path("idfc_statement.csv")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("idfc_statement.csv", f, "text/csv")},
                headers=_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_transactions"] == 8

    def test_upload_sbi_text_xls(self, client, test_user):
        """Upload SBI XLS file that is actually tab-separated text (common Indian bank export)."""
        filepath = get_fixture_path("sbi_statement.xls")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("sbi_statement.xls", f, "application/vnd.ms-excel")},
                headers=_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_transactions"] == 5
        assert data["summary"]["bank_name"] == "SBI"

    def test_upload_invalid_file_type(self, client, test_user):
        """Reject unsupported file types."""
        response = client.post(
            "/api/v1/upload",
            files={"file": ("report.txt", b"fake content", "text/plain")},
            headers=_headers(),
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_upload_empty_file(self, client, test_user):
        """Reject empty files."""
        response = client.post(
            "/api/v1/upload",
            files={"file": ("empty.csv", b"", "text/csv")},
            headers=_headers(),
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_upload_creates_bank_statement_record(self, client, test_user):
        """Verify bank statement metadata is persisted correctly."""
        filepath = get_fixture_path("hdfc_statement.csv")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("hdfc_statement.csv", f, "text/csv")},
                headers=_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_transactions"] == 8
        assert data["summary"]["date_range"]["start"] is not None
        assert data["summary"]["date_range"]["end"] is not None

    def test_list_statements(self, client, test_user):
        """Upload and then list statements."""
        filepath = get_fixture_path("hdfc_statement.csv")
        with open(filepath, "rb") as f:
            client.post(
                "/api/v1/upload",
                files={"file": ("hdfc_statement.csv", f, "text/csv")},
                headers=_headers(),
            )

        response = client.get("/api/v1/upload/statements", headers=_headers())
        assert response.status_code == 200
        statements = response.json()
        assert len(statements) == 1
        assert statements[0]["bank_name"] == "HDFC"

    def test_upload_unauthorized(self, client, test_user):
        """Upload without auth returns 401."""
        filepath = get_fixture_path("hdfc_statement.csv")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("hdfc_statement.csv", f, "text/csv")},
            )
        assert response.status_code == 401
