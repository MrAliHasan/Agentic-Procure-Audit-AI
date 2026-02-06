"""
Report Generator - Create formatted analysis reports
"""
from datetime import datetime
from typing import Optional
import json

from src.models.analysis import VendorAnalysis, ComparisonReport, MarketIntelligence


class ReportGenerator:
    """
    Generate formatted reports from analysis results.
    Supports multiple output formats.
    """
    
    async def vendor_report(
        self,
        analysis: VendorAnalysis,
        format: str = "markdown"
    ) -> str:
        """
        Generate a vendor analysis report.
        
        Args:
            analysis: VendorAnalysis object
            format: Output format (markdown, html, json)
            
        Returns:
            Formatted report string
        """
        if format == "json":
            return json.dumps(analysis.model_dump(), indent=2, default=str)
        
        # Markdown format
        recommendation_emoji = {
            "APPROVED": "✅",
            "REVIEW": "⚠️",
            "REJECTED": "❌"
        }
        
        report = f"""# Vendor Analysis Report

## {analysis.vendor_name}

**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  
**Analysis ID**: `{analysis.id}`

---

## Summary

| Metric | Value |
|--------|-------|
| **Overall Score** | **{analysis.overall_score}/100** |
| **Recommendation** | {recommendation_emoji.get(analysis.recommendation, '')} **{analysis.recommendation}** |
| **Confidence** | {analysis.confidence:.0%} |

---

## Score Breakdown

"""
        
        for criterion, detail in analysis.breakdown.items():
            score_bar = self._score_bar(detail.score)
            report += f"""### {criterion.title()}
**Score**: {detail.score}/100 {score_bar}

{detail.reasoning}

"""
        
        if analysis.reasoning_chain:
            report += """---

## Analysis Reasoning

"""
            for i, step in enumerate(analysis.reasoning_chain, 1):
                report += f"{i}. {step}\n"
        
        if analysis.sources:
            report += """
---

## Sources

"""
            for source in analysis.sources:
                report += f"- {source}\n"
        
        return report
    
    async def comparison_report(
        self,
        comparison: dict,  # From VendorGrader.compare()
        format: str = "markdown"
    ) -> str:
        """
        Generate a vendor comparison report.
        
        Args:
            comparison: Comparison result dict
            format: Output format
            
        Returns:
            Formatted report string
        """
        if format == "json":
            return json.dumps(comparison, indent=2, default=str)
        
        analyses = comparison.get("analyses", [])
        
        report = f"""# Vendor Comparison Report

**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  
**Vendors Compared**: {len(analyses)}

---

## Overall Ranking

| Rank | Vendor | Score | Recommendation |
|------|--------|-------|----------------|
"""
        
        for i, analysis in enumerate(analyses, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            report += f"| {medal} | {analysis['vendor_name']} | {analysis['overall_score']}/100 | {analysis['recommendation']} |\n"
        
        if comparison.get("winner"):
            winner = next((a for a in analyses if a['vendor_id'] == comparison['winner']), None)
            if winner:
                report += f"""
---

## 🏆 Recommended Vendor: {winner['vendor_name']}

**Overall Score**: {winner['overall_score']}/100

"""
        
        # Criterion rankings
        criterion_rankings = comparison.get("criterion_rankings", {})
        if criterion_rankings:
            report += """---

## Criterion Rankings

"""
            for criterion, vendor_ids in criterion_rankings.items():
                report += f"### {criterion.title()}\n"
                for i, vid in enumerate(vendor_ids[:3], 1):
                    vendor = next((a for a in analyses if a['vendor_id'] == vid), None)
                    if vendor:
                        score = vendor['breakdown'].get(criterion, {}).get('score', 'N/A')
                        report += f"{i}. {vendor['vendor_name']} ({score}/100)\n"
                report += "\n"
        
        return report
    
    async def market_report(
        self,
        intelligence: MarketIntelligence,
        format: str = "markdown"
    ) -> str:
        """
        Generate a market intelligence report.
        
        Args:
            intelligence: MarketIntelligence object
            format: Output format
            
        Returns:
            Formatted report string
        """
        if format == "json":
            return json.dumps(intelligence.model_dump(), indent=2, default=str)
        
        report = f"""# Market Intelligence Report

**Query**: {intelligence.query}  
**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## Executive Summary

{intelligence.summary}

---

## Key Findings

"""
        
        for finding in intelligence.findings:
            report += f"- {finding.get('finding', finding)}\n"
        
        if intelligence.trends:
            report += """
---

## Market Trends

"""
            for trend in intelligence.trends:
                report += f"📈 {trend}\n\n"
        
        if intelligence.risks or intelligence.opportunities:
            report += """---

## Risk & Opportunity Analysis

"""
            if intelligence.risks:
                report += "### ⚠️ Risks\n"
                for risk in intelligence.risks:
                    report += f"- {risk}\n"
            
            if intelligence.opportunities:
                report += "\n### 💡 Opportunities\n"
                for opp in intelligence.opportunities:
                    report += f"- {opp}\n"
        
        if intelligence.sources:
            report += """
---

## Sources

"""
            for source in intelligence.sources:
                if isinstance(source, dict):
                    report += f"- [{source.get('title', 'Source')}]({source.get('url', '#')})\n"
                else:
                    report += f"- {source}\n"
        
        return report
    
    def _score_bar(self, score: int, width: int = 10) -> str:
        """Generate a visual score bar."""
        filled = int((score / 100) * width)
        empty = width - filled
        
        if score >= 70:
            char = "🟢"
        elif score >= 50:
            char = "🟡"
        else:
            char = "🔴"
        
        return f"[{'█' * filled}{'░' * empty}]"
