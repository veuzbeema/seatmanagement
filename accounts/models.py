from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone
from core.models import TimestampedModel

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', UserType.ADMIN)
        extra_fields.setdefault('status', Status.ACTIVE)

        return self.create_user(email, password, **extra_fields)


class UserType(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    MANAGER = 'manager', 'Manager'
    STAFF = 'staff', 'Staff'

class Status(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.STAFF)
    email = models.EmailField(unique=True, db_index=True) 
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    date_joined = models.DateTimeField(default=timezone.now)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] 

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email


class UserPermission(models.Model):
    """
    Granular permissions per module and action.
    """
    class Module(models.TextChoices):
        SEATS = 'seats', 'Manage Seats'
        BADGES = 'badges', 'Print Badges'
        USERS = 'users', 'User Management'
        ALIGNMENT = 'alignment', 'Badge Alignment'

    class Action(models.TextChoices):
        VIEW = 'view', 'View'
        EDIT = 'edit', 'Edit'
        DELETE = 'delete', 'Delete'
        PRINT = 'print', 'Print'
        EXPORT = 'export', 'Export'
        CREATE = 'create', 'Create'
        UPLOAD = 'upload', 'Upload'
        RESET = 'reset', 'Reset'

    user = models.ForeignKey(
        'User', 
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    module = models.CharField(max_length=20, choices=Module.choices)
    action = models.CharField(max_length=20, choices=Action.choices)

    class Meta:
        unique_together = ('user', 'module', 'action')
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
        indexes = [
            models.Index(fields=['user', 'module']),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.get_module_display()}: {self.get_action_display()}"