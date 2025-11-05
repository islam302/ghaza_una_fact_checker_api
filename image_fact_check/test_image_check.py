"""
Test script for Image Fact Check API
Usage: python image_fact_check/test_image_check.py
"""
import requests
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/image_check/"


def test_image_check(image_path: str, lang: str = None):
    """
    Test the image fact-check endpoint
    
    Args:
        image_path: Path to image file
        lang: Optional language code (ar, en, fr, es, etc.)
    """
    print(f"🧪 Testing Image Fact Check API")
    print(f"📍 Endpoint: {ENDPOINT}")
    print(f"🖼️  Image: {image_path}")
    print(f"🌐 Language: {lang or 'Auto-detect'}")
    print("-" * 60)
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Error: Image file not found: {image_path}")
        return
    
    try:
        # Prepare request
        files = {'image': open(image_path, 'rb')}
        params = {}
        if lang:
            params['lang'] = lang
        
        print("📤 Sending request...")
        response = requests.post(ENDPOINT, files=files, params=params)
        
        # Close file
        files['image'].close()
        
        # Check response
        print(f"📥 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS!\n")
            print(f"🤖 Is AI Generated: {result.get('is_ai_generated')}")
            print(f"📊 AI Confidence: {result.get('ai_confidence', 0):.2%}")
            print(f"🌐 Language: {result.get('language', 'unknown')}")
            
            if result.get('ai_indicators'):
                print(f"\n🔍 AI Indicators:")
                for indicator in result.get('ai_indicators', [])[:5]:
                    print(f"   • {indicator}")
            
            fact_check = result.get('fact_check', {})
            print(f"\n📋 Fact Check Result: {fact_check.get('case', 'N/A')}")
            if fact_check.get('extracted_text'):
                print(f"\n📝 Extracted Text: {fact_check.get('extracted_text')[:200]}...")
            if fact_check.get('claims'):
                print(f"\n💬 Claims Found:")
                for claim in fact_check.get('claims', [])[:3]:
                    print(f"   • {claim}")
            
            if fact_check.get('sources'):
                print(f"\n📚 Verification Sources: {len(fact_check.get('sources', []))} found")
            
            image_analysis = result.get('image_analysis', {})
            if image_analysis.get('description'):
                print(f"\n🖼️  Image Description:")
                print(f"   {image_analysis.get('description')[:300]}...")
        else:
            print("\n❌ ERROR!")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server.")
        print("   Make sure Django server is running: python manage.py runserver")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Image Fact Check API")
    parser.add_argument("image_path", help="Path to image file")
    parser.add_argument("--lang", "-l", help="Language code (ar, en, fr, es, etc.)", default=None)
    parser.add_argument("--url", "-u", help="Base URL (default: http://localhost:8000)", 
                       default="http://localhost:8000")
    
    args = parser.parse_args()
    
    if args.url != BASE_URL:
        global ENDPOINT
        BASE_URL = args.url.rstrip('/')
        ENDPOINT = f"{BASE_URL}/image_check/"
    
    test_image_check(args.image_path, args.lang)

