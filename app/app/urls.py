from django.contrib import admin
from django.urls import path, include
from core.api import api as core_api
from user.api import api as user_api
from recipe.api import api as recipe_api
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/core/', core_api.urls),
    path('api/user/', user_api.urls),
    path('api/recipe/', recipe_api.urls),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
