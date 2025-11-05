from django.urls import path
from .views import (
    FactCheckWithOpenaiView, 
    AnalyticalNewsView,
    ComposeNewsView,
    ComposeTweetView
)

urlpatterns = [
    path("", FactCheckWithOpenaiView.as_view(), name="fact_check"),
    path("analytical_news/", AnalyticalNewsView.as_view(), name="analytical-news"),
    path("compose_news/", ComposeNewsView.as_view(), name="compose-news"),
    path("compose_tweet/", ComposeTweetView.as_view(), name="compose-tweet"),
]
