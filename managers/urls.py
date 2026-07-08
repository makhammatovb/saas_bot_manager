from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from .views import (
    RegisterView, 
    UserLoginView, 
    ManagerUpdateUserView,
    ProfileView, 
    PasswordChangeView,
    ManagerListView,
    TelegramUserViewSet,
    TelegramGroupViewSet,
    JobViewSet,
)

router = DefaultRouter()

router.register(r'telegram-users', TelegramUserViewSet, basename='telegram-user') # checked
router.register(r'telegram-groups', TelegramGroupViewSet, basename='telegram-group')
router.register(r'jobs', JobViewSet, basename='job')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'), # checked 
    path('auth/login/', UserLoginView.as_view(), name='login'), # checked
    path('auth/profile/', ProfileView.as_view(), name='profile'), # checked
    path('auth/refresh-token/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/change-password/', PasswordChangeView.as_view(), name='change-password'), # checked
    path('managers/', ManagerListView.as_view(), name='manager-list'), # checked
    path('managers/<int:pk>/update/', ManagerUpdateUserView.as_view(), name='manager-update'), # checked
    path('', include(router.urls)),
]