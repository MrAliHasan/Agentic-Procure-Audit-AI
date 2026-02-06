"""
Tests for VendorGrader
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestVendorGrader:
    """Test suite for vendor grading functionality."""
    
    @pytest.mark.asyncio
    async def test_grade_basic(self, sample_vendor_data):
        """Test basic vendor grading."""
        # Mock the LLM response
        mock_response = '''
        {
            "breakdown": {
                "price": {"score": 85, "reasoning": "Competitive pricing"},
                "quality": {"score": 90, "reasoning": "High quality products"},
                "reliability": {"score": 80, "reasoning": "Good track record"},
                "risk": {"score": 75, "reasoning": "Low risk profile"}
            },
            "overall_score": 82,
            "recommendation": "APPROVED",
            "confidence": 0.85
        }
        '''
        
        with patch('src.processors.vendor_grader.OllamaClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.generate = AsyncMock(return_value=mock_response)
            mock_instance.close = AsyncMock()
            
            from src.processors.vendor_grader import VendorGrader
            
            grader = VendorGrader()
            analysis = await grader.grade(
                "Test Vendor Corp",
                sample_vendor_data
            )
            
            assert analysis.vendor_name == "Test Vendor Corp"
            assert analysis.overall_score == 82
            assert analysis.recommendation == "APPROVED"
            assert analysis.confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_grade_with_web_research(self, sample_vendor_data):
        """Test grading with web research."""
        web_research = {
            "company overview": [{"title": "Test Vendor", "content": "Great company"}]
        }
        
        mock_response = '{"overall_score": 88, "recommendation": "APPROVED", "breakdown": {}, "confidence": 0.9}'
        
        with patch('src.processors.vendor_grader.OllamaClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.generate = AsyncMock(return_value=mock_response)
            mock_instance.close = AsyncMock()
            
            from src.processors.vendor_grader import VendorGrader
            
            grader = VendorGrader()
            analysis = await grader.grade(
                "Test Vendor Corp",
                sample_vendor_data,
                web_research=web_research
            )
            
            assert analysis.web_research_used == True
            assert analysis.overall_score == 88
    
    @pytest.mark.asyncio
    async def test_compare_vendors(self):
        """Test vendor comparison."""
        vendors = [
            ("Vendor A", {"name": "Vendor A"}),
            ("Vendor B", {"name": "Vendor B"})
        ]
        
        mock_response = '{"overall_score": 75, "recommendation": "APPROVED", "breakdown": {}, "confidence": 0.8}'
        
        with patch('src.processors.vendor_grader.OllamaClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.generate = AsyncMock(return_value=mock_response)
            mock_instance.close = AsyncMock()
            
            from src.processors.vendor_grader import VendorGrader
            
            grader = VendorGrader()
            comparison = await grader.compare(vendors)
            
            assert "analyses" in comparison
            assert len(comparison["analyses"]) == 2
            assert "winner" in comparison
