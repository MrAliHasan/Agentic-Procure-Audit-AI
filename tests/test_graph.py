"""
Tests for the Order Intelligence Graph
"""
import pytest
from unittest.mock import AsyncMock, patch


class TestOrderIntelligenceGraph:
    """Test suite for the main LangGraph workflow."""
    
    @pytest.mark.asyncio
    async def test_analyze_query_basic(self):
        """Test basic query analysis."""
        # Mock all dependencies
        with patch('src.graphs.order_intelligence.get_vector_store') as mock_store, \
             patch('src.graphs.order_intelligence.TavilySearchTool') as mock_tavily, \
             patch('src.graphs.order_intelligence.OllamaClient') as mock_ollama:
            
            # Setup mocks
            mock_store_instance = mock_store.return_value
            mock_store_instance.similarity_search = AsyncMock(return_value=[])
            
            mock_ollama_instance = mock_ollama.return_value
            mock_ollama_instance.generate = AsyncMock(return_value='{"score": 0.5, "decision": "needs_search"}')
            mock_ollama_instance.close = AsyncMock()
            
            mock_tavily_instance = mock_tavily.return_value
            mock_tavily_instance.search = AsyncMock(return_value=[])
            
            from src.graphs.order_intelligence import analyze_query
            
            result = await analyze_query("Test query", ["price", "quality"])
            
            assert "query" in result
            assert result["query"] == "Test query"
            assert "reasoning_chain" in result
    
    @pytest.mark.asyncio
    async def test_retrieve_node(self):
        """Test the retrieve node function."""
        from src.graphs.order_intelligence import retrieve_node
        
        with patch('src.graphs.order_intelligence.get_vector_store') as mock_store:
            mock_instance = mock_store.return_value
            mock_instance.similarity_search = AsyncMock(return_value=[
                {"id": "v_test", "text": "Test vendor", "score": 0.95}
            ])
            
            state = {"query": "test query"}
            result = await retrieve_node(state)
            
            assert "vendors" in result
            assert len(result["vendors"]) == 1
            assert "reasoning_steps" in result
    
    @pytest.mark.asyncio
    async def test_grade_node_sufficient(self):
        """Test grade node with sufficient data."""
        from src.graphs.order_intelligence import grade_node
        
        with patch('src.graphs.order_intelligence.OllamaClient') as mock_ollama:
            mock_instance = mock_ollama.return_value
            mock_instance.generate = AsyncMock(
                return_value='{"score": 0.85, "reasoning": "Good data", "decision": "sufficient"}'
            )
            mock_instance.close = AsyncMock()
            
            state = {
                "query": "test query",
                "vendors": [{"id": "v1", "text": "Vendor data"}],
                "documents": []
            }
            
            result = await grade_node(state)
            
            assert result["grade_decision"] == "sufficient"
    
    @pytest.mark.asyncio
    async def test_decide_to_search(self):
        """Test the routing decision function."""
        from src.graphs.order_intelligence import decide_to_search
        
        # Test sufficient data
        state = {"grade_decision": "sufficient", "iteration": 0, "max_iterations": 3}
        assert decide_to_search(state) == "generate"
        
        # Test needs search
        state = {"grade_decision": "needs_search", "iteration": 0, "max_iterations": 3}
        assert decide_to_search(state) == "search"
        
        # Test max iterations reached
        state = {"grade_decision": "needs_search", "iteration": 3, "max_iterations": 3}
        assert decide_to_search(state) == "generate"
