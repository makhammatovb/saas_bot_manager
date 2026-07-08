from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet


router = DefaultRouter()

router.register(r'companies', CompanyViewSet, basename='companies') # checked

urlpatterns = router.urls
