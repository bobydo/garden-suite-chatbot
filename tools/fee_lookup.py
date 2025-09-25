from typing import Dict, Any
from qdrant_client import QdrantClient
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Qdrant as QdrantVS
from service.log_helper import LogHelper
from config import QDRANT_HOST, QDRANT_PORT, WEBSITE_COLLECTION, EMBED_MODEL
import re


class FeeLookup:
    """Real fee lookup tool that searches Qdrant GUIDES_COLLECTION for current permit fees."""
    
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.logger = LogHelper.get_logger("Tools.FeeLookup")
        
    def find(self, item: str) -> Dict[str, Any]:
        """
        Find current permit fees for garden suite related items.
        
        Args:
            item: The fee item to search for (e.g., "development permit", "building permit", "garden suite")
        
        Returns:
            Dict with text, url, amount, and confidence score
        """
        try:
            # Create vector store connection
            guides_db = QdrantVS(
                client=self.client,
                embedding_function=self.embeddings.embed_query,
                collection_name=WEBSITE_COLLECTION
            )
            
            # Build search query focused on fees
            search_query = self._build_fee_search_query(item)
            
            # Search for fee information
            results = guides_db.similarity_search_with_score(search_query, k=5)
            
            if not results:
                self.logger.warning(f"No fee information found for: {item}")
                return {
                    "text": f"No fee information found for '{item}'. Please check the official Edmonton website for current fees.",
                    "url": "https://www.edmonton.ca/permits_development/fees",
                    "amount": "Not found",
                    "confidence": 0.0
                }
            
            # Find the best result that contains fee information
            best_result = self._find_best_fee_result(results, item)
            
            if not best_result:
                return {
                    "text": f"Fee information for '{item}' may be available but not clearly stated in the retrieved content.",
                    "url": "https://www.edmonton.ca/permits_development/fees",
                    "amount": "See website",
                    "confidence": 0.3
                }
            
            doc, score = best_result
            
            # Extract fee amount if possible
            fee_amount = self._extract_fee_amount(doc.page_content)
            
            # Get URL from metadata
            url = doc.metadata.get('url', doc.metadata.get('source', 'https://www.edmonton.ca/permits_development/fees'))
            
            result = {
                "text": doc.page_content[:400] + "..." if len(doc.page_content) > 400 else doc.page_content,
                "url": url,
                "amount": fee_amount,
                "confidence": float(1 - score)  # Convert distance to confidence
            }
            
            self.logger.info(f"Found fee info for '{item}': {fee_amount}")
            return result
            
        except Exception as e:
            self.logger.error(f"Fee lookup failed for '{item}': {e}")
            return {
                "text": f"Error retrieving fee information: {str(e)}",
                "url": "https://www.edmonton.ca/permits_development/fees",
                "amount": "Error",
                "confidence": 0.0
            }
    
    def _build_fee_search_query(self, item: str) -> str:
        """Build a search query focused on fees."""
        # Add fee-related terms to improve search accuracy
        fee_terms = ["fee", "cost", "price", "permit", "application"]
        query_parts = [item] + fee_terms
        
        # Add specific garden suite terms
        if "garden" not in item.lower() and "suite" not in item.lower():
            query_parts.extend(["garden suite", "backyard housing"])
        
        return " ".join(query_parts)
    
    def _find_best_fee_result(self, results, item: str):
        """Find the result that most likely contains fee information."""
        fee_keywords = ["$", "fee", "cost", "price", "dollar", "amount", "charge"]
        
        for doc, score in results:
            content_lower = doc.page_content.lower()
            
            # Check if content contains fee-related keywords
            if any(keyword in content_lower for keyword in fee_keywords):
                return (doc, score)
        
        # If no explicit fee content found, return the first result
        return results[0] if results else None
    
    def _extract_fee_amount(self, content: str) -> str:
        """Extract fee amounts from text content."""
        # Patterns to match various fee formats
        patterns = [
            r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # $123.45, $1,234.56
            r'\$\d+',  # $123
            r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*dollars?',  # 123.45 dollars
            r'fee\s+(?:is|of|:)\s*\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # fee is $123.45
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Return the first match, clean it up
                return matches[0].strip()
        
        # If no specific amount found, look for general fee references
        if any(word in content.lower() for word in ["fee", "cost", "charge"]):
            return "See content for details"
        
        return "Amount not specified"
