from rest_framework import serializers
from .models import Company, CustomUser, TelegramUser, TelegramGroup, Job
from django.contrib.auth import get_user_model


class CompanySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Company
        fields = '__all__'

    
class TelegramUserViewSerializer(serializers.ModelSerializer):
    company = CompanySerializer()

    class Meta:
        model = TelegramUser
        fields = '__all__'


class TelegramUserWriteSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = TelegramUser
        fields = '__all__'


class TelegramGroupViewSerializer(serializers.ModelSerializer):
    company = CompanySerializer()

    class Meta:
        model = TelegramGroup
        fields = '__all__'


class TelegramGroupWriteSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = TelegramGroup
        fields = '__all__'


class JobViewSerializer(serializers.ModelSerializer):
    company = CompanySerializer()

    class Meta:
        model = Job
        fields = '__all__'


class JobWriteSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Job
        fields = '__all__'


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'company', 'password', 'role']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            company=validated_data.get('company', None),
            password=validated_data['password'],
            role=validated_data.get('role', 'company_manager')
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'company', 'role', 'is_active']


class UserUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'company', 'role', 'is_active']


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)
