import os, traceback, requests, json
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

load_dotenv()

def translate_date_references(text: str) -> str:
    """
    إرجاع النص كما هو دون تغيير المراجع الزمنية
    لتجنب تغيير معنى البحث عند استخدام كلمات مثل "اليوم"
    """
    # إرجاع النص كما هو دون أي تعديل
    return text

def generate_professional_news_article_from_analysis(claim_text: str, case: str, talk: str, sources: List[Dict], lang: str = "ar") -> str:
    """
    Generate a professional news article based on fact-check analysis and sources
    Uses the analysis (talk) and sources to create a balanced, journalistic piece
    """
    
    # Prepare sources context
    if not sources:
        sources_context = "No specific sources available for this investigation."
    else:
        sources_context = "\n\n".join([
            f"**Source {i+1}:**\n"
            f"Title: {source.get('title', 'N/A')}\n"
            f"URL: {source.get('url', 'N/A')}\n"
            f"Snippet: {source.get('snippet', 'N/A')}"
            for i, source in enumerate(sources[:5])  # Limit to 5 sources
        ])
    
    # Determine the prompt based on the case
    if case.lower() in {"حقيقي", "true", "vrai", "verdadero", "pravda"}:
        # TRUE case - Use the specific prompt for confirmed news
        FACT_CHECK_NEWS_PROMPT = f"""
You are a senior international news agency journalist writing in {lang.upper()} language.

Write a professional news article in the style of international news agencies based on the provided headline and analysis.

**MANDATORY REQUIREMENT:**
- You MUST write about the headline and analysis provided in the user message
- Extract ALL facts and details from the Fact-check Analysis provided by the user
- Do NOT create unrelated news - only use information from the provided analysis
- The headline is: "{claim_text}"
- Use the analysis to write the news article about this specific headline

**CRITICAL INSTRUCTIONS FOR TRUE NEWS:**
- You MUST write about the headline and analysis provided in the user message
- Start DIRECTLY with the news event/statement itself (e.g., "أرسلت [الدولة/الهيئة]..." or "[Entity] sent...")
- Write as a DIRECT NEWS REPORT, NOT as analysis or verification
- First paragraph: Report the main event naturally with details (who, what, when, where, participants, etc.) based on the provided analysis
- Second paragraph: Discuss the topics, themes, or issues that were addressed/covered, using details from the analysis
- Third paragraph: Provide additional context about sessions, discussions, or highlights from the analysis
- AVOID any mention of "verification", "fact-check", "results", "تحقق", "نتائج التحقق" anywhere in the article
- Write naturally and smoothly as if reporting events as they happened
- Mention official sources and statements naturally from the analysis provided

**STRUCTURE TEMPLATE FOR TRUE NEWS:**
1. **Opening Paragraph**: Start directly with the event from the headline (e.g., "أرسلت [الدولة]..." or "[Entity] sent...") with key details from the analysis
2. **Second Paragraph**: Discuss the details, quantities, beneficiaries, or specific information from the analysis
3. **Third Paragraph**: Additional context about significance, continuation, or broader implications from the analysis

**REQUIREMENTS:**
- Language: {lang.upper()} entirely
- Style: Professional news reporting (like AFP, Reuters, AP)
- Tone: Neutral, factual, authoritative
- Structure: Exactly 3 paragraphs following the template above
- Length: 150-250 words
- Must follow the exact structure template
- Use professional journalistic language
- NO mention of verification or fact-checking
"""
    else:
        # UNCERTAIN case - Use the specific prompt for unconfirmed news
        FACT_CHECK_NEWS_PROMPT = f"""
        You are a professional journalist at an international news agency writing in {lang.upper()}.

        Write a polished, factual, and concise news report that follows the official style of agencies such as QNA, WAM, and SPA.

        **STYLE TO FOLLOW (VERY IMPORTANT):**
        - Begin directly with the main event using a strong news verb (e.g., "أرسلت"، "أعلنت"، "اختتمت"، "وقّعت").
        - First paragraph: summarize the event (who, what, where, why) in one flowing sentence.
        - Second paragraph: include factual details — quantities, participating entities, dates, beneficiaries, or program names.
        - Third paragraph: provide broader meaning or context — humanitarian, diplomatic, developmental, or cooperative significance.
        - Keep tone neutral, official, and humanitarian in tone.
        - Avoid any mention of verification, analysis, or fact-checking.
        - Use formal Modern Standard Arabic (MSA).

        **TARGET STYLE EXAMPLE:**
        أرسلت دولة قطر مساعدات إغاثية وإنسانية عاجلة إلى مدينة الدبة في الولاية الشمالية بجمهورية السودان، في إطار التزامها الثابت بدعم الشعب السوداني، لا سيما في ظل الظروف الإنسانية الصعبة التي يعيشها المدنيون من نقص حاد في الغذاء واحتياج متزايد لمستلزمات الإيواء والمواد الأساسية.

        وتشمل المساعدات نحو 3 آلاف سلة غذائية و1650 خيمة إيواء ومستلزمات أخرى، مقدمة من صندوق قطر للتنمية وقطر الخيرية، لدعم النازحين من مدينة الفاشر والمناطق المجاورة، ومن المقرر أن يستفيد منها أكثر من 50 ألف شخص، فضلا عن إنشاء مخيم خاص بالمساعدات القطرية تحت مسمى قطر الخير.

        ويعد هذا الدعم امتدادا لجهود دولة قطر المتواصلة في الوقوف إلى جانب الشعب السوداني الشقيق وتخفيف معاناته جراء النزاع المسلح، كما يجسد دورها الريادي في تعزيز الاستجابة الإنسانية وبناء جسور التضامن مع الشعوب المتضررة في مختلف أنحاء العالم.

        **REQUIREMENTS:**
        - Language: {lang.upper()} only
        - Length: 150–220 words
        - Structure: exactly 3 paragraphs (intro, details, context)
        - Tone: factual, diplomatic, humanitarian
        - No analysis, no opinion, no “fact-checking” terms
        """

    # Create the user message
    if case.lower() in {"حقيقي", "true", "vrai", "verdadero", "pravda"}:
        user_message = f"""
**PROVIDED DATA:**
Headline: {claim_text}
Fact-check Analysis: {talk}

**AVAILABLE SOURCES:**
{sources_context}

**EXAMPLE FORMAT FOR TRUE NEWS (ARABIC):**
أرسلت دولة قطر مساعدات إغاثية وإنسانية عاجلة إلى مدينة الدبة في الولاية الشمالية بجمهورية السودان، في إطار التزامها الثابت بدعم الشعب السوداني، لا سيما في ظل الظروف الإنسانية الصعبة التي يعيشها المدنيون من نقص حاد في الغذاء واحتياج متزايد لمستلزمات الإيواء والمواد الأساسية.

وتشمل المساعدات نحو 3 آلاف سلة غذائية و1650 خيمة إيواء ومستلزمات أخرى، مقدمة من صندوق قطر للتنمية وقطر الخيرية، لدعم النازحين من مدينة الفاشر والمناطق المجاورة، ومن المقرر أن يستفيد منها أكثر من 50 ألف شخص، فضلا عن إنشاء مخيم خاص بالمساعدات القطرية تحت مسمى قطر الخير.

ويعد هذا الدعم امتدادا لجهود دولة قطر المتواصلة في الوقوف إلى جانب الشعب السوداني الشقيق وتخفيف معاناته جراء النزاع المسلح، كما يجسد دورها الريادي في تعزيز الاستجابة الإنسانية وبناء جسور التضامن مع الشعوب المتضررة في مختلف أنحاء العالم.

**CRITICAL REQUIREMENTS:**
- The news article MUST be about the headline provided: "{claim_text}"
- You MUST use ALL the information from the Fact-check Analysis provided below
- The Fact-check Analysis contains the actual facts and details - extract them and write the news article based on them
- Do NOT invent or create unrelated news - only use information from the analysis
- Follow the exact structure shown in the example above
- First paragraph: Start directly with the event from the headline (who, what, when, where, participants) using details from the analysis
- Second paragraph: Discuss the details, quantities, beneficiaries, or specific information from the analysis
- Third paragraph: Additional context about significance, continuation, or broader implications from the analysis
- Write as a direct news report, NOT as verification or fact-check
- AVOID any mention of "verification", "fact-check", "results", "تحقق", "نتائج التحقق"
- Use the analysis data to inform your reporting, but present it as breaking news
- The article MUST be relevant to the headline: "{claim_text}"
- Adapt the structure to the target language ({lang.upper()}) while maintaining the same meaning
"""
    else:
        user_message = f"""
**PROVIDED DATA:**
Headline: {claim_text}
Fact-check Analysis: {talk}

**AVAILABLE SOURCES:**
{sources_context}

**EXAMPLE FORMAT FOR UNCERTAIN NEWS (ARABIC):**
تداولت منصات التواصل الاجتماعي مزاعم تفيد بأن [الادعاء]، غير أن نتائج التحقق أظهرت أن هذا الادعاء لا يمكن تأكيده.

وبحسب المعلومات المتاحة، [شرح المعلومات المتاحة والسبب في عدم التأكيد]. [معلومات تاريخية أو سياق إذا كان متاحاً].

وبناءً على ذلك، يتبيّن أن الادعاء المتداول يفتقر إلى أي أساس من الأدلة الموثوقة، ولا توجد مصادر تدعم صحته.

**INSTRUCTIONS:**
- Follow the exact structure shown in the example above
- Use the analysis data to explain why the claim cannot be confirmed
- Include historical context or relevant background when available
- End with the conclusion that the claim lacks reliable evidence
- Adapt the structure to the target language ({lang.upper()}) while maintaining the same meaning
"""

    try:
        print("📰 Generating news article...")
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": FACT_CHECK_NEWS_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,  # Very low temperature for factual, measured content
            max_tokens=400,   # Allow enough tokens for 150-250 words
            top_p=0.9,        # Focus on most likely responses
            frequency_penalty=0.1,  # Slight penalty to avoid repetition
            presence_penalty=0.1    # Encourage diverse vocabulary
        )
        
        article = response.choices[0].message.content.strip()
        print("✅ News article generated successfully")
        return article
        
    except Exception as e:
        print(f"❌ Error generating news article: {e}")
        error_messages = {
            "ar": "عذراً، حدث خطأ أثناء كتابة المقال الإخباري. يرجى المحاولة مرة أخرى.",
            "en": "Sorry, an error occurred while writing the news article. Please try again.",
            "fr": "Désolé, une erreur s'est produite lors de la rédaction de l'article de presse. Veuillez réessayer.",
            "es": "Lo siento, ocurrió un error al escribir el artículo de noticias. Por favor, inténtalo de nuevo.",
        }
        return error_messages.get(lang, error_messages["en"])

def generate_analytical_news_article(headline: str, analysis: str, lang: str = "ar") -> str:
    """
    Generate a professional analytical news article using international news agency style
    Based on provided headline and fact-check analysis
    """
    
    # Professional analytical journalism prompt
    ANALYTICAL_NEWS_PROMPT = f"""
You are a senior editor-in-chief at a major international news agency (like Reuters or AFP) with 20+ years of experience in analytical journalism and fact-checking.

**REQUIRED EXPERTISE:**
1. **Editor-in-Chief**: Oversee editorial standards and journalistic integrity
2. **Analytical Journalist**: Provide deep and objective analysis
3. **Fact-Checking Specialist**: Present verified information clearly
4. **Breaking News Editor**: Handle developing stories with incomplete information
5. **Geopolitical Analyst**: Provide geopolitical and military context
6. **Public Interest Journalist**: Focus on what the public needs to know
7. **Crisis Communication Specialist**: Handle sensitive and unconfirmed information

**ANALYTICAL NEWS STANDARDS:**
- **Accuracy**: Build the article based on reliable information and sources
- **Objectivity**: Present information clearly and objectively
- **Transparency**: Clearly state what was found and what remains unclear
- **Context**: Provide background and historical perspective
- **Balance**: Include all relevant viewpoints fairly
- **Responsibility**: Consider public impact of reporting
- **Clarity**: Write for general audience understanding
- **Completeness**: Cover all important aspects of the story

**CRITICAL WRITING APPROACH:**

**FOR UNCONFIRMED NEWS:**
Write a professional news article in the style of international agencies.
Begin by reporting what is being circulated or claimed in media/social platforms in an objective manner such as: "Social media platforms circulated claims stating that..." or "Reports spread claiming that...", then report the actual situation: no evidence found, unconfirmed, or refuted.
Write as DIRECT NEWS REPORTING, NOT as a fact-check or verification result.
AVOID mentioning "verification" or "fact-check" anywhere in the article.

**FOR CONFIRMED NEWS:**
Write a professional news article in the style of international agencies.
Begin the news with the main statement or event itself, NOT with phrases like "verification results confirmed" or "analysis shows".
Present the information as breaking news or a news report, NOT as analysis or verification.
Write naturally as if reporting events as they happened.
AVOID any mention of "verification", "fact-check", "analysis", "investigation", or "confirmation".

**PROFESSIONAL TERMINOLOGY REQUIRED:**
- "The ministry announced..."
- "The authority confirmed..."
- "According to an official statement..."
- "This represents a step towards..."
- "The development comes as..."
- "This coincides with..."
- "Sources indicate that..."
- "The move signals..."
- "This follows..."
- "The announcement marks..."

**ARTICLE STRUCTURE:**
1. **Opening Sentence**: Strong and neutral journalistic sentence that places the reader in the atmosphere of the event
2. **Second Paragraph**: Provide key information and context in professional language
3. **Middle Paragraphs**: Expand with logical geopolitical or military context
4. **Concluding Paragraph**: Reflections or broader questions related to the event without taking a position

**LANGUAGE POLICY:**
- Write ENTIRELY in {lang.upper()} language
- Use professional journalistic terminology
- Maintain consistency in terminology
- Adapt cultural context appropriately
- Use formal, respectful language

**RESPONSE FORMAT:**
Write a professional news article (150-250 words) that reports the story directly.
Build the article on the information provided to inform readers.
Present what is known and what remains unclear in a natural news reporting style.

**PROVIDED DATA:**
Headline: {headline}
News Information: {analysis}

**REQUIREMENTS:**
- Language: {lang.upper()} entirely
- Style: Professional news reporting (like AFP, Reuters, AP)
- Tone: Objective, transparent, informative
- Structure: News article format with structured paragraphs
"""

    try:
        print("📰 Generating analytical news article...")
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": ANALYTICAL_NEWS_PROMPT}
            ],
            temperature=0.1,  # Very low temperature for factual, measured content
            max_tokens=500,   # Allow enough tokens for 150-250 words
            top_p=0.9,        # Focus on most likely responses
            frequency_penalty=0.1,  # Slight penalty to avoid repetition
            presence_penalty=0.1    # Encourage diverse vocabulary
        )
        
        article = response.choices[0].message.content.strip()
        print("✅ Analytical news article generated successfully")
        return article
        
    except Exception as e:
        print(f"❌ Error generating analytical news article: {e}")
        error_messages = {
            "ar": "عذراً، حدث خطأ أثناء كتابة المقال التحليلي. يرجى المحاولة مرة أخرى.",
            "en": "Sorry, an error occurred while writing the analytical article. Please try again.",
            "fr": "Désolé, une erreur s'est produite lors de la rédaction de l'article analytique. Veuillez réessayer.",
            "es": "Lo siento, ocurrió un error al escribir el artículo analítico. Por favor, inténtalo de nuevo.",
        }
        return error_messages.get(lang, error_messages["en"])

def generate_x_tweet(claim_text: str, case: str, talk: str, sources: List[Dict], lang: str = "ar") -> str:
    """
    Generate a professional X (Twitter) tweet based on fact-check results
    Optimized for X platform with proper formatting and engagement
    """
    
    # X/Twitter specific prompt
    X_TWEET_PROMPT = f"""
You are a professional social media journalist and X (Twitter) content creator with expertise in:

**X PLATFORM EXPERTISE:**
1. **Social Media Journalist**: Create engaging, accurate news content for X
2. **Viral Content Creator**: Understand what drives engagement on X
3. **Fact-Checking Specialist**: Present verified information clearly
4. **Crisis Communication**: Handle sensitive information responsibly
5. **Community Manager**: Engage audiences while maintaining credibility
6. **Digital Storyteller**: Tell compelling stories in limited characters
7. **Breaking News Reporter**: Handle urgent, time-sensitive information
8. **Public Interest Communicator**: Serve public interest on social media

**X PLATFORM REQUIREMENTS:**
- Maximum 280 characters (strict limit)
- Use hashtags strategically (2-3 relevant hashtags)
- Include emojis appropriately for engagement
- Write for mobile-first audience
- Use clear, concise language
- Include call-to-action when appropriate
- Maintain professional credibility
- Respect X community guidelines

**TWEET STRUCTURE FOR FACT-CHECKING:**
1. **Hook**: Attention-grabbing opening
2. **Fact**: Clear statement of the fact-check result
3. **Context**: Brief explanation or key detail
4. **Hashtags**: Relevant, trending hashtags
5. **Emojis**: Strategic use for engagement and clarity

**LANGUAGE POLICY:**
- Write ENTIRELY in {lang.upper()} language
- Use professional but engaging tone
- Adapt to social media communication style
- Maintain journalistic credibility
- Use appropriate emojis for the language/culture

**ENGAGEMENT STRATEGY:**
- Start with compelling hook
- Use numbers/statistics when available
- Include relevant hashtags
- Use emojis strategically
- End with clear conclusion or call-to-action
- Maintain professional credibility

**RESPONSE FORMAT:**
Generate a single, professional X tweet (max 280 characters) that:
- Clearly states the fact-check result
- Engages the audience appropriately
- Maintains journalistic credibility
- Uses relevant hashtags and emojis
- Respects X platform guidelines
"""

    # Prepare context based on fact-check result (only True or Uncertain)
    if case.lower() in {"حقيقي", "true", "vrai", "verdadero", "pravda"}:
        result_emoji = "✅"
        result_text = "حقيقي" if lang == "ar" else "TRUE"
        tone = "confirming"
    else:  # uncertain
        result_emoji = "⚠️"
        result_text = "غير مؤكد" if lang == "ar" else "UNCERTAIN"
        tone = "uncertain"

    # Create the user message
    user_message = f"""
**FACT-CHECK RESULT:**
Claim: {claim_text}
Result: {case} ({result_text})
Analysis: {talk}

**SOURCES:**
{len(sources)} sources available

**INSTRUCTIONS:**
Create a professional X tweet that:
1. Clearly communicates the fact-check result
2. Engages the audience appropriately
3. Uses relevant hashtags and emojis
4. Maintains journalistic credibility
5. Respects X platform guidelines
6. Stays within 280 character limit

**TONE:** {tone}
**LANGUAGE:** {lang.upper()}
**PLATFORM:** X (Twitter)
**CHARACTER LIMIT:** 280 characters maximum
"""

    try:
        print("🐦 Generating X tweet...")
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": X_TWEET_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,  # Balanced creativity and accuracy
            max_tokens=150,   # Enough for tweet + some buffer
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.1
        )
        
        tweet = response.choices[0].message.content.strip()
        
        # Ensure tweet is within character limit
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        
        print("✅ X tweet generated successfully")
        return tweet
        
    except Exception as e:
        print(f"❌ Error generating X tweet: {e}")
        error_messages = {
            "ar": "⚠️ حدث خطأ أثناء إنشاء التغريدة. يرجى المحاولة مرة أخرى.",
            "en": "⚠️ An error occurred while generating the tweet. Please try again.",
            "fr": "⚠️ Une erreur s'est produite lors de la génération du tweet. Veuillez réessayer.",
            "es": "⚠️ Ocurrió un error al generar el tweet. Por favor, inténtalo de nuevo.",
        }
        return error_messages.get(lang, error_messages["en"])

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
SERPAPI_HL = os.getenv("SERPAPI_HL", "ar")
SERPAPI_GL = os.getenv("SERPAPI_GL", "")
NEWS_AGENCIES = [d.strip() for d in os.getenv("NEWS_AGENCIES", "aljazeera.net,una-oic.org,bbc.com").split(",") if d.strip()]

if not SERPAPI_KEY or not OPENAI_API_KEY:
    raise RuntimeError("⚠️ رجاءً ضع SERPAPI_KEY و OPENAI_API_KEY في .env")

client = OpenAI(api_key=OPENAI_API_KEY)

def _lang_hint_from_claim(text: str) -> str:
    try:
        resp = client.chat.completions.create(
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

def is_news_content(text: str) -> tuple[bool, str]:
    """
    Validate if the input text is news/journalistic content SPECIFICALLY about Gaza, Palestine, or OIC.
    Returns (is_valid, reason) tuple.
    If not news-related OR not about Gaza/Palestine/OIC, returns (False, reason in Arabic).
    """
    try:
        validation_prompt = """You are a news content validator for a SPECIALIZED FACT-CHECKING API focused ONLY on Gaza, Palestine, and the Organization of Islamic Cooperation (OIC).

🎯 **STRICT SCOPE LIMITATION:**
This API ONLY accepts news claims/statements that are DIRECTLY related to:
1. **Gaza** (غزة) - Any news, events, statements, or claims about Gaza Strip
2. **Palestine** (فلسطين) - Any news, events, statements, or claims about Palestine, Palestinian territories, Palestinian people, Palestinian-Israeli conflict, Palestinian Authority, Palestinian government, Palestinian cities (Ramallah, Nablus, Hebron, Bethlehem, etc.), Palestinian refugees, Palestinian cause
3. **Organization of Islamic Cooperation (OIC)** (منظمة التعاون الإسلامي) - Any news, events, statements, or claims about OIC, its member states' actions related to Palestine/Gaza, OIC summits, OIC statements, OIC resolutions, OIC humanitarian aid

⚠️ KEY DISTINCTION: Accept STATEMENTS/CLAIMS about events, NOT personal questions asking for opinions or information.

✅ ACCEPT (News Claims/Statements ABOUT GAZA/PALESTINE/OIC ONLY):
- STATEMENTS about Gaza events (e.g., "قصف إسرائيلي على غزة" = YES)
- STATEMENTS about Palestine events (e.g., "اجتماع في رام الله" = YES)
- STATEMENTS about Palestinian-Israeli conflict (e.g., "اشتباكات في الضفة الغربية" = YES)
- STATEMENTS about OIC actions/resolutions regarding Palestine/Gaza (e.g., "إعلان منظمة التعاون الإسلامي" = YES)
- CLAIMS about Palestinian Authority, Palestinian government, Palestinian cities
- NEWS HEADLINES about Gaza, Palestine, or OIC-related Palestine news
- Declarative sentences about events, people, places IN Gaza, Palestine, or related to OIC-Palestine
- ANY CLAIM that can be fact-checked AND is about Gaza/Palestine/OIC-Palestine

❌ REJECT (Content OUTSIDE Gaza/Palestine/OIC scope):
- ANY claim NOT about Gaza, Palestine, or OIC-Palestine (e.g., "زلزال في تركيا" = NO - wrong location)
- News about other countries unless it's OIC action related to Palestine/Gaza
- General world news not related to Palestine/Gaza/OIC
- Sports news unless it's about Palestinian teams or Gaza
- Celebrity news unless it's about Palestinian celebrities or Gaza-related
- QUESTIONS asking for opinions (e.g., "ما رأيك في الوضع؟" = NO)
- QUESTIONS asking for information (e.g., "كيف الطقس اليوم؟" = NO)
- How-to guides, recipes (e.g., "طريقة عمل المحشي" = NO)
- Casual conversations, greetings ("مرحبا، كيف حالك؟" = NO)
- Educational tutorials ("كيف أتعلم البرمجة" = NO)
- Personal questions without specific claim
- Philosophical discussions without Gaza/Palestine/OIC news context
- General knowledge questions
- Requests for advice or tips

🔑 THE KEY TESTS:
1. Is it a STATEMENT/CLAIM about something that happened or will happen?
2. Is it DIRECTLY related to Gaza, Palestine, or OIC-Palestine actions?
- If YES to both → ACCEPT (it can be fact-checked)
- If NO to either → REJECT (not in scope)

EXAMPLES - ACCEPT ✅:
- "قصف إسرائيلي على غزة" → YES (Gaza-related claim)
- "اجتماع في رام الله" → YES (Palestine-related claim)
- "منظمة التعاون الإسلامي تدين العدوان على غزة" → YES (OIC-Palestine related)
- "استشهاد فلسطيني في الضفة الغربية" → YES (Palestine-related claim)
- "مساعدات إنسانية إلى غزة" → YES (Gaza-related claim)
- "قرار منظمة التعاون الإسلامي بشأن فلسطين" → YES (OIC-Palestine related)
- "مظاهرات نصرة لغزة" → YES (Gaza-related claim)

EXAMPLES - REJECT ❌:
- "زلزال يضرب تركيا" → NO (not Gaza/Palestine/OIC-related)
- "مقتل ترامب" → NO (not Gaza/Palestine/OIC-related)
- "إنشاء قطار يربط الدوحة بالرياض" → NO (not Gaza/Palestine/OIC-related)
- "حريق في مبنى برج خليفة" → NO (not Gaza/Palestine/OIC-related)
- "فوز الهلال بالدوري" → NO (not Gaza/Palestine/OIC-related)
- "ما رأيك في الطقس اليوم؟" → NO (question asking for opinion)
- "كيف الطقس اليوم؟" → NO (question asking for information)
- "هل تعتقد أن الاقتصاد سيتحسن؟" → NO (opinion question, not Gaza/Palestine/OIC-specific)
- "طريقة عمل المحشي" → NO (how-to/recipe)
- "كيف أتعلم البرمجة" → NO (educational question)
- "مرحبا، كيف حالك؟" → NO (casual greeting)
- "ما هي أفضل طريقة للسفر؟" → NO (advice question)

⚠️ CRITICAL: 
1. A CLAIM/STATEMENT can be fact-checked. A QUESTION asking for opinion/info cannot.
2. The claim MUST be about Gaza, Palestine, or OIC-Palestine actions. Other topics are OUT OF SCOPE.

Respond with ONLY one word: "yes" if it's a news claim/statement ABOUT GAZA/PALESTINE/OIC, "no" if it's not.
Then on a new line, provide a CLEAR and DETAILED explanation in Arabic explaining why the content is rejected.

**IMPORTANT FOR REJECTION MESSAGES:**
- If the content is OUTSIDE Gaza/Palestine/OIC scope: Explain clearly that this API is specialized ONLY for Gaza, Palestine, and OIC-related news. Mention what the content is about and why it doesn't fit.
- If it's a question: Explain that only news claims/statements are accepted, not questions.
- Be specific and helpful - tell the user exactly what is wrong and what they should send instead.

Example rejection messages:
- "هذا الخبر يتعلق بتركيا، بينما هذا النظام متخصص فقط في الأخبار المتعلقة بغزة وفلسطين ومنظمة التعاون الإسلامي. يرجى إرسال خبر متعلق بهذا السياق فقط."
- "النص المقدم سؤال وليس خبراً إخبارياً. يرجى إرسال خبر أو ادعاء متعلق بغزة أو فلسطين أو منظمة التعاون الإسلامي."
- "هذا المحتوى لا يتعلق بغزة أو فلسطين أو منظمة التعاون الإسلامي. يرجى إرسال خبر متعلق بهذا السياق المتخصص فقط."""

        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": validation_prompt},
                {"role": "user", "content": text.strip()},
            ],
            temperature=0.1,
            max_tokens=200  # زيادة الـ tokens للسماح بشرح أوضح
        )
        
        answer = (resp.choices[0].message.content or "").strip().lower()
        lines = answer.split('\n', 1)
        is_valid = lines[0].strip() == "yes"
        reason = lines[1].strip() if len(lines) > 1 else ""
        
        if not is_valid:
            # إذا لم يكن هناك سبب واضح، نعطي رسالة توضيحية مفصلة
            if not reason or len(reason.strip()) < 20:
                reason = f"""⚠️ هذا النظام متخصص فقط في التحقق من الأخبار المتعلقة بـ:
• غزة (قطاع غزة)
• فلسطين (الأراضي الفلسطينية، الشعب الفلسطيني، السلطة الفلسطينية)
• منظمة التعاون الإسلامي (خاصة فيما يتعلق بفلسطين وغزة)

النص المقدم لا يتعلق بهذا السياق المتخصص. يرجى إرسال خبر أو ادعاء متعلق بغزة أو فلسطين أو منظمة التعاون الإسلامي فقط."""
            return (False, reason)
        return (True, "")
        
    except Exception as e:
        # On error, allow through but log it
        print(f"⚠️ Error validating news content: {e}")
        return (True, "")  # Allow through on error to avoid blocking valid requests

def _fetch_serp(query: str, extra: Dict | None = None, num: int = 10) -> List[Dict]:
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
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
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
        print("❌ Error fetching from SerpAPI:", e)
        return []

FACT_PROMPT_SYSTEM = (
    "You are a rigorous fact-checking assistant. Use ONLY the sources provided below.\n"
    "- You can ONLY return TWO possible verdicts: True OR Uncertain.\n"
    "- If the claim is supported by credible sources with clear evidence → verdict: True\n"
    "- If evidence is insufficient, conflicting, unclear, or off-topic → verdict: Uncertain\n"
    "- IMPORTANT: There is NO 'False' option. If you cannot confirm something as True, mark it as Uncertain.\n"
    "- Prefer official catalogs and reputable agencies over blogs or social posts.\n"
    "- Match the claim's date/place/magnitude when relevant; do not infer beyond the given sources.\n\n"

    "LANGUAGE POLICY:\n"
    "- You MUST respond **entirely** in the language specified by LANG_HINT.\n"
    "- Do NOT switch to another language or translate.\n"
    "- Examples:\n"
    "   • If LANG_HINT = 'fr' → respond fully in French.\n"
    "   • If LANG_HINT = 'ar' → respond fully in Arabic.\n"
    "   • If LANG_HINT = 'en' → respond fully in English.\n"
    "   • If LANG_HINT = 'es' → respond fully in Spanish.\n"
    "   • If LANG_HINT = 'cs' → respond fully in Czech.\n\n"

    "FORMAT RULES:\n"
    "• You MUST write all free-text fields strictly in LANG_HINT language.\n"
    "• JSON keys must remain EXACTLY as: \"الحالة\", \"talk\", \"sources\" (do not translate keys).\n"
    "• The value of \"الحالة\" must be ONLY one of these two options (localized):\n"
    "   - Arabic: حقيقي / غير مؤكد (ONLY these two options)\n"
    "   - English: True / Uncertain (ONLY these two options)\n"
    "   - French: Vrai / Incertain (ONLY these two options)\n"
    "   - Spanish: Verdadero / Incierto (ONLY these two options)\n"
    "   - Czech: Pravda / Nejisté (ONLY these two options)\n"
    "• NEVER use: False, Faux, Falso, Nepravda, كاذب - these are NOT valid options!\n"

    "RESPONSE FORMAT (JSON ONLY — no extra text):\n"
    "{\n"
    '  \"الحالة\": \"<Localized verdict: True OR Uncertain ONLY>\",\n'
    '  \"talk\": \"<Explanation paragraph ~350 words in LANG_HINT>\",\n'
    '  \"sources\": [ {\"title\": \"<title>\", \"url\": \"<url>\"}, ... ]\n'
    "}\n\n"

    "SOURCES RULES:\n"
    "1) Include ONLY sources that DIRECTLY support or relate to the claim.\n"
    "2) Do NOT include unrelated sources, even if they mention similar topics.\n"
    "3) If a source title/content is NOT relevant to the claim → DO NOT include it.\n"
    "4) Maximum 10 sources (prioritize the most relevant and credible ones).\n"
    "5) Remove duplicate URLs - include each source only once.\n"
    "6) Each source must have both title AND url.\n\n"

    "FINAL RULES:\n"
    "1) Output STRICTLY valid JSON (UTF-8). No extra commentary before or after.\n"
    "2) If the claim is Uncertain → keep 'sources' as an empty array [].\n"
    "3) If the claim is True → include ONLY RELEVANT confirming sources (max 10).\n"
    "4) Do not fabricate URLs or titles; use only provided sources.\n"
    "5) REMEMBER: You can ONLY return True or Uncertain. There is NO False option.\n"
    "6) ONLY include sources that are DIRECTLY related to the specific claim.\n"
)


def check_fact_simple(claim_text: str, k_sources: int = 5, generate_news: bool = False, preserve_sources: bool = False, generate_tweet: bool = False) -> dict:
    try:
        # ترجمة المراجع الزمنية في النص
        processed_claim = translate_date_references(claim_text)
        print(f"🧠 Fact-checking: {processed_claim}")
        lang = _lang_hint_from_claim(processed_claim)

        # Collect results from all sources and remove duplicates
        all_results = []
        for domain in NEWS_AGENCIES:
            domain_results = _fetch_serp(f"{processed_claim} site:{domain}", extra={"hl": lang} if lang else None, num=2)
            all_results.extend(domain_results)
        google_results = _fetch_serp(processed_claim, extra={"hl": lang} if lang else None, num=k_sources)
        all_results.extend(google_results)
        
        # Remove duplicates based on URL
        results = []
        seen_urls = set()
        for result in all_results:
            url = result.get("link", "")
            # Only add if URL is not empty and not seen before
            if url and url not in seen_urls:
                results.append(result)
                seen_urls.add(url)

        print(f"🔎 Total combined results: {len(results)}")

        if not results:
            no_results_by_lang = {
                "ar": "لم يتم العثور على نتائج بحث.",
                "en": "No search results were found.",
                "fr": "Aucun résultat de recherche trouvé.",
                "es": "No se encontraron resultados de búsqueda.",
                "cs": "Nebyly nalezeny žádné výsledky vyhledávání.",
                "de": "Es wurden keine Suchergebnisse gefunden.",
                "tr": "Arama sonuçları bulunamadı.",
                "ru": "Результаты поиска не найдены.",
            }
            return {"case": "غير مؤكد", "talk": no_results_by_lang.get(lang, no_results_by_lang["en"]), "sources": [], "news_article": None}

        def clip(s: str, n: int) -> str:
            return s.strip() if len(s) <= n else s[:n] + "…"

        context = "\n\n---\n\n".join(
            f"عنوان: {clip(r['title'], 100)}\nملخص: {clip(r['snippet'], 200)}\nرابط: {r['link']}"
            for r in results
        )

        system_prompt = FACT_PROMPT_SYSTEM.replace("LANG_HINT", lang)
        user_msg = f"""
LANG_HINT: {lang}
CURRENT_DATE: {datetime.now().strftime('%Y-%m-%d')}

الادعاء:
{processed_claim}

السياق:
{context}
""".strip()

        print("📤 Sending prompt to OpenAI")
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        answer = (resp.choices[0].message.content or "").strip()
        if answer.startswith("```"):
            answer = answer.strip("` \n")
            if answer.lower().startswith("json"):
                answer = answer[4:].strip()

        parsed = json.loads(answer)

        case = parsed.get("الحالة", "غير مؤكد")
        talk = parsed.get("talk", "")
        sources = parsed.get("sources", [])
        
        # Remove duplicates and irrelevant sources
        if sources:
            unique_sources = []
            seen_source_urls = set()
            
            # Extract key words from claim (ignore common stop words)
            stop_words = {'في', 'من', 'إلى', 'على', 'عن', 'مع', 'هذا', 'هذه', 'ذلك', 'التي', 'الذي', 
                         'و', 'أو', 'لكن', 'ف', 'ب', 'ك', 'ل', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 
                         'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
            claim_words = set(word.lower() for word in processed_claim.split() if word.lower() not in stop_words and len(word) > 2)
            
            for source in sources:
                source_url = source.get("url", "")
                source_title = source.get("title", "").lower()
                source_snippet = source.get("snippet", "").lower()
                
                # Skip if URL is empty or already seen
                if not source_url or source_url in seen_source_urls:
                    continue
                
                # Check if source is relevant to the claim
                # More strict relevance check: title + snippet should contain meaningful key words
                title_words = set(word.lower() for word in source_title.split() if word.lower() not in stop_words and len(word) > 2)
                snippet_words = set(word.lower() for word in source_snippet.split() if word.lower() not in stop_words and len(word) > 2)
                all_source_words = title_words | snippet_words
                
                # Calculate relevance score
                if claim_words and all_source_words:
                    common_words = claim_words & all_source_words
                    relevance_ratio = len(common_words) / len(claim_words) if claim_words else 0
                    
                    # More lenient threshold to ensure we get enough sources
                    # Require at least 20% overlap OR at least 1-2 key words in common
                    min_common = max(1, int(len(claim_words) * 0.2))
                    
                    # Accept if relevance is reasonable (20% or has at least min_common words)
                    if len(common_words) >= min_common or relevance_ratio >= 0.2:
                        unique_sources.append(source)
                        seen_source_urls.add(source_url)
                        if os.getenv("FACT_DEBUG", "0") == "1":
                            print(f"✓ Relevant source: {source_title[:50]}... (score: {relevance_ratio:.2f}, common: {len(common_words)})")
                    else:
                        if os.getenv("FACT_DEBUG", "0") == "1":
                            print(f"✗ Filtered out: {source_title[:50]}... (score: {relevance_ratio:.2f}, common: {len(common_words)})")
                elif len(source_title) > 0:
                    # If claim has no meaningful words, just check if source has title
                    unique_sources.append(source)
                    seen_source_urls.add(source_url)
            
            sources = unique_sources
            
            # Ensure we have at least 3 sources if available from original results
            # If we filtered too aggressively and have < 3 sources, add more from results
            if len(sources) < 3 and len(results) > 0:
                print(f"⚠️ Only {len(sources)} sources after filtering, adding more from search results...")
                # Add sources from original results that haven't been added yet
                for r in results[:10]:
                    url = r.get("link", "")
                    if url and url not in seen_source_urls:
                        sources.append({
                            "title": r.get("title", ""),
                            "url": url,
                            "snippet": r.get("snippet", "")
                        })
                        seen_source_urls.add(url)
                        if len(sources) >= 5:  # Target at least 5 sources
                            break
                print(f"📚 Now have {len(sources)} sources after adding from search results")
            
            # Limit sources to top 10 to avoid overwhelming response
            if len(sources) > 10:
                sources = sources[:10]
                print(f"📚 Limited sources to top 10 (from {len(unique_sources)})")

        uncertain_terms = {
            "ar": {"غير مؤكد"},
            "en": {"uncertain"},
            "fr": {"incertain"},
            "es": {"incierto"},
            "cs": {"nejisté", "nejiste", "nejistá"},
            "de": {"unsicher"},
            "tr": {"belirsiz"},
            "ru": {"неопределенно", "неопределённо", "неопределенный"},
        }
        lowered = case.strip().lower()
        is_uncertain = lowered in {t for s in uncertain_terms.values() for t in s}
        
        # Generate professional news article if requested for all cases (true, false, uncertain)
        news_article = ""
        if generate_news:
            print("📰 Generating professional news article as requested...")
            # Use the fact-check analysis (talk) and sources for news generation
            news_article = generate_professional_news_article_from_analysis(processed_claim, case, talk, results, lang)
        
        # Generate X tweet if requested for all cases (true, false, uncertain)
        x_tweet = ""
        if generate_tweet:
            print("🐦 Generating X tweet as requested...")
            # Use the original search results for tweet generation
            x_tweet = generate_x_tweet(processed_claim, case, talk, results, lang)
        
        # Clear sources for uncertain results unless explicitly requested to preserve them
        # But if preserve_sources is true, use the original search results instead of AI sources
        if is_uncertain:
            if preserve_sources:
                # Use original search results when preserving sources (already deduplicated)
                sources = [{"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")} for r in results]
            else:
                # Clear sources as per original logic
                sources = []

        return {
            "case": case, 
            "talk": talk, 
            "sources": sources,
            "news_article": news_article if generate_news else None,
            "x_tweet": x_tweet if generate_tweet else None
        }

    except Exception as e:
        print("❌ Error:", traceback.format_exc())
        error_by_lang = {
            "ar": "⚠️ حدث خطأ أثناء التحقق.",
            "en": "⚠️ An error occurred during fact-checking.",
            "fr": "⚠️ Une erreur s'est produite lors de la vérification des faits.",
            "es": "⚠️ Se produjo un error durante la verificación de hechos.",
            "cs": "⚠️ Během ověřování faktů došlo k chybě.",
            "de": "⚠️ Bei der Faktenprüfung ist ein Fehler aufgetreten.",
            "tr": "⚠️ Doğrulama sırasında bir hata oluştu.",
            "ru": "⚠️ Во время проверки фактов произошла ошибка.",
        }
        try:
            lang = _lang_hint_from_claim(processed_claim if 'processed_claim' in locals() else claim_text)
        except Exception:
            lang = "en"
        return {"case": "غير مؤكد", "talk": error_by_lang.get(lang, error_by_lang["en"]), "sources": [], "news_article": None}
