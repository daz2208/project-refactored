"""
End-to-end API endpoint tests (Phase 5).

Tests all 12 API endpoints with actual HTTP calls using FastAPI TestClient.
Verifies full workflows from registration through document management.
"""

import pytest
import base64
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Register and login, return auth headers."""
    # Register a test user
    username = "testuser_api"
    password = "testpass123"

    register_response = client.post(
        "/users",
        json={"username": username, "password": password}
    )

    # Login to get token
    login_response = client.post(
        "/token",
        json={"username": username, "password": password}
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

def test_register_new_user(client):
    """Test user registration."""
    response = client.post(
        "/users",
        json={"username": "newuser123", "password": "password123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser123"


def test_register_duplicate_user(client):
    """Test registering duplicate username fails."""
    username = "duplicate_user"
    password = "password123"

    # First registration
    client.post("/users", json={"username": username, "password": password})

    # Second registration should fail
    response = client.post(
        "/users",
        json={"username": username, "password": password}
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_register_invalid_username(client):
    """Test username validation."""
    # Too short
    response = client.post(
        "/users",
        json={"username": "ab", "password": "password123"}
    )
    assert response.status_code == 422


def test_register_invalid_password(client):
    """Test password validation."""
    # Too short
    response = client.post(
        "/users",
        json={"username": "validuser", "password": "short"}
    )
    assert response.status_code == 422


def test_login_success(client):
    """Test successful login."""
    username = "logintest"
    password = "password123"

    # Register
    client.post("/users", json={"username": username, "password": password})

    # Login
    response = client.post(
        "/token",
        json={"username": username, "password": password}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """Test login with wrong password."""
    response = client.post(
        "/token",
        json={"username": "nonexistent", "password": "wrongpass"}
    )

    assert response.status_code == 401


def test_unauthorized_access(client):
    """Test accessing protected endpoint without auth."""
    response = client.get("/clusters")
    assert response.status_code == 401


# =============================================================================
# UPLOAD TESTS
# =============================================================================

@patch('backend.main.concept_extractor.extract')
async def test_upload_text(mock_extract, client, auth_headers):
    """Test text upload endpoint."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Python", "category": "language", "confidence": 0.9}
        ],
        "skill_level": "intermediate",
        "suggested_cluster": "Python Programming",
        "primary_topic": "Programming"
    }

    response = client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "Learn Python programming basics"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert "cluster_id" in data


def test_upload_text_empty_content(client, auth_headers):
    """Test uploading empty text fails."""
    response = client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": ""}
    )

    assert response.status_code == 400


@patch('backend.main.ingest.download_url')
@patch('backend.main.concept_extractor.extract')
async def test_upload_url(mock_extract, mock_download, client, auth_headers):
    """Test URL upload endpoint."""
    # Mock URL download
    mock_download.return_value = "Article content about Docker"

    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Docker", "category": "tool", "confidence": 0.85}
        ],
        "skill_level": "intermediate",
        "suggested_cluster": "Containerization",
        "primary_topic": "DevOps"
    }

    response = client.post(
        "/upload",
        headers=auth_headers,
        json={"url": "https://example.com/docker-tutorial"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert "cluster_id" in data


@patch('backend.main.ingest.ingest_upload_file')
@patch('backend.main.concept_extractor.extract')
async def test_upload_file(mock_extract, mock_ingest, client, auth_headers):
    """Test file upload endpoint."""
    # Mock file ingestion
    mock_ingest.return_value = "PDF content about testing"

    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Testing", "category": "concept", "confidence": 0.8}
        ],
        "skill_level": "beginner",
        "suggested_cluster": "Software Testing",
        "primary_topic": "Quality Assurance"
    }

    # Encode fake file content
    file_content = b"Fake PDF content"
    encoded = base64.b64encode(file_content).decode('utf-8')

    response = client.post(
        "/upload_file",
        headers=auth_headers,
        json={"filename": "test.pdf", "content": encoded}
    )

    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert "cluster_id" in data


def test_upload_file_too_large(client, auth_headers):
    """Test uploading file larger than 50MB fails."""
    # Create 51MB of data
    large_content = b"x" * (51 * 1024 * 1024)
    encoded = base64.b64encode(large_content).decode('utf-8')

    response = client.post(
        "/upload_file",
        headers=auth_headers,
        json={"filename": "large.pdf", "content": encoded}
    )

    assert response.status_code == 413


@patch('backend.main.image_processor.extract_text_from_image')
@patch('backend.main.image_processor.get_image_metadata')
@patch('backend.main.image_processor.store_image')
@patch('backend.main.concept_extractor.extract')
async def test_upload_image(mock_extract, mock_store, mock_meta, mock_ocr, client, auth_headers):
    """Test image upload with OCR."""
    # Mock OCR
    mock_ocr.return_value = "Text from image"
    mock_meta.return_value = {"width": 800, "height": 600}
    mock_store.return_value = "stored_images/doc_0.png"

    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "OCR", "category": "technology", "confidence": 0.7}
        ],
        "skill_level": "advanced",
        "suggested_cluster": "Image Processing",
        "primary_topic": "Computer Vision"
    }

    # Encode fake image
    image_bytes = b"fake image data"
    encoded = base64.b64encode(image_bytes).decode('utf-8')

    response = client.post(
        "/upload_image",
        headers=auth_headers,
        json={
            "filename": "test.png",
            "content": encoded,
            "description": "Test image"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert "ocr_text_length" in data


# =============================================================================
# CLUSTER TESTS
# =============================================================================

def test_get_clusters_empty(client, auth_headers):
    """Test getting clusters when none exist."""
    response = client.get("/clusters", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "clusters" in data
    assert isinstance(data["clusters"], list)


@patch('backend.main.concept_extractor.extract')
async def test_get_clusters_with_data(mock_extract, client, auth_headers):
    """Test getting clusters after uploading content."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "FastAPI", "category": "framework", "confidence": 0.9}
        ],
        "skill_level": "intermediate",
        "suggested_cluster": "Web Frameworks",
        "primary_topic": "Backend Development"
    }

    # Upload some content first
    client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "FastAPI tutorial for building APIs"}
    )

    # Get clusters
    response = client.get("/clusters", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["clusters"]) > 0

    cluster = data["clusters"][0]
    assert "id" in cluster
    assert "name" in cluster
    assert "doc_count" in cluster


# =============================================================================
# SEARCH TESTS
# =============================================================================

@patch('backend.main.concept_extractor.extract')
async def test_search_documents(mock_extract, client, auth_headers):
    """Test search functionality."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Python", "category": "language", "confidence": 0.9}
        ],
        "skill_level": "beginner",
        "suggested_cluster": "Python Basics",
        "primary_topic": "Programming"
    }

    # Upload content
    client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "Python programming tutorial"}
    )

    # Search
    response = client.get(
        "/search_full?q=Python&top_k=10",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_search_empty_query(client, auth_headers):
    """Test search with empty query."""
    response = client.get(
        "/search_full?q=",
        headers=auth_headers
    )

    # Should return empty results or error
    assert response.status_code in [200, 400]


@patch('backend.main.concept_extractor.extract')
async def test_search_with_filters(mock_extract, client, auth_headers):
    """Test search with filters (source_type, skill_level)."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Testing", "category": "concept", "confidence": 0.8}
        ],
        "skill_level": "intermediate",
        "suggested_cluster": "Testing",
        "primary_topic": "QA"
    }

    # Upload content
    client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "Unit testing with pytest"}
    )

    # Search with filters
    response = client.get(
        "/search_full?q=testing&source_type=text&skill_level=intermediate",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "filters_applied" in data
    assert data["filters_applied"]["source_type"] == "text"


# =============================================================================
# DOCUMENT MANAGEMENT TESTS
# =============================================================================

@patch('backend.main.concept_extractor.extract')
async def test_get_document(mock_extract, client, auth_headers):
    """Test getting a single document."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "API", "category": "concept", "confidence": 0.85}
        ],
        "skill_level": "intermediate",
        "suggested_cluster": "APIs",
        "primary_topic": "Backend"
    }

    # Upload document
    upload_response = client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "REST API design patterns"}
    )
    doc_id = upload_response.json()["document_id"]

    # Get document
    response = client.get(f"/documents/{doc_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"] == doc_id
    assert "content" in data
    assert "metadata" in data


def test_get_nonexistent_document(client, auth_headers):
    """Test getting document that doesn't exist."""
    response = client.get("/documents/99999", headers=auth_headers)
    assert response.status_code == 404


@patch('backend.main.concept_extractor.extract')
async def test_delete_document(mock_extract, client, auth_headers):
    """Test deleting a document."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Delete", "category": "concept", "confidence": 0.7}
        ],
        "skill_level": "beginner",
        "suggested_cluster": "Operations",
        "primary_topic": "CRUD"
    }

    # Upload document
    upload_response = client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "Document to be deleted"}
    )
    doc_id = upload_response.json()["document_id"]

    # Delete document
    response = client.delete(f"/documents/{doc_id}", headers=auth_headers)

    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()

    # Verify deletion
    get_response = client.get(f"/documents/{doc_id}", headers=auth_headers)
    assert get_response.status_code == 404


@patch('backend.main.concept_extractor.extract')
async def test_update_document_metadata(mock_extract, client, auth_headers):
    """Test updating document metadata."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Update", "category": "concept", "confidence": 0.75}
        ],
        "skill_level": "intermediate",
        "suggested_cluster": "Updates",
        "primary_topic": "Metadata"
    }

    # Upload document
    upload_response = client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "Document to update"}
    )
    doc_id = upload_response.json()["document_id"]

    # Update metadata
    response = client.put(
        f"/documents/{doc_id}/metadata",
        headers=auth_headers,
        json={"skill_level": "advanced"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["skill_level"] == "advanced"


# =============================================================================
# CLUSTER MANAGEMENT TESTS
# =============================================================================

@patch('backend.main.concept_extractor.extract')
async def test_update_cluster(mock_extract, client, auth_headers):
    """Test updating cluster name."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Cluster", "category": "concept", "confidence": 0.8}
        ],
        "skill_level": "intermediate",
        "suggested_cluster": "Original Name",
        "primary_topic": "Clustering"
    }

    # Upload to create cluster
    upload_response = client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "Content for cluster"}
    )
    cluster_id = upload_response.json()["cluster_id"]

    # Update cluster
    response = client.put(
        f"/clusters/{cluster_id}",
        headers=auth_headers,
        json={"name": "Updated Cluster Name"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["cluster"]["name"] == "Updated Cluster Name"


@patch('backend.main.concept_extractor.extract')
async def test_export_cluster_json(mock_extract, client, auth_headers):
    """Test exporting cluster as JSON."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Export", "category": "concept", "confidence": 0.8}
        ],
        "skill_level": "intermediate",
        "suggested_cluster": "Export Test",
        "primary_topic": "Data Export"
    }

    # Upload to create cluster
    upload_response = client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "Content for export"}
    )
    cluster_id = upload_response.json()["cluster_id"]

    # Export as JSON
    response = client.get(
        f"/export/cluster/{cluster_id}?format=json",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "cluster" in data
    assert "documents" in data


@patch('backend.main.concept_extractor.extract')
async def test_export_cluster_markdown(mock_extract, client, auth_headers):
    """Test exporting cluster as Markdown."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Markdown", "category": "format", "confidence": 0.9}
        ],
        "skill_level": "beginner",
        "suggested_cluster": "Markdown Export",
        "primary_topic": "Documentation"
    }

    # Upload to create cluster
    upload_response = client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "Markdown export test"}
    )
    cluster_id = upload_response.json()["cluster_id"]

    # Export as Markdown
    response = client.get(
        f"/export/cluster/{cluster_id}?format=markdown",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["format"] == "markdown"


def test_export_nonexistent_cluster(client, auth_headers):
    """Test exporting cluster that doesn't exist."""
    response = client.get(
        "/export/cluster/99999?format=json",
        headers=auth_headers
    )
    assert response.status_code == 404


@patch('backend.main.concept_extractor.extract')
async def test_export_all(mock_extract, client, auth_headers):
    """Test exporting entire knowledge bank."""
    # Mock concept extraction
    mock_extract.return_value = {
        "concepts": [
            {"name": "Full", "category": "concept", "confidence": 0.7}
        ],
        "skill_level": "intermediate",
        "suggested_cluster": "Full Export",
        "primary_topic": "Export"
    }

    # Upload some content
    client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "First document"}
    )
    client.post(
        "/upload_text",
        headers=auth_headers,
        json={"content": "Second document"}
    )

    # Export all as JSON
    response = client.get("/export/all?format=json", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "clusters" in data
    assert len(data["documents"]) >= 2


# =============================================================================
# BUILD SUGGESTIONS TEST
# =============================================================================

@patch('backend.main.build_suggester.analyze_knowledge_bank')
async def test_what_can_i_build(mock_analyze, client, auth_headers):
    """Test build suggestions endpoint."""
    # Mock build suggestions
    mock_analyze.return_value = [
        {
            "title": "Test Project",
            "description": "A test project",
            "feasibility": "high",
            "effort_estimate": "1 week",
            "required_skills": ["Python"],
            "missing_knowledge": [],
            "relevant_clusters": [0],
            "starter_steps": ["Step 1", "Step 2"],
            "file_structure": "project/\n  main.py"
        }
    ]

    response = client.post(
        "/what_can_i_build",
        headers=auth_headers,
        json={"max_suggestions": 5}
    )

    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert "knowledge_summary" in data


# =============================================================================
# HEALTH CHECK TEST
# =============================================================================

def test_health_check(client):
    """Test health check endpoint (no auth required)."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "statistics" in data
    assert "documents" in data["statistics"]
    assert "clusters" in data["statistics"]
    assert "users" in data["statistics"]
    assert "dependencies" in data
    assert "disk_healthy" in data["dependencies"]
    assert "openai_configured" in data["dependencies"]


# =============================================================================
# INTEGRATION TEST - FULL WORKFLOW
# =============================================================================

@patch('backend.main.concept_extractor.extract')
async def test_full_workflow(mock_extract, client):
    """
    Test complete workflow: register → login → upload → search → delete.

    This is a comprehensive integration test that exercises the entire system.
    """
    # Mock concept extraction for all uploads
    mock_extract.return_value = {
        "concepts": [
            {"name": "Integration", "category": "concept", "confidence": 0.9},
            {"name": "Testing", "category": "concept", "confidence": 0.85}
        ],
        "skill_level": "advanced",
        "suggested_cluster": "Integration Testing",
        "primary_topic": "Software Testing"
    }

    # 1. Register user
    register_response = client.post(
        "/users",
        json={"username": "workflow_user", "password": "testpass123"}
    )
    assert register_response.status_code == 200

    # 2. Login
    login_response = client.post(
        "/token",
        json={"username": "workflow_user", "password": "testpass123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Upload text document
    upload_response = client.post(
        "/upload_text",
        headers=headers,
        json={"content": "Integration testing is important for software quality"}
    )
    assert upload_response.status_code == 200
    doc_id = upload_response.json()["document_id"]
    cluster_id = upload_response.json()["cluster_id"]

    # 4. Search for document
    search_response = client.get(
        "/search_full?q=integration&top_k=5",
        headers=headers
    )
    assert search_response.status_code == 200
    assert len(search_response.json()["results"]) > 0

    # 5. Get clusters
    clusters_response = client.get("/clusters", headers=headers)
    assert clusters_response.status_code == 200
    assert len(clusters_response.json()["clusters"]) > 0

    # 6. Export cluster
    export_response = client.get(
        f"/export/cluster/{cluster_id}?format=json",
        headers=headers
    )
    assert export_response.status_code == 200

    # 7. Update document metadata
    update_response = client.put(
        f"/documents/{doc_id}/metadata",
        headers=headers,
        json={"skill_level": "expert"}
    )
    assert update_response.status_code == 200

    # 8. Delete document
    delete_response = client.delete(f"/documents/{doc_id}", headers=headers)
    assert delete_response.status_code == 200

    # 9. Verify deletion
    get_response = client.get(f"/documents/{doc_id}", headers=headers)
    assert get_response.status_code == 404

    # 10. Check health
    health_response = client.get("/health")
    assert health_response.status_code == 200
