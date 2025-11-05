"""
Comprehensive Test File for Fact-Checking System
ملف اختبار شامل لنظام التحقق من الأخبار

يغطي جميع الحالات الممكنة:
- أخبار حقيقية (True)
- أخبار غير مؤكدة (Uncertain)
- حالات خاصة (Edge Cases)
- لغات مختلفة
- أنواع مختلفة من الأخبار
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from utils_async import check_fact_simple_async


# ==================== TEST CASES ====================

# 1. أخبار حقيقية متوقع أن تكون "حقيقي" (True)
EXPECTED_TRUE_CLAIMS = [
    {
        "claim": "إنشاء قطار يربط الدوحة بالرياض",
        "category": "مشروع حكومي",
        "expected": "حقيقي",
        "description": "مشروع قطار الخليج"
    },
    {
        "claim": "قطر تستضيف كأس العالم 2022",
        "category": "حدث رياضي",
        "expected": "حقيقي",
        "description": "حدث رياضي تاريخي"
    },
    {
        "claim": "جو بايدن رئيس الولايات المتحدة",
        "category": "حقيقة سياسية",
        "expected": "حقيقي",
        "description": "رئيس أمريكا الحالي"
    },
]

# 2. شائعات وأخبار كاذبة متوقع أن تكون "غير مؤكد" (Uncertain)
EXPECTED_UNCERTAIN_CLAIMS = [
    {
        "claim": "اكتشاف مدينة أطلانتس المفقودة في البحر الأحمر",
        "category": "شائعة",
        "expected": "غير مؤكد",
        "description": "شائعة غير موثقة"
    },
    {
        "claim": "انفجار بركان في القاهرة",
        "category": "شائعة",
        "expected": "غير مؤكد",
        "description": "لا يوجد بركان في القاهرة"
    },
    {
        "claim": "وصول مركبة فضائية غريبة إلى الأرض",
        "category": "خيال علمي",
        "expected": "غير مؤكد",
        "description": "غير مؤكد"
    },
]

# 3. حالات خاصة (Edge Cases)
EDGE_CASES = [
    {
        "claim": "الشمس تشرق من الشرق",
        "category": "حقيقة علمية",
        "expected": "حقيقي",
        "description": "حقيقة علمية عامة"
    },
    {
        "claim": "القاهرة عاصمة مصر",
        "category": "حقيقة جغرافية",
        "expected": "حقيقي",
        "description": "معلومة أساسية"
    },
    {
        "claim": "ترامب رئيس أمريكا حاليا",
        "category": "معلومة قديمة",
        "expected": "غير مؤكد",
        "description": "معلومة قديمة (كان رئيساً سابقاً)"
    },
]

# 4. أخبار بلغات مختلفة
MULTILINGUAL_CLAIMS = [
    {
        "claim": "Donald Trump elected president in 2024",
        "category": "English",
        "expected": "حقيقي",
        "description": "خبر بالإنجليزية"
    },
    {
        "claim": "La France a gagné la Coupe du Monde en 2018",
        "category": "French",
        "expected": "حقيقي",
        "description": "خبر بالفرنسية"
    },
]

# 5. أخبار رياضية
SPORTS_CLAIMS = [
        {
        "claim": "ليونيل ميسي فاز بكأس العالم 2022",
        "category": "رياضة",
        "expected": "حقيقي",
        "description": "فوز الأرجنتين"
    },
    {
        "claim": "الهلال السعودي يفوز بدوري أبطال آسيا",
        "category": "رياضة",
        "expected": "حقيقي",
        "description": "إنجاز رياضي"
    },
]

# 6. أخبار اقتصادية
ECONOMIC_CLAIMS = [
    {
        "claim": "ارتفاع أسعار النفط في 2022",
        "category": "اقتصاد",
        "expected": "حقيقي",
        "description": "حدث اقتصادي"
    },
    {
        "claim": "الدولار يساوي 100 ريال سعودي",
        "category": "اقتصاد",
        "expected": "غير مؤكد",
        "description": "معلومة خاطئة"
    },
]

# 7. أخبار سياسية
POLITICAL_CLAIMS = [
    {
        "claim": "قمة مجلس التعاون الخليجي في الرياض",
        "category": "سياسة",
        "expected": "حقيقي",
        "description": "حدث دبلوماسي"
    },
    {
        "claim": "الأمم المتحدة تأسست عام 1945",
        "category": "سياسة",
        "expected": "حقيقي",
        "description": "حقيقة تاريخية"
    },
]

# 8. أخبار علمية وتكنولوجية
SCIENCE_TECH_CLAIMS = [
    {
        "claim": "إطلاق تلسكوب جيمس ويب الفضائي",
        "category": "علوم",
        "expected": "حقيقي",
        "description": "إنجاز علمي"
    },
    {
        "claim": "اكتشاف لقاح كورونا",
        "category": "طب",
        "expected": "حقيقي",
        "description": "إنجاز طبي"
    },
]

# 9. كوارث وأحداث طبيعية
DISASTER_CLAIMS = [
    {
        "claim": "زلزال تركيا وسوريا 2023",
        "category": "كارثة",
        "expected": "حقيقي",
        "description": "كارثة طبيعية"
    },
    {
        "claim": "إعصار كاترينا يضرب نيو أورليانز",
        "category": "كارثة",
        "expected": "حقيقي",
        "description": "كارثة تاريخية"
    },
]

# 10. أخبار فنية وترفيهية
ENTERTAINMENT_CLAIMS = [
    {
        "claim": "فيلم Oppenheimer يفوز بأوسكار أفضل فيلم",
        "category": "فن",
        "expected": "حقيقي",
        "description": "جائزة فنية"
    },
]

# 11. شائعات شهيرة (لاختبار الكشف عن الأخبار الكاذبة)
FAMOUS_RUMORS = [
    {
        "claim": "بيل غيتس يزرع شرائح في اللقاحات",
        "category": "شائعة",
        "expected": "غير مؤكد",
        "description": "نظرية مؤامرة شهيرة"
    },
    {
        "claim": "5G تسبب كورونا",
        "category": "شائعة",
        "expected": "غير مؤكد",
        "description": "معلومة مضللة"
    },
]

# 12. حالات نصوص قصيرة جدًا
SHORT_CLAIMS = [
    {
        "claim": "ترامب",
        "category": "نص قصير",
        "expected": "غير مؤكد",
        "description": "نص قصير جداً"
    },
    {
        "claim": "زلزال",
        "category": "نص قصير",
        "expected": "غير مؤكد",
        "description": "كلمة واحدة فقط"
    },
]

# 13. نصوص طويلة ومعقدة
COMPLEX_CLAIMS = [
    {
        "claim": "وزارة الخارجية السعودية تعلن عن توقيع اتفاقية شراكة استراتيجية مع فرنسا في مجالات الطاقة المتجددة والتكنولوجيا والثقافة خلال زيارة ولي العهد إلى باريس",
        "category": "نص معقد",
        "expected": "حقيقي",
        "description": "خبر طويل ومفصل"
    },
]

# 14. أخبار بتواريخ محددة
DATE_SPECIFIC_CLAIMS = [
    {
        "claim": "بدء الحرب العالمية الثانية في 1939",
        "category": "تاريخ",
        "expected": "حقيقي",
        "description": "حدث تاريخي بتاريخ"
    },
]

# 15. أخبار محلية (خليجية)
LOCAL_GULF_CLAIMS = [
    {
        "claim": "افتتاح برج خليفة في دبي",
        "category": "محلي",
        "expected": "حقيقي",
        "description": "حدث محلي خليجي"
    },
    {
        "claim": "تأسيس مجلس التعاون الخليجي",
        "category": "محلي",
        "expected": "حقيقي",
        "description": "حدث تاريخي خليجي"
    },
]


# ==================== TEST EXECUTION ====================

async def test_single_claim(claim_data: dict, test_number: int, total_tests: int):
    """Test a single claim"""
    claim = claim_data["claim"]
    category = claim_data["category"]
    expected = claim_data["expected"]
    description = claim_data["description"]
    
    print(f"\n{'='*80}")
    print(f"Test {test_number}/{total_tests}")
    print(f"{'='*80}")
    print(f"📝 الادعاء: {claim}")
    print(f"📂 الفئة: {category}")
    print(f"🎯 النتيجة المتوقعة: {expected}")
    print(f"📋 الوصف: {description}")
    print(f"{'-'*80}")
    
    try:
        # Run fact-check
        result = await check_fact_simple_async(claim, k_sources=8, generate_news=False, preserve_sources=False, generate_tweet=False)
        
        case = result.get("case", "غير معروف")
        talk = result.get("talk", "")
        sources = result.get("sources", [])
        
        # Normalize case for comparison
        case_normalized = case.lower().strip()
        expected_normalized = expected.lower().strip()
        
        # Check if result matches expected
        is_match = (
            (expected_normalized in ["حقيقي", "true", "vrai"] and case_normalized in ["حقيقي", "true", "vrai"]) or
            (expected_normalized in ["غير مؤكد", "uncertain", "incertain"] and case_normalized in ["غير مؤكد", "uncertain", "incertain"])
        )
        
        status = "✅ نجح" if is_match else "❌ فشل"
        
        print(f"\n📊 النتيجة الفعلية: {case}")
        print(f"🔍 الحالة: {status}")
        print(f"📚 عدد المصادر: {len(sources)}")
        
        if talk:
            # Show first 200 characters of talk
            talk_preview = talk[:200] + "..." if len(talk) > 200 else talk
            print(f"💬 التحليل: {talk_preview}")
        
        if sources:
            print(f"\n📎 المصادر (أول 3):")
            for i, source in enumerate(sources[:3], 1):
                title = source.get("title", "بدون عنوان")
                url = source.get("url", "بدون رابط")
                print(f"   {i}. {title[:60]}...")
                print(f"      {url}")
        
        return {
            "claim": claim,
            "category": category,
            "expected": expected,
            "actual": case,
            "match": is_match,
            "sources_count": len(sources),
            "description": description
        }
        
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")
        return {
            "claim": claim,
            "category": category,
            "expected": expected,
            "actual": "ERROR",
            "match": False,
            "sources_count": 0,
            "description": description,
            "error": str(e)
        }


async def run_all_tests():
    """Run all comprehensive tests"""
    print("\n" + "="*80)
    print("🧪 اختبار شامل لنظام التحقق من الأخبار")
    print("Comprehensive Fact-Checking System Test")
    print("="*80)
    print(f"⏰ بدء الاختبار: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Combine all test cases
    all_test_cases = (
        EXPECTED_TRUE_CLAIMS +
        EXPECTED_UNCERTAIN_CLAIMS +
        EDGE_CASES +
        MULTILINGUAL_CLAIMS +
        SPORTS_CLAIMS +
        ECONOMIC_CLAIMS +
        POLITICAL_CLAIMS +
        SCIENCE_TECH_CLAIMS +
        DISASTER_CLAIMS +
        ENTERTAINMENT_CLAIMS +
        FAMOUS_RUMORS +
        SHORT_CLAIMS +
        COMPLEX_CLAIMS +
        DATE_SPECIFIC_CLAIMS +
        LOCAL_GULF_CLAIMS
    )
    
    total_tests = len(all_test_cases)
    print(f"📊 إجمالي الاختبارات: {total_tests}")
    
    results = []
    for i, test_case in enumerate(all_test_cases, 1):
        result = await test_single_claim(test_case, i, total_tests)
        results.append(result)
        
        # Small delay between tests to avoid rate limiting
        await asyncio.sleep(2)
    
    # Summary
    print("\n" + "="*80)
    print("📈 ملخص النتائج - Results Summary")
    print("="*80)
    
    passed = sum(1 for r in results if r["match"])
    failed = sum(1 for r in results if not r["match"])
    errors = sum(1 for r in results if r["actual"] == "ERROR")
    
    print(f"\n✅ النجاح: {passed}/{total_tests} ({passed*100/total_tests:.1f}%)")
    print(f"❌ الفشل: {failed}/{total_tests} ({failed*100/total_tests:.1f}%)")
    print(f"⚠️ الأخطاء: {errors}/{total_tests} ({errors*100/total_tests:.1f}%)")
    
    # Group by category
    print("\n" + "-"*80)
    print("📂 النتائج حسب الفئة:")
    print("-"*80)
    
    categories = {}
    for result in results:
        cat = result["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0, "total": 0}
        categories[cat]["total"] += 1
        if result["match"]:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1
    
    for cat, stats in sorted(categories.items()):
        success_rate = stats["passed"] * 100 / stats["total"] if stats["total"] > 0 else 0
        print(f"   {cat}: {stats['passed']}/{stats['total']} ({success_rate:.0f}%)")
    
    # Failed tests details
    failed_tests = [r for r in results if not r["match"]]
    if failed_tests:
        print("\n" + "-"*80)
        print("❌ الاختبارات الفاشلة:")
        print("-"*80)
        for i, test in enumerate(failed_tests, 1):
            print(f"\n{i}. {test['claim'][:60]}...")
            print(f"   المتوقع: {test['expected']} | الفعلي: {test['actual']}")
            print(f"   الفئة: {test['category']}")
    
    print("\n" + "="*80)
    print(f"⏰ انتهاء الاختبار: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Save results to JSON
    output_file = "test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "success_rate": passed * 100 / total_tests if total_tests > 0 else 0,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 تم حفظ النتائج في: {output_file}")


async def run_quick_test():
    """Run a quick test with only a few cases"""
    print("\n" + "="*80)
    print("⚡ اختبار سريع - Quick Test")
    print("="*80)
    
    quick_cases = [
        EXPECTED_TRUE_CLAIMS[0],
        EXPECTED_UNCERTAIN_CLAIMS[0],
        EDGE_CASES[0],
        SPORTS_CLAIMS[0],
    ]
    
    results = []
    for i, test_case in enumerate(quick_cases, 1):
        result = await test_single_claim(test_case, i, len(quick_cases))
        results.append(result)
        await asyncio.sleep(1)
    
    passed = sum(1 for r in results if r["match"])
    print(f"\n✅ النجاح: {passed}/{len(quick_cases)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Run quick test
        asyncio.run(run_quick_test())
    else:
        # Run all tests
        asyncio.run(run_all_tests())

