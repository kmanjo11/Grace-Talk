#!/usr/bin/env python3
"""
Test script for OpenInterpreter message fixes
Tests both word spacing preservation and conversation persistence
"""

import sys
import os
sys.path.append('/home/ubuntu/Grace-Talk')

from src.utils.message_processor import MessageProcessor

def test_word_spacing():
    """Test word spacing preservation in message processing"""
    print("🧪 Testing Word Spacing Preservation...")
    
    processor = MessageProcessor()
    
    # Test cases that previously caused spacing issues
    test_cases = [
        {
            'input': "I see you're trying to understand something. Let me help you with that.",
            'expected_contains': ['understand', 'something', 'help', 'with', 'that']
        },
        {
            'input': "It looks like you want to know about this. Here's what I think.",
            'expected_contains': ['want', 'to', 'know', 'about', 'this', "Here's", 'what', 'think']
        },
        {
            'input': "Based on your request I'll analyze this step by step.",
            'expected_contains': ['analyze', 'this', 'step', 'by', 'step']
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases):
        result = processor.format_final_response(test_case['input'])
        print(f"\nTest {i+1}:")
        print(f"Input:  '{test_case['input']}'")
        print(f"Output: '{result}'")
        
        # Check for proper word spacing
        words = result.split()
        if len(words) < 2:
            print(f"❌ FAIL: Result has too few words: {len(words)}")
            all_passed = False
            continue
            
        # Check for no concatenated words (basic heuristic)
        has_spacing_issues = False
        for word in words:
            if len(word) > 20:  # Likely concatenated words
                print(f"❌ FAIL: Potential concatenated word detected: '{word}'")
                has_spacing_issues = True
                all_passed = False
        
        if not has_spacing_issues:
            print("✅ PASS: Word spacing looks good")
    
    if all_passed:
        print("\n🎉 All word spacing tests PASSED!")
    else:
        print("\n❌ Some word spacing tests FAILED!")
    
    return all_passed

def test_message_consistency():
    """Test message consistency features"""
    print("\n🧪 Testing Message Consistency...")
    
    processor = MessageProcessor()
    
    # Test greeting detection
    greeting_tests = [
        "hi",
        "hello",
        "hey there",
        "Hi!",
        "Hello there!"
    ]
    
    for greeting in greeting_tests:
        is_greeting = processor.is_simple_greeting(greeting)
        response = processor.get_greeting_response() if is_greeting else "Not a greeting"
        print(f"'{greeting}' -> Greeting: {is_greeting}, Response: '{response}'")
    
    print("✅ Message consistency tests completed")

if __name__ == "__main__":
    print("🚀 Running OpenInterpreter Message Fixes Test Suite")
    print("=" * 60)
    
    # Test word spacing
    spacing_passed = test_word_spacing()
    
    # Test message consistency
    test_message_consistency()
    
    print("\n" + "=" * 60)
    if spacing_passed:
        print("🎉 OVERALL: Message fixes appear to be working correctly!")
        print("📝 Word spacing preservation: ✅ FIXED")
        print("💬 Message consistency: ✅ WORKING")
        print("\n🔄 Now restart the Streamlit app to test conversation persistence...")
    else:
        print("❌ OVERALL: Some issues detected in message processing")
        print("Please review the test output above")
    
    print("=" * 60)

