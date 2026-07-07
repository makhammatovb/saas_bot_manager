from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.models import Company
from core.serializers import CompanySerializer
from core.permissions import IsSuperAdmin, IsCompanyManagerOrSuperAdmin


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Company.objects.all()
        company_id = getattr(user, 'company_id', None)
        if company_id:
            return Company.objects.filter(id=company_id)
        return Company.objects.none()

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsSuperAdmin()]
        return [IsCompanyManagerOrSuperAdmin()]
    