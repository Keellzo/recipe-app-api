from django.contrib import admin
from django.urls import path, include
from core.api import api as core_api
from user.api import api as user_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/core/', core_api.urls),
    path('api/user/', user_api.urls),
]
