#!/usr/bin/env python3
"""
Quick test script for Gemini integration
Tests the novel crawler with local WordPress instance
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from config_loader import load_config
from gemini_translator import GeminiTranslator


def test_gemini_connection():
    """Test if Gemini API is working"""
    print("="*60)
    print("Testing Gemini API Connection")
    print("="*60)
    
    # Load config
    config = load_config('config.json')
    gemini_api_key = config.get('gemini_api_key', '')
    
    if not gemini_api_key:
        print("❌ ERROR: No Gemini API key found in config.json")
        print("Please add your API key to config.json:")
        print('  "gemini_api_key": "YOUR_API_KEY_HERE"')
        return False
    
    print(f"✓ API Key found: {gemini_api_key[:10]}...{gemini_api_key[-5:]}")
    
    # Initialize Gemini translator
    def log(msg):
        print(f"  {msg}")
    
    translator = GeminiTranslator(gemini_api_key, log)
    
    if not translator.client:
        print("❌ ERROR: Gemini client initialization failed")
        return False
    
    print("✓ Gemini client initialized successfully")
    
    # Test translation
    print("\n" + "-"*60)
    print("Testing Description Translation")
    print("-"*60)
    
    test_description = """
    <div class="describe-html">
        <p>这是一部修真小说，讲述了主人公林羽的修仙之路。</p>
        <p>从一个普通的少年，一步步成长为强大的修士。</p>
        <p>最近更新：第100章</p>
        <p>状态：连载中</p>
    </div>
    """
    
    translated = translator.translate_description(test_description)
    print(f"\nOriginal:\n{test_description}")
    print(f"\nTranslated:\n{translated}")
    
    # Test chapter translation with mock glossary
    print("\n" + "-"*60)
    print("Testing Chapter Content Translation")
    print("-"*60)
    
    test_content = """
    林羽站在青云宗的山门前，看着眼前的一切。
    他刚刚突破到筑基期，感受到体内澎湃的灵气。
    "终于成功了！"他心中激动不已。
    """
    
    mock_glossary = {
        "林羽": "Lin Yu",
        "青云宗": "Azure Cloud Sect",
        "筑基期": "Foundation Establishment",
        "灵气": "Spiritual Energy"
    }
    
    translated_content, success = translator.translate_chapter_content(
        test_content, 1, mock_glossary
    )
    
    if success:
        print(f"\nOriginal:\n{test_content}")
        print(f"\nTranslated:\n{translated_content}")
        print("\n✓ Chapter translation successful")
    else:
        print("\n❌ Chapter translation failed")
        return False
    
    print("\n" + "="*60)
    print("✅ All tests passed! Gemini integration is working.")
    print("="*60)
    return True


def test_wordpress_connection():
    """Test WordPress API connection"""
    print("\n" + "="*60)
    print("Testing WordPress API Connection")
    print("="*60)
    
    config = load_config('config.json')
    wordpress_url = config.get('wordpress_url', '')
    api_key = config.get('api_key', '')
    
    if not wordpress_url or not api_key:
        print("❌ ERROR: WordPress URL or API key not configured")
        return False
    
    print(f"✓ WordPress URL: {wordpress_url}")
    print(f"✓ API Key: {api_key[:10]}...{api_key[-5:]}")
    
    from wordpress_api import WordPressAPI
    
    def log(msg):
        print(f"  {msg}")
    
    wp = WordPressAPI(wordpress_url, api_key, log)
    
    success, result = wp.test_connection()
    
    if success:
        print(f"✓ Connected to WordPress v{result.get('wordpress', 'unknown')}")
        print(f"✓ PHP v{result.get('php', 'unknown')}")
        print("\n✅ WordPress connection successful!")
        return True
    else:
        print(f"❌ Connection failed: {result}")
        return False


if __name__ == '__main__':
    print("\n🧪 Novel Crawler - Integration Test\n")
    
    # Test Gemini
    gemini_ok = test_gemini_connection()
    
    # Test WordPress
    wordpress_ok = test_wordpress_connection()
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Gemini API:     {'✅ PASS' if gemini_ok else '❌ FAIL'}")
    print(f"WordPress API:  {'✅ PASS' if wordpress_ok else '❌ FAIL'}")
    
    if gemini_ok and wordpress_ok:
        print("\n🎉 All systems operational! Ready to crawl novels.")
        print("\nTry crawling a test novel:")
        print("  python crawler.py https://www.xbanxia.cc/books/396508.html")
    else:
        print("\n⚠️  Please fix the errors above before crawling.")
        sys.exit(1)
