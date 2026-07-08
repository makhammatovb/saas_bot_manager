from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    api_id = models.IntegerField()
    api_hash = models.CharField(max_length=255)
    session_name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.namea

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.name.lower().replace(" ", "-")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Companies"


class CustomUser(AbstractUser):
    company = models.ForeignKey(
        Company, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users'
    )
    role = models.CharField(
        max_length=20, 
        choices=[('super_admin', 'Super Admin'), ('company_manager', 'Company Manager')],
        default='company_manager'
    )
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        db_table = "users"


class TelegramUser(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='telegram_users', null=True, blank=True)
    telegram_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=100, null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    added_by = models.BigIntegerField(null=True, blank=True)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (('company', 'telegram_id'), ('company', 'username'))
        verbose_name_plural = "Telegram Users"


class TelegramGroup(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='groups', null=True, blank=True)
    telegram_id = models.BigIntegerField()
    title = models.CharField(max_length=255, blank=True)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('company', 'telegram_id')
        verbose_name_plural = "Telegram Groups"


class Job(models.Model):
    JOB_TYPES = [('add', 'Add'), ('remove', 'Remove')]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('in_progress', 'In Progress'),
        ('done', 'Done'), ('failed', 'Failed'), ('flood_wait', 'Flood Wait')
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    job_type = models.CharField(max_length=10, choices=JOB_TYPES)
    user_ref = models.CharField(max_length=100)
    group_telegram_id = models.BigIntegerField()
    status = models.CharField(max_length=20, default='pending', choices=STATUS_CHOICES)
    attempts = models.IntegerField(default=0)
    error = models.TextField(blank=True)
    retry_after = models.DateTimeField(null=True, blank=True)
    requested_by = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Jobs"
