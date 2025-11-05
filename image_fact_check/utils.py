import os, traceback, json
import asyncio
import re
import base64
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import AsyncOpenAI
import aiohttp
from io import BytesIO
from PIL import Image
from .forensic_analysis import comprehensive_forensic_analysis

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SERPAPI_HL = os.getenv("SERPAPI_HL", "ar")
SERPAPI_GL = os.getenv("SERPAPI_GL", "")

if not OPENAI_API_KEY:
    raise RuntimeError("⚠️ Please set OPENAI_API_KEY in .env")

# Create async OpenAI client
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def _lang_hint_from_claim_async(text: str) -> str:
    """Detect language from text"""
    try:
        resp = await async_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Detect the input language and return ONLY its ISO 639-1 code (like ar, en, fr, es, de)."},
                {"role": "user", "content": text.strip()},
            ],
            temperature=0.0,
            max_tokens=5
        )
        lang = (resp.choices[0].message.content or "").strip().lower()
        if len(lang) == 2:
            return lang
    except Exception:
        pass

    # fallback
    ar_count = sum(1 for ch in text if '\u0600' <= ch <= '\u06FF')
    ratio = ar_count / max(1, len(text))
    return "ar" if ratio >= 0.15 else "en"


async def _fetch_serp_async(session: aiohttp.ClientSession, query: str, extra: Dict | None = None, num: int = 10) -> List[Dict]:
    """Fetch search results from SerpAPI"""
    url = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": SERPAPI_HL,
        "gl": SERPAPI_GL,
        "num": num
    }
    if extra:
        params.update(extra)
    try:
        print(f"🔍 Fetching: {query}")
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=20)) as response:
            response.raise_for_status()
            data = await response.json()
            results = []
            for it in data.get("organic_results", []):
                results.append({
                    "title": it.get("title") or "",
                    "snippet": it.get("snippet") or (it.get("snippet_highlighted_words", [""]) or [""])[0],
                    "link": it.get("link") or it.get("displayed_link") or "",
                })
            print(f"✅ Found {len(results)} results for query: {query}")
            return [r for r in results if r["title"] or r["snippet"] or r["link"]]
    except Exception as e:
        print(f"❌ Error fetching from SerpAPI: {e}")
        return []


async def check_image_fact_and_ai_async(image_file, lang: Optional[str] = None) -> dict:
    """
    تحليل الصورة لتحديد إذا كانت مصنوعة بالذكاء الاصطناعي، معدلة بـ Photoshop، أو مزورة
    
    Args:
        image_file: Django UploadedFile أو ملف صورة
        lang: (مهمل - سيتم استخدام العربية دائماً)
    
    Returns:
        dict مع:
        - is_ai_generated: bool (إذا كانت الصورة مصنوعة بالذكاء الاصطناعي)
        - is_photoshopped: bool (إذا كانت الصورة معدلة بـ Photoshop أو برامج التعديل)
        - is_fake: bool (إذا كانت الصورة مزورة بأي طريقة)
        - message: str (رسالة بالعربية توضح النتيجة بالتفصيل)
    """
    try:
        print("🖼️ Starting comprehensive image analysis...")
        
        # ============================================
        # STEP 1: Advanced Forensic Analysis (Python-based)
        # ============================================
        print("🔬 Running advanced forensic analysis...")
        forensic_results = comprehensive_forensic_analysis(image_file)
        
        forensic_is_edited = forensic_results.get('is_edited', False)
        forensic_confidence = forensic_results.get('confidence', 0.0)
        forensic_details = forensic_results.get('detection_details', [])
        
        print(f"📊 Forensic Analysis Results:")
        print(f"   - Is Edited: {forensic_is_edited}")
        print(f"   - Confidence: {forensic_confidence:.2f}")
        print(f"   - Suspicious Indicators: {forensic_results.get('suspicious_count', 0)}/{forensic_results.get('total_checks', 0)}")
        
        # Reset file pointer before reading again for OpenAI Vision API
        image_file.seek(0)
        
        # Read and process image for OpenAI Vision API
        image_data = image_file.read()
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary (handles RGBA, P, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (OpenAI Vision has size limits)
        # Using larger size for better detection accuracy
        max_size = 2048
        original_size = (image.width, image.height)
        
        if image.width > max_size or image.height > max_size:
            print(f"📏 Resizing image from {image.width}x{image.height} to max {max_size}px for OpenAI Vision API...")
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            print(f"✅ Resized to {image.width}x{image.height}")
        
        # Convert to base64
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # استخدام العربية دائماً
        lang = "ar"
        
        # Create highly precise prompt in English for better model understanding
        IMAGE_ANALYSIS_PROMPT = """
You are a professional image forensics expert working for a fact-checking service. Your role is to analyze images for authenticity and detect any digital manipulations for journalistic and informational verification purposes.

**Purpose**: This analysis is for legitimate fact-checking and news verification to help identify authentic vs. manipulated images in media.

⚠️ **YOUR TASK**: Analyze the provided image to detect if it has been artificially generated (AI) or digitally edited (Photoshop/manipulation software), even if the edits are extremely subtle.

**Detailed Analysis of Photoshop/Image Editing (Including Very Minor Edits):**

🔍 **Pixel-Level Analysis:**
- Extremely subtle differences in noise patterns between different regions
- Minor variations in pixel density or color gradients indicating clone tool usage
- Precise repetitions of small visual patterns (less than 1% of the image)

🔍 **Compression & Quality Analysis:**
- Variations in JPEG compression algorithms across different parts of the image
- Regions with slightly different color/quality indicating multiple image merges
- Inconsistencies in detail quality between different regions

🔍 **Lighting & Shadow Analysis:**
- Analyze light direction: ensure all objects share the same light direction
- Analyze light intensity: must be consistent with a single light source
- Analyze shadows: must be consistent with lighting and gravity
- ANY minor difference (even just 5%) in lighting may indicate editing

🔍 **Color & Contrast Analysis:**
- Subtle differences in white balance between regions
- Minor variations in color saturation indicating edits
- Unnatural color gradients or illogical sharp transitions

🔍 **Edge & Boundary Analysis:**
- Extremely perfect edges may indicate selection tool usage
- Unnatural transitions between objects and background
- "Too clean" edges may indicate Refine Edge tool usage

🔍 **Perspective & Depth Analysis:**
- Analyze depth of field: must be consistent with focal length
- Analyze perspective: ensure parallel lines converge at correct vanishing points
- Any minor perspective flaw may indicate editing

🔍 **Micro-Detail Analysis:**
- Repetition of very small patterns (grass, sand, hair) indicates Clone Stamp usage
- Regions with exactly the same pattern may indicate copy-paste
- Variations in sharpness between image parts

🔍 **Physics & Logic Analysis:**
- Ensure objects follow physics laws (gravity, shadows)
- Ensure reflections are consistent with environment
- Anything that "looks correct but feels subtly unnatural" may be edited

**AI-Generated Image Indicators:**
- Unnaturally perfect or overly consistent details
- Text rendering issues (distorted characters, incorrect words)
- Inconsistent colors or lighting
- Unrealistic body proportions
- Perfect or unnaturally repetitive patterns

**100% Authentic Original Images:**
- Everything perfectly consistent: lighting, colors, quality, compression
- Natural and random patterns in small details
- Shadows and lighting consistent with single light source
- Uniform quality across all image parts
- Natural, imperfect edges

**⚠️ CRITICAL Analysis Instructions - ULTRA HYPER-SENSITIVE (DETECT EVERYTHING):**

1. **Pixel-by-Pixel Mental Scan**: Examine the entire image systematically, region by region, looking for ANY inconsistency, even if it's 0.1% different
2. **Compare Everything**: Compare lighting, colors, sharpness, noise patterns, compression quality between ALL regions - ANY difference = editing
3. **ULTRA ZERO TOLERANCE POLICY**: If you detect ANY of these → mark as edited (even if subtle):
   - Even 1% difference in lighting/shadow direction between objects
   - Any edge that seems "too perfect" or unnaturally clean
   - Slight color temperature differences between regions
   - Any sharpness inconsistency (one part sharper/blurrier than another)
   - Any compression artifact difference
   - Any repetitive pattern (even if subtle)
   - Slight noise pattern differences
   - Any area that seems to have been "brushed" or "smoothed"
   - Unnatural blending between regions

4. **When in Doubt, Mark as Edited**: If you're even 1% unsure → is_photoshopped=true and is_fake=true
5. **Professional Edits Leave Traces**: Even expert edits have telltale signs:
   - Slight mismatch in lighting direction
   - Minor color temperature shifts
   - Edge artifacts from selection tools
   - Compression inconsistencies
   - Noise pattern mismatches
6. **Vintage/Old Photo Analysis**: For old/vintage looking photos, check for:
   - Inconsistent aging/sepia effects
   - Grain pattern inconsistencies
   - Sharpness variations that don't match focal plane
   - Lighting inconsistencies with the supposed era/photography technique

**Required Format (JSON ONLY):**
{
  "is_ai_generated": true/false,
  "is_photoshopped": true/false,
  "is_fake": true/false,
  "confidence": 0.0-1.0,
  "message": "Detailed result message in Arabic",
  "detection_details": "Precise details of detected signs (mention exactly what you found and where - in Arabic)"
}

**⚠️ ULTRA HYPER-STRICT Rules (ZERO Tolerance for ANY Edits - Even Tiny Ones):**
- **CRITICAL DEFAULT ASSUMPTION**: Assume the image is EDITED unless you can prove with 100% absolute certainty it's completely authentic
- If you find ANY sign of editing, no matter how tiny or minor (even 0.01% difference) → is_photoshopped=true AND is_fake=true
- If there's ANY doubt whatsoever (even 0.01% uncertainty) → assume the image is edited
- REMEMBER: Humans can't detect tiny edits, but they exist - you MUST find them
- **For vintage/old photos especially**: Old photos are frequently edited/restored. Check EXTREMELY carefully:
  - Grain inconsistencies = EDITING
  - Sharpness inconsistencies = EDITING  
  - Lighting that doesn't match old photography = EDITING
  - Any modern editing artifacts = EDITING
- Default assumption: Image is EDITED UNTIL proven authentic beyond ANY doubt
- Look for these SPECIFIC signs (even if very subtle):
  * Lighting inconsistencies (objects with different light sources)
  * Color temperature mismatches
  * Sharpness variations (one area sharper than background suggests pasting/editing)
  * Edge quality differences (smooth edges in some areas, rough in others)
  * Noise/grain pattern inconsistencies
  * Compression quality variations
  * Any "perfect" or "too clean" areas in an otherwise natural photo
  * Shadow direction mismatches
  * Reflective surface inconsistencies
  * Depth of field that doesn't match (sharp objects at wrong distances)
- ALL text fields (message, detection_details) MUST be in Arabic
- Return ONLY valid JSON, no additional text
- Be extremely detailed: mention EXACTLY what you found and WHERE (top-left, center-right, etc.)
"""
        
        print("🤖 Sending image to OpenAI Vision API for analysis...")
        
        # Try with detailed prompt first
        try:
            response = await async_client.chat.completions.create(
                model=OPENAI_MODEL,  # GPT-4o supports vision
                messages=[
                    {
                        "role": "system",
                        "content": IMAGE_ANALYSIS_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                }
                            },
                            {
                            "type": "text",
                            "text": """⚠️ ULTRA CRITICAL INSTRUCTION: Default assumption = THIS IMAGE IS EDITED. You MUST prove it's authentic with 100% certainty, otherwise mark as edited.

REMEMBER: Humans cannot detect tiny edits, but YOU CAN. Your job is to find edits that humans miss.

Perform an EXHAUSTIVE forensic analysis. You MUST find evidence of editing - even the tiniest edits leave traces that you can detect.

Examine EVERY aspect systematically with ULTRA sensitivity:

1. **Lighting Analysis (CRITICAL):**
   - Check if ALL objects have the same light direction and intensity
   - Look for shadow inconsistencies (wrong shadow direction, wrong shadow intensity)
   - Compare lighting on different parts - ANY difference = EDITING

2. **Color Analysis:**
   - Check white balance consistency across all regions
   - Look for color temperature shifts (warm vs cool areas)
   - Check saturation consistency
   - Any color mismatch = EDITING

3. **Sharpness & Quality Analysis:**
   - Compare sharpness levels - are some areas unnaturally sharp or blurry compared to their depth?
   - Check for compression quality variations (different JPEG quality in different areas)
   - Look for noise/grain pattern differences
   - Sharpness inconsistency = EDITING

4. **Edge Analysis:**
   - Are some edges "too perfect" or "too clean" compared to others?
   - Look for unnatural transitions between objects and background
   - Check for selection tool artifacts
   - Perfect edges = EDITING

5. **Pattern Analysis:**
   - Look for any repeated patterns (clone stamp usage)
   - Check for unnatural texture repetition
   - Repetitive patterns = EDITING

6. **For Vintage/Old Photos:**
   - Check if aging effects are consistent
   - Look for grain/noise inconsistencies
   - Verify lighting matches the photography technique of that era
   - Inconsistent aging = EDITING

7. **Depth of Field Analysis:**
   - Are objects at the same distance equally sharp?
   - Does sharpness match the focal plane?
   - Mismatch = EDITING

**ULTRA ZERO TOLERANCE - Default to EDITED**:
- Start with assumption: is_photoshopped=true, is_fake=true
- Only set to false if you can prove with 100% ABSOLUTE certainty the image is completely authentic
- If you find ANY of the above (even 0.01% difference), confirm is_photoshopped=true and is_fake=true
- For vintage/old photos: They are almost always edited/restored. Assume edited unless proven otherwise with 100% certainty
- REMEMBER: You are detecting edits that humans cannot see. Be hyper-sensitive. Any inconsistency = editing.

Return JSON:
{
  "is_ai_generated": true/false,
  "is_photoshopped": true/false,
  "is_fake": true/false,
  "confidence": 0.0-1.0,
  "message": "Your conclusion in Arabic",
  "detection_details": "EXACT details of what you found and WHERE (in Arabic) - be VERY specific"
}

All text must be in Arabic."""
                            }
                        ]
                    }
                ],
                temperature=0.0,
                max_tokens=800
            )
            
            answer = (response.choices[0].message.content or "").strip()
            
            # Check if the model refused to analyze
            if not answer or answer.lower() in [
                "i'm sorry, i can't assist with that.",
                "i'm sorry, i cannot assist with that.",
                "i can't assist with that",
                "i cannot assist with that",
                "sorry, i can't help with that",
                "i apologize, but i can't assist"
            ] or "can't assist" in answer.lower() or "cannot assist" in answer.lower() or "unable to" in answer.lower():
                print(f"⚠️ Model refused detailed analysis. Trying simpler approach...")
                
                # Try simpler prompt
                try:
                    simple_response = await async_client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an image analysis expert. Analyze images for technical authenticity only."
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{img_base64}"
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": """Analyze this image for digital editing or manipulation. Check for:
- Lighting inconsistencies
- Color inconsistencies  
- Sharpness variations
- Edge quality differences
- Any signs of Photoshop or editing software

Return JSON in this format:
{
  "is_ai_generated": false,
  "is_photoshopped": true/false,
  "is_fake": true/false,
  "confidence": 0.0-1.0,
  "message": "Result in Arabic",
  "detection_details": "Details in Arabic"
}"""
                                    }
                                ]
                            }
                        ],
                        temperature=0.1,
                        max_tokens=500
                    )
                    answer = (simple_response.choices[0].message.content or "").strip()
                    print(f"✅ Simpler prompt succeeded")
                except Exception as simple_error:
                    print(f"⚠️ Simpler prompt also failed: {simple_error}")
                    answer = None
            
            if not answer or "can't assist" in answer.lower() or "cannot assist" in answer.lower() or "unable to" in answer.lower():
                print(f"⚠️ Model refused to analyze the image. Response: {answer[:200] if answer else 'Empty'}")
                return {
                    "is_ai_generated": None,
                    "is_photoshopped": None,
                    "is_fake": None,
                    "message": "لا يمكن تحليل هذه الصورة. قد تحتوي على محتوى غير مدعوم من قبل النموذج أو قد يكون هناك قيود أمنية.",
                    "error": "Model refused to analyze"
                }
        
        except Exception as api_error:
            print(f"❌ API Error: {api_error}")
            return {
                "is_ai_generated": None,
                "is_photoshopped": None,
                "is_fake": None,
                "message": f"حدث خطأ تقني أثناء الاتصال بخدمة التحليل: {str(api_error)}",
                "error": str(api_error)
            }
        
        # Clean up JSON response
        if answer.startswith("```"):
            answer = answer.strip("` \n")
            if answer.lower().startswith("json"):
                answer = answer[4:].strip()
        
        # Extract JSON if wrapped
        json_match = re.search(r'\{[\s\S]*\}', answer)
        if json_match:
            answer = json_match.group(0)
        
        # Parse JSON
        try:
            parsed = json.loads(answer)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing error: {e}")
            print(f"📄 Response content: {answer[:500]}")
            # Try to extract information from the text response if it's not JSON
            if "ai" in answer.lower() or "artificial" in answer.lower() or "generated" in answer.lower():
                # Try to infer from response text
                is_ai_inferred = "ai" in answer.lower() and ("generated" in answer.lower() or "artificial" in answer.lower())
                is_edited_inferred = any(word in answer.lower() for word in ["edited", "photoshop", "manipulated", "fake", "modified"])
                
                parsed = {
                    "is_ai_generated": is_ai_inferred,
                    "is_photoshopped": is_edited_inferred,
                    "is_fake": is_edited_inferred or is_ai_inferred,
                    "confidence": 0.6,
                    "message": "تم تحليل الصورة لكن التنسيق لم يكن صحيحاً. النتيجة قد لا تكون دقيقة.",
                    "detection_details": ""
                }
            else:
                # Fallback response
                parsed = {
                    "is_ai_generated": None,
                    "is_photoshopped": None,
                    "is_fake": None,
                    "confidence": 0.5,
                    "message": "حدث خطأ أثناء تحليل الصورة. يرجى المحاولة مرة أخرى.",
                    "detection_details": ""
                }
        
        # ============================================
        # STEP 2: Combine Forensic + OpenAI Vision Results
        # ============================================
        print("🔗 Combining forensic and AI vision results...")
        
        # استخراج المعلومات من OpenAI Vision
        ai_vision_is_ai = parsed.get("is_ai_generated", False)
        ai_vision_is_photoshopped = parsed.get("is_photoshopped", False)
        ai_vision_is_fake = parsed.get("is_fake", False)
        ai_vision_confidence = parsed.get("confidence", parsed.get("ai_confidence", 0.5))
        ai_vision_message = parsed.get("message", "")
        ai_vision_detection_details = parsed.get("detection_details", "")
        
        # For vintage/old photos: be more aggressive in detection
        # Check if it's a vintage/old photo based on message or details
        is_vintage_photo = any(word in ai_vision_message.lower() or word in ai_vision_detection_details.lower() 
                              for word in ['vintage', 'old', 'قديم', 'عتيق', 'sepia', 'grain', 'حبيبات'])
        
        # ============================================
        # FINAL DECISION: Combine Both Analyses
        # ============================================
        # Use forensic analysis as primary indicator (more reliable for technical edits)
        # Use AI vision for visual analysis and AI detection
        
        # ULTRA STRICT POLICY: If ANY forensic indicator flags it, mark as edited
        # Even the smallest edit leaves traces - trust the forensic analysis
        
        if forensic_is_edited:
            # ANY forensic detection = edited (ultra strict)
            is_photoshopped = True
            is_fake = True
            # Boost confidence if multiple indicators or AI vision also detected
            if ai_vision_is_photoshopped or ai_vision_is_fake:
                combined_confidence = min(0.98, max(forensic_confidence, ai_vision_confidence) + 0.1)
            else:
                combined_confidence = max(forensic_confidence, 0.65)  # Minimum 65% if forensic detected
        elif ai_vision_is_photoshopped or ai_vision_is_fake:
            # AI vision detected something - trust it
            is_photoshopped = ai_vision_is_photoshopped
            is_fake = ai_vision_is_fake
            combined_confidence = max(ai_vision_confidence, 0.7)  # Minimum 70% if AI vision detected
        else:
            # Neither detected strongly, but check confidence levels
            # VERY STRICT: Low confidence = assume edited
            if ai_vision_confidence < 0.90 or (is_vintage_photo and ai_vision_confidence < 0.95):
                # Low confidence = assume edited (ultra strict policy)
                is_photoshopped = True
                is_fake = True
                combined_confidence = 0.7  # High suspicion even without clear detection
            else:
                # Very high confidence authentic (only if >90%)
                is_photoshopped = False
                is_fake = False
                combined_confidence = ai_vision_confidence
        
        # AI detection: use AI vision result (better at detecting AI-generated images)
        is_ai = ai_vision_is_ai
        
        # Build comprehensive message with both analyses
        message_parts = []
        
        if is_fake:
            if is_ai:
                message_parts.append("⚠️ الصورة مصنوعة بالذكاء الاصطناعي")
            elif is_photoshopped:
                message_parts.append("⚠️ الصورة معدلة أو مزورة باستخدام برامج التعديل مثل Photoshop")
            else:
                message_parts.append("⚠️ الصورة مزورة أو معدلة")
            
            # Add forensic detection details
            if forensic_details:
                message_parts.append("\n🔬 تحليل فني متقدم:")
                for detail in forensic_details:
                    message_parts.append(f"   • {detail}")
            
            # Add AI vision detection details
            if ai_vision_detection_details and ai_vision_detection_details not in ' '.join(forensic_details):
                message_parts.append("\n👁️ تحليل بصري:")
                message_parts.append(f"   • {ai_vision_detection_details}")
            
            # Add confidence information
            message_parts.append(f"\n📊 مستوى الثقة: {combined_confidence:.0%}")
            if forensic_is_edited:
                message_parts.append(f"   • التحليل الفني: {forensic_results.get('suspicious_count', 0)}/{forensic_results.get('total_checks', 0)} مؤشرات مشبوهة")
        else:
            message_parts.append("✅ الصورة حقيقية وأصلية")
            message_parts.append(f"\n📊 مستوى الثقة: {combined_confidence:.0%}")
            if forensic_is_edited:
                # Even if we marked as authentic, mention forensic findings
                message_parts.append("\n⚠️ ملاحظة: التحليل الفني وجد بعض المؤشرات، لكن الصورة تبدو أصلية بشكل عام")
        
        message = "\n".join(message_parts)
        
        # If no message was built, use AI vision message
        if not message or message.strip() == "":
            message = ai_vision_message if ai_vision_message else "تم تحليل الصورة"
        
        print(f"✅ Final Results:")
        print(f"   - Is AI Generated: {is_ai}")
        print(f"   - Is Photoshopped: {is_photoshopped}")
        print(f"   - Is Fake: {is_fake}")
        print(f"   - Combined Confidence: {combined_confidence:.2f}")
        
        return {
            "is_ai_generated": is_ai,
            "is_photoshopped": is_photoshopped,
            "is_fake": is_fake,
            "message": message.strip(),
            "confidence": combined_confidence,
            "forensic_analysis": {
                "detected": forensic_is_edited,
                "confidence": forensic_confidence,
                "indicators": forensic_results.get('suspicious_count', 0)
            }
        }
        
    except Exception as e:
        print(f"❌ Error in image analysis: {e}")
        print(traceback.format_exc())
        return {
            "is_ai_generated": None,
            "is_photoshopped": None,
            "is_fake": None,
            "message": "حدث خطأ أثناء تحليل الصورة. يرجى المحاولة مرة أخرى.",
            "error": str(e)
        }

