from django.urls import path
from .views import ImageFactCheckView

urlpatterns = [
    path("", ImageFactCheckView.as_view(), name="image-fact-check"),
]

