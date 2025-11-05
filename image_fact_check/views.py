from __future__ import annotations
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.http import JsonResponse, HttpRequest, HttpResponse
import traceback
from io import BytesIO

from .utils import check_image_fact_and_ai_async


@method_decorator(csrf_exempt, name="dispatch")
class ImageFactCheckView(View):
    """
    POST /image_check/
    Body: Form-data with 'image' file
    
    Response (بالعربية فقط):
    {
        ok: true,
        is_ai_generated: bool,
        is_photoshopped: bool,
        is_fake: bool,
        message: "رسالة بالعربية توضح النتيجة بالتفصيل"
    }
    
    ⚡ ASYNC VERSION - يفحص إذا كانت الصورة مصنوعة بالذكاء الاصطناعي، معدلة بـ Photoshop، أو مزورة
    """

    async def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            # Check if image file was uploaded
            if 'image' not in request.FILES:
                return JsonResponse(
                    {"ok": False, "error": "لم يتم رفع صورة. يرجى رفع صورة مع المفتاح 'image'."},
                    status=400,
                )
            
            image_file = request.FILES['image']
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return JsonResponse(
                    {"ok": False, "error": f"نوع الملف غير مدعوم. الأنواع المدعومة: {', '.join(allowed_types)}"},
                    status=400,
                )
            
            # Check file size (max 50MB - increased for high-resolution images)
            max_size = 50 * 1024 * 1024  # 50MB
            if image_file.size > max_size:
                return JsonResponse(
                    {"ok": False, "error": "حجم الصورة كبير جداً. الحد الأقصى: 50 ميجابايت"},
                    status=400,
                )
            
            # Warn if image is very large but still process it
            if image_file.size > 20 * 1024 * 1024:  # 20MB
                print(f"⚠️ Large image detected: {image_file.size / (1024*1024):.2f} MB - Processing may take longer...")
            
            # Read file data synchronously before passing to async function
            # Django file uploads are synchronous - reading synchronously is fine in async views
            image_file.seek(0)
            image_data = image_file.read()
            
            # Create a BytesIO object from the file data for async processing
            image_file_obj = BytesIO(image_data)
            image_file_obj.name = getattr(image_file, 'name', 'image.jpg')  # Preserve filename if available
            
            # Analyze image (اللغة دائماً عربية)
            result = await check_image_fact_and_ai_async(image_file_obj)
            
            # Check if there was an error or model refused
            if 'error' in result or result.get("is_ai_generated") is None and result.get("is_photoshopped") is None:
                return JsonResponse(
                    {
                        "ok": False,
                        "error": result.get("message", "حدث خطأ أثناء تحليل الصورة"),
                        "is_ai_generated": result.get("is_ai_generated"),
                        "is_photoshopped": result.get("is_photoshopped"),
                        "is_fake": result.get("is_fake"),
                        "message": result.get("message", "حدث خطأ أثناء تحليل الصورة")
                    },
                    status=200,  # Return 200 with ok: false instead of 500
                )
            
            # Return response (بالعربية فقط)
            return JsonResponse(
                {
                    "ok": True,
                    "is_ai_generated": result.get("is_ai_generated"),
                    "is_photoshopped": result.get("is_photoshopped"),
                    "is_fake": result.get("is_fake"),
                    "message": result.get("message", "حدث خطأ أثناء تحليل الصورة")
                },
                status=200,
            )

        except Exception as e:
            return JsonResponse(
                {
                    "ok": False,
                    "error": str(e),
                    "trace": traceback.format_exc(),
                },
                status=500,
            )
