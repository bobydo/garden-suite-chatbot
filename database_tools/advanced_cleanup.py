#!/usr/bin/env python3
"""
Advanced cleanup script to find and remove all corrupted binary data points.
This scans all collections for points with excessive binary/special characters.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, PointIdsList
from service.log_helper import LogHelper
import config
from typing import List, Sequence, cast

def is_likely_corrupted(content: str, threshold: float = 0.2) -> bool:
    """
    Check if content appears to be corrupted binary data.
    
    Args:
        content: Text content to check
        threshold: Ratio of special chars that indicates corruption (0.0-1.0)
    
    Returns:
        True if content appears corrupted
    """
    if not content or len(content) < 50:  # Skip very short content
        return False
    
    # Count problematic characters
    special_chars = sum(1 for c in content if ord(c) < 32 or ord(c) > 126)
    special_ratio = special_chars / len(content)
    
    # Additional checks for common binary patterns
    has_null_bytes = '\x00' in content
    has_many_question_marks = content.count('ï¿½') > 10  # UTF-8 replacement chars
    starts_with_binary = any(content.startswith(pattern) for pattern in ['\x00', 'PK\x03\x04'])
    
    return (special_ratio > threshold or 
            has_null_bytes or 
            has_many_question_marks or 
            starts_with_binary)

def find_corrupted_points(collection_name: str, batch_size: int = 100) -> List[str]:
    """Find all corrupted point IDs in a collection."""
    
    logger = LogHelper.get_logger("FindCorrupted")
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    
    corrupted_ids = []
    offset = None
    
    logger.info(f"Scanning {collection_name} for corrupted points...")
    
    while True:
        # Get batch of points
        result = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True
        )
        
        points = result[0]
        if not points:
            break
            
        # Check each point for corruption
        for point in points:
            if not point.payload:
                continue
                
            content = point.payload.get('page_content', '')
            if is_likely_corrupted(content):
                corrupted_ids.append(point.id)
                
                # Log details about corrupted point
                url = point.payload.get('url', 'N/A')
                source = point.payload.get('source', 'N/A')
                preview = content[:100].replace('\x00', '\\x00').replace('\n', '\\n')
                logger.warning(f"Corrupted point {point.id}: URL={url}, Source={source}")
                logger.warning(f"  Preview: {preview}...")
        
        # Update offset for next batch
        offset = result[1] if result[1] else None
        if offset is None:
            break
    
    logger.info(f"Found {len(corrupted_ids)} corrupted points in {collection_name}")
    return corrupted_ids

def delete_corrupted_points(collection_name: str, point_ids: List[str]) -> bool:
    """Delete corrupted points by their IDs."""
    
    logger = LogHelper.get_logger("DeleteCorrupted")
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    
    if not point_ids:
        logger.info(f"No corrupted points to delete in {collection_name}")
        return True
        
    try:
        logger.info(f"Deleting {len(point_ids)} corrupted points from {collection_name}...")
        
        # Qdrant expects a list of ExtendedPointId (int | str). Ensure correct type for static checker.
        ids_seq: Sequence[str] = cast(Sequence[str], point_ids)
        client.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(points=list(ids_seq)),
            wait=True
        )
        
        logger.info(f"✅ Successfully deleted {len(point_ids)} corrupted points")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete corrupted points: {e}")
        return False

def cleanup_all_collections():
    """Find and remove corrupted points from all collections."""
    
    logger = LogHelper.get_logger("CleanupAll")
    collections = [config.WEBSITE_COLLECTION, config.PDF_COLLECTION, config.EXCEL_COLLECTION]
    
    total_removed = 0
    
    for collection in collections:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing collection: {collection}")
            logger.info(f"{'='*60}")
            
            # Find corrupted points
            corrupted_ids = find_corrupted_points(collection)
            
            if corrupted_ids:
                # Show summary before deletion
                print(f"\n🚨 Found {len(corrupted_ids)} corrupted points in {collection}")
                response = input("Delete these corrupted points? (y/N): ")
                
                if response.lower() in ['y', 'yes']:
                    success = delete_corrupted_points(collection, corrupted_ids)
                    if success:
                        total_removed += len(corrupted_ids)
                else:
                    logger.info("Skipped deletion for this collection")
            else:
                logger.info(f"✅ No corrupted points found in {collection}")
                
        except Exception as e:
            logger.error(f"Failed to process collection {collection}: {e}")
    
    logger.info(f"\n🎉 Cleanup complete! Removed {total_removed} corrupted points total")

if __name__ == "__main__":
    print("🔍 Advanced corruption detection and cleanup")
    print("This will scan all collections for binary garbage and corrupted data")
    print("=" * 70)
    
    cleanup_all_collections()