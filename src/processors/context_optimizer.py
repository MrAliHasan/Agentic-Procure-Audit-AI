"""
Context Optimizer - Smart selection and compression of context for LLM
Uses embeddings to rank relevance and HTML cleaning to extract clean text
"""
import re
from typing import Optional
from bs4 import BeautifulSoup


class ContextOptimizer:
    """
    Optimizes context sent to LLM by:
    1. Ranking content by relevance using embeddings
    2. Cleaning HTML to extract clean text
    3. Compressing/summarizing long content
    """
    
    def __init__(self):
        self._embeddings = None
    
    def _get_embeddings(self):
        """Lazy load embeddings model."""
        if self._embeddings is None:
            from src.llm.embeddings import get_embeddings
            self._embeddings = get_embeddings()
        return self._embeddings
    
    def clean_html(self, html_content: str) -> str:
        """
        Clean HTML to extract pure text content.
        Removes tags, scripts, styles while preserving structure.
        """
        if not html_content:
            return ""
        
        # If it looks like HTML
        if "<" in html_content and ">" in html_content:
            try:
                soup = BeautifulSoup(html_content, "lxml")
                
                # Remove script, style, nav, footer, aside
                for element in soup(["script", "style", "nav", "footer", "aside", "header", "noscript"]):
                    element.decompose()
                
                # Get text with newlines preserved
                text = soup.get_text(separator="\n", strip=True)
                
                # Clean up multiple newlines
                text = re.sub(r'\n{3,}', '\n\n', text)
                
                return text
            except Exception:
                pass
        
        # Already plain text
        return html_content
    
    def extract_key_content(self, text: str, max_length: int = 3000) -> str:
        """
        Extract key content from text, prioritizing:
        - Prices and numbers
        - Product names
        - Key facts and specifications
        """
        if len(text) <= max_length:
            return text
        
        lines = text.split('\n')
        
        # Score each line
        scored_lines = []
        for line in lines:
            score = 0
            line_stripped = line.strip()
            
            if not line_stripped or len(line_stripped) < 10:
                continue
            
            # Boost lines with prices
            if re.search(r'\$[\d,]+\.?\d*', line_stripped):
                score += 10
            
            # Boost lines with numbers (specs)
            if re.search(r'\d+', line_stripped):
                score += 2
            
            # Boost lines with key terms
            key_terms = ['price', 'cost', 'quality', 'rating', 'review', 'stock', 'available', 
                        'specification', 'datasheet', 'manufacturer', 'part number']
            for term in key_terms:
                if term.lower() in line_stripped.lower():
                    score += 3
            
            # Penalize very long lines (probably navigation/menus)
            if len(line_stripped) > 200:
                score -= 2
            
            scored_lines.append((score, line_stripped))
        
        # Sort by score descending
        scored_lines.sort(key=lambda x: x[0], reverse=True)
        
        # Take highest scoring lines up to max_length
        result = []
        current_length = 0
        
        for score, line in scored_lines:
            if current_length + len(line) + 1 <= max_length:
                result.append(line)
                current_length += len(line) + 1
        
        return '\n'.join(result)
    
    async def rank_by_relevance(
        self,
        query: str,
        contents: list[dict],
        content_key: str = "content"
    ) -> list[dict]:
        """
        Rank content items by relevance to query using embeddings.
        
        Args:
            query: The search query
            contents: List of dicts with content
            content_key: Key in dict containing the text content
            
        Returns:
            Contents sorted by relevance (highest first)
        """
        if not contents:
            return []
        
        try:
            embeddings = self._get_embeddings()
            
            # Get query embedding
            query_embedding = embeddings.embed_query(query)
            
            # Get content embeddings and calculate similarity
            scored_contents = []
            for item in contents:
                content = item.get(content_key, "")[:2000]  # Limit for embedding
                if not content:
                    scored_contents.append((0, item))
                    continue
                
                content_embedding = embeddings.embed_query(content)
                
                # Cosine similarity
                similarity = self._cosine_similarity(query_embedding, content_embedding)
                scored_contents.append((similarity, item))
            
            # Sort by similarity descending
            scored_contents.sort(key=lambda x: x[0], reverse=True)
            
            # Add relevance score to items
            result = []
            for score, item in scored_contents:
                item["relevance_score"] = round(score, 3)
                result.append(item)
            
            return result
            
        except Exception as e:
            print(f"Ranking failed: {e}")
            return contents  # Return original order if ranking fails
    
    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def optimize_context(
        self,
        query: str,
        pages: list[dict],
        max_total_chars: int = 25000,
        max_chars_per_page: int = 3000
    ) -> dict:
        """
        Optimize context for LLM by:
        1. Cleaning HTML from all pages
        2. Ranking by relevance to query
        3. Selecting best content up to max_total_chars
        
        Args:
            query: The search query
            pages: List of page dicts with 'content', 'title', 'url'
            max_total_chars: Maximum total characters to return
            max_chars_per_page: Maximum characters per page
            
        Returns:
            Optimized context dict with pages and stats
        """
        if not pages:
            return {"pages": [], "total_chars": 0, "pages_included": 0}
        
        # Step 1: Clean HTML from all pages
        for page in pages:
            raw_content = page.get("content", "")
            page["clean_content"] = self.clean_html(raw_content)
        
        # Step 2: Rank by relevance
        ranked_pages = await self.rank_by_relevance(query, pages, content_key="clean_content")
        
        # Step 3: Select pages up to max_total_chars
        selected_pages = []
        total_chars = 0
        
        for page in ranked_pages:
            clean_content = page.get("clean_content", "")
            
            # Extract key content (prioritizing prices, specs)
            key_content = self.extract_key_content(clean_content, max_chars_per_page)
            
            if total_chars + len(key_content) <= max_total_chars:
                selected_pages.append({
                    "title": page.get("title", "")[:150],
                    "url": page.get("url", ""),
                    "content": key_content,
                    "relevance": page.get("relevance_score", 0)
                })
                total_chars += len(key_content)
        
        return {
            "pages": selected_pages,
            "total_chars": total_chars,
            "pages_included": len(selected_pages),
            "pages_available": len(pages)
        }
    
    def format_for_llm(self, optimized_context: dict) -> str:
        """
        Format optimized context for LLM consumption.
        
        Returns clean, structured text ready for the prompt.
        """
        pages = optimized_context.get("pages", [])
        
        if not pages:
            return "No relevant web content available."
        
        sections = []
        sections.append(f"**Web Research ({optimized_context.get('pages_included', 0)} of {optimized_context.get('pages_available', 0)} pages, ranked by relevance):**\n")
        
        for i, page in enumerate(pages, 1):
            sections.append(f"### Source {i}: {page['title']}")
            sections.append(f"URL: {page['url']}")
            sections.append(f"Relevance: {page.get('relevance', 0):.2f}")
            sections.append(f"\n{page['content']}\n")
            sections.append("---")
        
        return "\n".join(sections)
