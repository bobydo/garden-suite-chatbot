from typing import Optional, Dict, Any
from qdrant_client import QdrantClient
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Qdrant as QdrantVS
from service.log_helper import LogHelper
from config import QDRANT_HOST, QDRANT_PORT, BYLAW_COLLECTION, EMBED_MODEL


class BylawLookup:
    """Real bylaw lookup tool that searches Qdrant BYLAW_COLLECTION for precise bylaw sections."""
    
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.logger = LogHelper.get_logger("Tools.BylawLookup")
        
    def find(self, section_or_term: str, zone: Optional[str] = None, lot_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Find specific bylaw sections related to garden suites.
        
        Args:
            section_or_term: The bylaw section number or search term (e.g., "610", "pedestrian access")
            zone: Optional zone type (e.g., "RF1", "RF3") to filter results
            lot_context: Optional dict with lot details like {"width": 15, "area": 400}
        
        Returns:
            Dict with text, section, url, and confidence score
        """
        try:
            # Create vector store connection
            bylaw_db = QdrantVS(
                client=self.client,
                embedding_function=self.embeddings.embed_query,
                collection_name=BYLAW_COLLECTION
            )
            
            # Build enhanced search query
            search_query = self._build_search_query(section_or_term, zone, lot_context)
            
            # Search for relevant bylaw sections
            results = bylaw_db.similarity_search_with_score(search_query, k=3)
            
            if not results:
                self.logger.warning(f"No bylaw results found for: {section_or_term}")
                return {
                    "text": f"No specific bylaw information found for '{section_or_term}'. Please try a more general search term.",
                    "section": "Not found",
                    "url": "",
                    "confidence": 0.0
                }
            
            # Get the best match
            best_doc, score = results[0]
            
            # Extract section number if available in metadata or content
            section = self._extract_section_number(best_doc.page_content, best_doc.metadata)
            
            # Get URL from metadata
            url = best_doc.metadata.get('url', best_doc.metadata.get('source', ''))
            
            result = {
                "text": best_doc.page_content[:500] + "..." if len(best_doc.page_content) > 500 else best_doc.page_content,
                "section": section,
                "url": url,
                "confidence": float(1 - score)  # Convert distance to confidence (lower distance = higher confidence)
            }
            
            self.logger.info(f"Found bylaw result for '{section_or_term}': {section}")
            return result
            
        except Exception as e:
            self.logger.error(f"Bylaw lookup failed for '{section_or_term}': {e}")
            return {
                "text": f"Error retrieving bylaw information: {str(e)}",
                "section": "Error",
                "url": "",
                "confidence": 0.0
            }
    
    def _build_search_query(self, section_or_term: str, zone: Optional[str], lot_context: Optional[Dict[str, Any]]) -> str:
        """Build an enhanced search query with context."""
        query_parts = [section_or_term]
        
        # Add zone context if provided
        if zone:
            query_parts.append(f"zone {zone}")
        
        # Add lot context if provided
        if lot_context:
            if lot_context.get("width"):
                query_parts.append(f"lot width {lot_context['width']}m")
            if lot_context.get("area"):
                query_parts.append(f"lot area {lot_context['area']}m2")
        
        # Always include garden suite context
        query_parts.extend(["garden suite", "backyard housing"])
        
        return " ".join(query_parts)
    
    def _extract_section_number(self, content: str, metadata: Dict[str, Any]) -> str:
        """Extract bylaw section number from content or metadata."""
        import re
        
        # Try to find section numbers in various formats
        patterns = [
            r'section\s+(\d+(?:\.\d+)*(?:\([a-z]\))?)',
            r's\.?\s*(\d+(?:\.\d+)*(?:\([a-z]\))?)',
            r'(\d+(?:\.\d+)+(?:\([a-z]\))?)',
            r'Section\s+(\d+(?:\.\d+)*(?:\([a-z]\))?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return f"s.{match.group(1)}"
        
        # Fallback to metadata if available
        return metadata.get('section', 'Unknown section')
