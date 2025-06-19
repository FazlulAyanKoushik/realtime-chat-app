""" User models for the system. """
import uuid

from django.contrib.auth.base_user import (
    BaseUserManager,
)
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.db import models
from django.db.models import TextChoices



#=====================================
# Media File Prefixes
#=====================================
def get_user_media_path_prefix(instance, filename):
    return f"users/{instance.uid}/{filename}"

# =====================================
# Choices
#=====================================
class Status(TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DRAFT = "DRAFT", "DRAFT"
    INACTIVE = "INACTIVE", "Inactive"
    REMOVED = "REMOVED", "Removed"


class UserKind(TextChoices):
    ADMIN = "ADMIN", "Admin"
    END_USER = "END_USER", "End User"
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    UNDEFINED = "UNDEFINED", "Undefined"

#=====================================
# Base Model
#=====================================
class BaseModelWithUID(models.Model):
    uid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        unique=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        db_index=True,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def get_all_actives(self):
        return self.__class__.objects.filter(status=Status.ACTIVE).order_by("-pk")



#=======================================
# User Manager
#=======================================
class UserManager(BaseUserManager):
    """Managers for users."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have a email address")

        email = self.normalize_email(email)

        user = self.model(
            email=email, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        """Create a new superuser and return superuser"""

        user = self.create_user(
            email=email, password=password
        )
        user.is_superuser = True
        user.is_staff = True
        user.kind = UserKind.SUPER_ADMIN
        user.save(using=self._db)

        return user


#=======================================
# User Model
#=======================================
class User(AbstractBaseUser, BaseModelWithUID, PermissionsMixin):
    """Users in the System"""

    email = models.EmailField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(
        default=True,
    )
    is_staff = models.BooleanField(
        default=False,
    )
    kind = models.CharField(
        max_length=20,
        choices=UserKind.choices,
        default=UserKind.UNDEFINED,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "System User"
        verbose_name_plural = "System Users"
        ordering = ("-created_at",)