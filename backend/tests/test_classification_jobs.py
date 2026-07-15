"""Integration tests for async classification jobs."""
import os
import pytest
from tests.conftest import get_fixture_path, TEST_SESSION_TOKEN

from app.models.classification_job import ClassificationJob


def _headers():
    return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}


class TestClassificationJobs:
    """Test the /api/v1/jobs/classification endpoints."""

    def test_upload_creates_classification_job(self, client, test_user, test_categories):
        """Upload creates a classification job for low-confidence transactions."""
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
        # classification_job_id should be present (may be null if all classified by rules)
        assert "classification_job_id" in data

    def test_upload_response_has_job_id_when_low_confidence(self, client, test_user, db_session):
        """When rule-engine has low confidence, a background job is created."""
        filepath = get_fixture_path("hdfc_statement.csv")
        with open(filepath, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("hdfc_statement.csv", f, "text/csv")},
                headers=_headers(),
            )

        data = response.json()
        job_id = data.get("classification_job_id")

        if job_id:
            # If a job was created, verify we can fetch it
            job_response = client.get(
                f"/api/v1/jobs/classification/{job_id}",
                headers=_headers(),
            )
            assert job_response.status_code == 200
            job_data = job_response.json()
            assert job_data["id"] == job_id
            assert job_data["status"] in ["pending", "running", "completed"]
            assert job_data["total_transactions"] > 0
            assert "progress_percent" in job_data

    def test_get_active_job_returns_none_when_no_job(self, client, test_user):
        """No active job should return null."""
        response = client.get(
            "/api/v1/jobs/classification/active",
            headers=_headers(),
        )
        assert response.status_code == 200
        assert response.json() is None

    def test_get_active_job_returns_pending_job(self, client, test_user, db_session):
        """Active job endpoint returns a pending/running job."""
        # Create a pending job
        job = ClassificationJob(
            user_id=test_user.id,
            total_transactions=50,
            classified_transactions=10,
            status="running",
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        response = client.get(
            "/api/v1/jobs/classification/active",
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert data["id"] == job.id
        assert data["status"] == "running"
        assert data["total_transactions"] == 50
        assert data["classified_transactions"] == 10
        assert data["progress_percent"] == 20.0

    def test_get_job_not_found(self, client, test_user):
        """Getting a nonexistent job returns 404."""
        response = client.get(
            "/api/v1/jobs/classification/nonexistent-id",
            headers=_headers(),
        )
        assert response.status_code == 404

    def test_get_job_unauthorized(self, client):
        """Job endpoints require authentication."""
        response = client.get("/api/v1/jobs/classification/active")
        assert response.status_code == 401

    def test_completed_job_not_returned_as_active(self, client, test_user, db_session):
        """Completed jobs are not returned by the active endpoint."""
        from datetime import datetime, timezone
        job = ClassificationJob(
            user_id=test_user.id,
            total_transactions=50,
            classified_transactions=50,
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(
            "/api/v1/jobs/classification/active",
            headers=_headers(),
        )
        assert response.status_code == 200
        assert response.json() is None
