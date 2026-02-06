"""
Vendor Grader - Multi-criteria vendor scoring with explainability
"""
import json
from typing import Optional

from src.llm.ollama_client import OllamaClient
from src.llm.prompts import GRADING_PROMPT
from src.models.analysis import VendorAnalysis, ScoreDetail
from src.config import settings


class VendorGrader:
    """
    Grades vendors based on multiple criteria with explainable AI.
    Uses LLM for nuanced evaluation with chain-of-thought reasoning.
    """
    
    def __init__(self, weights: dict = None):
        """
        Initialize the grader.
        
        Args:
            weights: Custom criterion weights (must sum to 1.0)
        """
        self.weights = weights or settings.scoring_weights
    
    async def grade(
        self,
        vendor_name: str,
        vendor_data: dict,
        criteria: list[str] = None,
        web_research: list[dict] = None
    ) -> VendorAnalysis:
        """
        Grade a vendor on specified criteria.
        
        Args:
            vendor_name: Name of the vendor
            vendor_data: Available vendor data
            criteria: Criteria to evaluate
            web_research: Optional web research results
            
        Returns:
            VendorAnalysis with scores and reasoning
        """
        criteria = criteria or list(self.weights.keys())
        
        # Build context for LLM
        context = f"""
        Vendor: {vendor_name}
        
        Available Data:
        {json.dumps(vendor_data, indent=2, default=str)}
        """
        
        if web_research:
            context += f"""
        
        Web Research:
        {json.dumps(web_research[:5], indent=2, default=str)}
        """
        
        prompt = f"""
        {context}
        
        Evaluate this vendor on the following criteria: {', '.join(criteria)}
        
        For each criterion:
        1. Analyze available evidence
        2. Assign a score from 0-100
        3. Provide clear reasoning
        
        Then calculate the overall weighted score using these weights:
        {json.dumps(self.weights, indent=2)}
        
        Finally, provide a recommendation:
        - APPROVED: overall score >= 70
        - REVIEW: overall score 50-69
        - REJECTED: overall score < 50
        
        Return as JSON with this structure:
        {{
            "breakdown": {{
                "criterion_name": {{"score": 85, "reasoning": "...", "evidence": ["..."]}}
            }},
            "overall_score": 82,
            "recommendation": "APPROVED",
            "confidence": 0.85,
            "key_findings": ["..."]
        }}
        """
        
        llm = OllamaClient()
        
        try:
            response = await llm.generate(prompt, system=GRADING_PROMPT, temperature=0.2)
            await llm.close()
            
            # Parse response
            result = self._parse_grading_response(response, criteria)
            
            # Build VendorAnalysis
            analysis = VendorAnalysis(
                vendor_id=vendor_data.get("id", f"v_{vendor_name[:8]}"),
                vendor_name=vendor_name,
                overall_score=result.get("overall_score", 50),
                recommendation=result.get("recommendation", "REVIEW"),
                breakdown={
                    k: ScoreDetail(
                        score=v.get("score", 50),
                        reasoning=v.get("reasoning", ""),
                        evidence=v.get("evidence", [])
                    )
                    for k, v in result.get("breakdown", {}).items()
                },
                reasoning_chain=result.get("key_findings", []),
                confidence=result.get("confidence", 0.7),
                criteria_used=criteria,
                web_research_used=bool(web_research)
            )
            
            return analysis
            
        except Exception as e:
            await llm.close()
            # Return a default analysis on error
            return VendorAnalysis(
                vendor_id=vendor_data.get("id", "unknown"),
                vendor_name=vendor_name,
                overall_score=0,
                recommendation="REVIEW",
                breakdown={},
                reasoning_chain=[f"Grading error: {str(e)}"],
                confidence=0.0
            )
    
    def _parse_grading_response(self, response: str, criteria: list[str]) -> dict:
        """Parse LLM response to extract grading data."""
        # Try to extract JSON
        if "{" in response and "}" in response:
            try:
                json_str = response[response.find("{"):response.rfind("}")+1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Fallback: return default structure
        return {
            "breakdown": {c: {"score": 50, "reasoning": "Unable to parse"} for c in criteria},
            "overall_score": 50,
            "recommendation": "REVIEW",
            "confidence": 0.3
        }
    
    async def compare(
        self,
        vendors: list[tuple[str, dict]],
        criteria: list[str] = None
    ) -> dict:
        """
        Compare multiple vendors.
        
        Args:
            vendors: List of (name, data) tuples
            criteria: Criteria to compare on
            
        Returns:
            Comparison report
        """
        criteria = criteria or list(self.weights.keys())
        
        # Grade each vendor
        analyses = []
        for name, data in vendors:
            analysis = await self.grade(name, data, criteria)
            analyses.append(analysis)
        
        # Sort by overall score
        analyses.sort(key=lambda a: a.overall_score, reverse=True)
        
        # Build rankings per criterion
        criterion_rankings = {}
        for criterion in criteria:
            sorted_by_criterion = sorted(
                analyses,
                key=lambda a: a.breakdown.get(criterion, ScoreDetail(score=0, reasoning="")).score,
                reverse=True
            )
            criterion_rankings[criterion] = [a.vendor_id for a in sorted_by_criterion]
        
        return {
            "analyses": [a.model_dump() for a in analyses],
            "overall_ranking": [a.vendor_id for a in analyses],
            "criterion_rankings": criterion_rankings,
            "winner": analyses[0].vendor_id if analyses else None,
            "summary": f"Compared {len(vendors)} vendors. Winner: {analyses[0].vendor_name if analyses else 'None'}"
        }
