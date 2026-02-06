"""
Tests for the FastAPI server
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


class TestAPIEndpoints:
    """Test suite for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies."""
        with patch('src.api.server.OllamaClient') as mock_ollama, \
             patch('src.api.server.get_vector_store') as mock_store:
            
            # Setup mocks
            mock_ollama_instance = mock_ollama.return_value
            mock_ollama_instance.health_check = AsyncMock(return_value=True)
            mock_ollama_instance.close = AsyncMock()
            
            mock_store_instance = mock_store.return_value
            mock_store_instance.get_stats = AsyncMock(return_value={})
            mock_store_instance.similarity_search = AsyncMock(return_value=[])
            mock_store_instance.add_documents = AsyncMock(return_value=["test_id"])
            
            from src.api.server import app
            
            yield TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "components" in data
    
    def test_add_vendor(self, client):
        """Test adding a vendor."""
        vendor_data = {
            "name": "Test Vendor",
            "description": "A test vendor",
            "website": "https://test.com",
            "industry": "Technology",
            "products": ["Widget"]
        }
        
        response = client.post("/vendors", json=vendor_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "vendor_id" in data
    
    def test_list_vendors(self, client):
        """Test listing vendors."""
        response = client.get("/vendors")
        assert response.status_code == 200
        
        data = response.json()
        assert "vendors" in data
        assert "count" in data
    
    def test_search_vendors(self, client):
        """Test vendor search."""
        response = client.post("/vendors/search", json={
            "query": "technology vendor",
            "limit": 5
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "count" in data
    
    def test_stats_endpoint(self, client):
        """Test stats endpoint."""
        response = client.get("/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "knowledge_base" in data
        assert "config" in data
