from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
    
urlpatterns = [
    path('', views.index, name='index'),
    path('analyze/', views.analyze, name='analyze'),
    # path('/', views.analyze, name='analyze'),
    path('text_to_speech/', views.text_to_speech, name='text_to_speech'),
    path("prompt/",views.ask_prompt,name="ask_prompt")
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)