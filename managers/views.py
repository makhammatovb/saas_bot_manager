from rest_framework import viewsets, generics, views, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from core.models import CustomUser, TelegramUser, TelegramGroup, Job
from core.permissions import IsCompanyManagerOrSuperAdmin, IsSuperAdmin
from core.serializers import (
    UserLoginSerializer, UserRegisterSerializer, UserProfileSerializer, PasswordChangeSerializer,
    TelegramUserViewSerializer,
    TelegramUserWriteSerializer,
    TelegramGroupViewSerializer,
    TelegramGroupWriteSerializer,
    JobViewSerializer,
    JobWriteSerializer, UserUpdateSerializer,
)
from .pagination import CustomPagination


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [IsSuperAdmin]


class UserLoginView(views.APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'success': True,
                'user': UserProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({"error": "Old password is incorrect"}, status=400)
            
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Password changed successfully"})
        return Response(serializer.errors, status=400)
    

class ManagerListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = CustomPagination


class ManagerUpdateUserView(generics.UpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [IsSuperAdmin]


class TelegramUserViewSet(viewsets.ModelViewSet):
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['username']
    filterset_fields = ['company']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return TelegramUser.objects.all()
        company_id = getattr(user, 'company_id', None)
        if company_id:
            return TelegramUser.objects.filter(company_id=company_id)
        return TelegramUser.objects.none()

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return TelegramUserWriteSerializer
        return TelegramUserViewSerializer
    
    def perform_create(self, serializer):
        user = self.request.user
        company = user.company if hasattr(user, 'company') and user.company else None
        serializer.save(
            added_by=user.id,
            company=company
        )


class TelegramGroupViewSet(viewsets.ModelViewSet):
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['title']
    filterset_fields = ['company']

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsCompanyManagerOrSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return TelegramGroup.objects.all()
        
        company_id = getattr(user, 'company_id', None)
        if company_id:
            return TelegramGroup.objects.filter(company_id=company_id)
        return TelegramGroup.objects.none()

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return TelegramGroupWriteSerializer
        return TelegramGroupViewSerializer
    
    def perform_create(self, serializer):
        user = self.request.user
        company = user.company if hasattr(user, 'company') and user.company else None
        serializer.save(
            company=company
        )
    
    @action(detail=True, methods=['post'], url_path='push')
    def push(self, request, pk=None):
        group = self.get_object()
        try:
            count = enqueue_push(
                company=group.company,
                group_telegram_id=group.telegram_id,
                requested_by=request.user.id
            )
            return Response({
                "status": "success",
                "message": f"Successfully queued {count} users to be added to group '{group.title}'.",
                "queued_count": count
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='wipe')
    def wipe(self, request, pk=None):
        group = self.get_object()
        try:
            count = enqueue_wipe(
                company=group.company,
                group_telegram_id=group.telegram_id,
                requested_by=request.user.id
            )
            return Response({
                "status": "success",
                "message": f"Successfully queued {count} users to be removed from group '{group.title}'.",
                "queued_count": count
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class JobViewSet(viewsets.ModelViewSet):
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['job_type', 'user_ref']
    filterset_fields = ['company', 'status', 'job_type']

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsCompanyManagerOrSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Job.objects.all()
        
        company_id = getattr(user, 'company_id', None)
        if company_id:
            return Job.objects.filter(company_id=company_id)
        return Job.objects.none()

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return JobWriteSerializer
        return JobViewSerializer
    