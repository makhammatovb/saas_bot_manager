from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=100, null=True, blank=True, unique=True)
    api_id = models.IntegerField()
    api_hash = models.CharField(max_length=255)
    session_name = models.CharField(max_length=255, null=True, blank=True, unique=True)
    is_active = models.BooleanField(default=True)
    daily_add_limit = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def get_daily_limit(self):
        from django.conf import settings
        return self.daily_add_limit or settings.DAILY_ADD_LIMIT

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            update_fields = []
            if not self.slug:
                self.slug = f"{self.name.lower().replace(' ', '-')}-{self.id}"
                update_fields.append("slug")
            if not self.session_name:
                self.session_name = f"company_{self.id}_session"
                update_fields.append("session_name")
            if update_fields:
                super().save(update_fields=update_fields)

    class Meta:
        verbose_name_plural = "Companies"
        db_table = "companies"


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
        db_table = "telegram_users"


class TelegramGroup(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='groups', null=True, blank=True)
    telegram_id = models.BigIntegerField()
    title = models.CharField(max_length=255, blank=True)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('company', 'telegram_id')
        verbose_name_plural = "Telegram Groups"
        db_table = "telegram_groups"


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
    error = models.TextField(null=True, blank=True)
    retry_after = models.DateTimeField(null=True, blank=True)
    requested_by = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Jobs"
        db_table = "jobs"
