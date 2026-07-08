from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from core.models import Job

class StatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        if user.is_staff:
            total_jobs = Job.objects.count()
            pending = Job.objects.filter(status='pending').count()
        else:
            total_jobs = Job.objects.filter(company=user.company).count()
            pending = Job.objects.filter(company=user.company, status='pending').count()

        return Response({
            "status": "ok",
            "company": user.company.name if hasattr(user, 'company') and user.company else "All Companies",
            "today": str(today),
            "total_jobs": total_jobs,
            "pending_jobs": pending,
            "daily_limit": getattr(settings, 'DAILY_ADD_LIMIT', 50),
        })
    