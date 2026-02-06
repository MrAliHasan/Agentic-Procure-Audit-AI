"""
Test Suite for Sovereign Order Intelligence
"""
import pytest
import asyncio


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "response": '{"overall_score": 85, "recommendation": "APPROVED", "confidence": 0.9}',
        "done": True
    }


@pytest.fixture
def sample_vendor_data():
    """Sample vendor data for testing."""
    return {
        "name": "Test Vendor Corp",
        "description": "A test vendor for unit testing",
        "website": "https://testvendor.com",
        "industry": "Technology",
        "products": ["Widget A", "Widget B"]
    }


@pytest.fixture
def sample_invoice_text():
    """Sample invoice text for OCR testing."""
    return """
    INVOICE
    
    From: Acme Corp
    123 Business St
    New York, NY 10001
    
    Bill To: Your Company
    
    Invoice #: INV-2025-001
    Date: 2025-02-01
    Due Date: 2025-03-01
    
    Description          Qty     Price       Total
    Widget A              10     $50.00     $500.00
    Widget B               5    $100.00     $500.00
    
    Subtotal:                              $1,000.00
    Tax (10%):                               $100.00
    Total:                                 $1,100.00
    
    Payment Terms: Net 30
    """
