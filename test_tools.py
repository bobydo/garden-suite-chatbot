#!/usr/bin/env python3
"""
Test script to verify the tools integration works correctly.
Run this after setting up Qdrant and ingesting data.
"""

from tools.bylaw_lookup import BylawLookup
from tools.fee_lookup import FeeLookup
from service.pipeline_service import PipelineService
from service.log_helper import LogHelper

logger = LogHelper.get_logger("TestTools")

def test_bylaw_lookup():
    """Test the BylawLookup tool."""
    print("\n=== Testing BylawLookup ===")
    
    bylaw_tool = BylawLookup()
    
    # Test cases
    test_cases = [
        "pedestrian access",
        "610", 
        "setback requirements",
        "parking requirements"
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: '{test_case}'")
        try:
            result = bylaw_tool.find(test_case)
            print(f"Section: {result['section']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Text preview: {result['text'][:100]}...")
            print(f"URL: {result['url']}")
        except Exception as e:
            print(f"Error: {e}")

def test_fee_lookup():
    """Test the FeeLookup tool."""
    print("\n=== Testing FeeLookup ===")
    
    fee_tool = FeeLookup()
    
    # Test cases
    test_cases = [
        "development permit",
        "building permit", 
        "garden suite fee",
        "application cost"
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: '{test_case}'")
        try:
            result = fee_tool.find(test_case)
            print(f"Amount: {result['amount']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Text preview: {result['text'][:100]}...")
            print(f"URL: {result['url']}")
        except Exception as e:
            print(f"Error: {e}")

def test_pipeline_agent():
    """Test the integrated pipeline with agent."""
    print("\n=== Testing PipelineService with Agents ===")
    
    try:
        pipeline = PipelineService(use_agents=True)
        
        test_questions = [
            "What are the setback requirements for garden suites?",
            "How much does a development permit cost?",
            "What is section 610 about?",
            "Tell me about parking requirements for garden suites"
        ]
        
        for question in test_questions:
            print(f"\nQuestion: {question}")
            try:
                answer = pipeline.run_chat(question)
                print(f"Answer: {answer[:200]}...")
            except Exception as e:
                print(f"Error processing question: {e}")
                
    except Exception as e:
        print(f"Failed to initialize pipeline: {e}")

def test_pipeline_fallback():
    """Test the pipeline with RAG fallback."""
    print("\n=== Testing PipelineService RAG Fallback ===")
    
    try:
        pipeline = PipelineService(use_agents=False)  # Force RAG mode
        
        question = "What are garden suite regulations?"
        print(f"\nQuestion: {question}")
        answer = pipeline.run_chat(question)
        print(f"Answer: {answer[:200]}...")
        
    except Exception as e:
        print(f"Failed RAG fallback test: {e}")

if __name__ == "__main__":
    logger.info("Starting tool integration tests...")
    
    print("Garden Suite Chatbot - Tools Integration Test")
    print("=" * 50)
    
    # Test individual tools
    test_bylaw_lookup()
    test_fee_lookup()
    
    # Test integrated pipeline
    test_pipeline_agent()
    test_pipeline_fallback()
    
    print("\n" + "=" * 50)
    print("Test completed! Check logs for detailed information.")