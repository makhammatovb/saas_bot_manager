from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView, 
    LoginView, 
    ProfileView, 
    PasswordChangeView,
    ManagerListView,
    TelegramUserViewSet,
    TelegramGroupViewSet,
    JobViewSet,
)

router = DefaultRouter()

router.register(r'telegram-users', TelegramUserViewSet, basename='telegram-user')
router.register(r'telegram-groups', TelegramGroupViewSet, basename='telegram-group')
router.register(r'jobs', JobViewSet, basename='job')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    path('auth/change-password/', PasswordChangeView.as_view(), name='change-password'),
    path('managers/', ManagerListView.as_view(), name='manager-list'),
    path('', include(router.urls)),
]