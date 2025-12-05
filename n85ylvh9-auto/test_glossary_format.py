#!/usr/bin/env python3
"""
Test script to verify glossary txt format works correctly
"""

import os
import sys
import tempfile

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from gemini_translator import GeminiTranslator


def test_glossary_txt_format():
    """Test that glossary saves and loads correctly in txt format"""
    print("="*60)
    print("Testing Glossary TXT Format")
    print("="*60)
    
    # Mock logger
    logs = []
    def log(msg):
        logs.append(msg)
        print(f"  {msg}")
    
    # Create translator (no API key needed for this test)
    translator = GeminiTranslator("", log)
    
    # Create test glossary
    test_glossary = {
        "林羽": "Lin Yu",
        "青云宗": "Azure Cloud Sect",
        "筑基期": "Foundation Establishment",
        "灵气": "Spiritual Energy",
        "修真": "Cultivation"
    }
    
    translator.glossary = test_glossary
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        novel_id = "test_novel_123"
        novel_dir = os.path.join(tmpdir, 'novels', f'novel_{novel_id}')
        os.makedirs(novel_dir, exist_ok=True)
        
        # Override the novels directory path for testing
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            # Test saving
            print("\n1. Testing save_glossary...")
            translator.save_glossary(novel_id, None)
            
            glossary_path = os.path.join(novel_dir, 'glossary.txt')
            assert os.path.exists(glossary_path), "Glossary file was not created"
            print(f"   ✓ Glossary file created: {glossary_path}")
            
            # Verify content
            with open(glossary_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"\n   File content:")
            for line in content.strip().split('\n'):
                print(f"     {line}")
            
            # Test loading
            print("\n2. Testing load_glossary...")
            translator2 = GeminiTranslator("", log)
            result = translator2.load_glossary(novel_id)
            
            assert result == True, "load_glossary returned False"
            assert len(translator2.glossary) == len(test_glossary), f"Expected {len(test_glossary)} entries, got {len(translator2.glossary)}"
            
            print(f"   ✓ Loaded {len(translator2.glossary)} entries")
            
            # Verify each entry
            for chinese, english in test_glossary.items():
                assert chinese in translator2.glossary, f"Missing entry: {chinese}"
                assert translator2.glossary[chinese] == english, f"Wrong translation: {chinese} -> {translator2.glossary[chinese]} (expected {english})"
            
            print("\n   Loaded glossary entries:")
            for chinese, english in translator2.glossary.items():
                print(f"     {chinese} = {english}")
            
            print("\n" + "="*60)
            print("✅ All tests passed!")
            print("="*60)
            return True
            
        finally:
            os.chdir(original_dir)


if __name__ == '__main__':
    try:
        success = test_glossary_txt_format()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
