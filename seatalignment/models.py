from django.db import models
from django.core.validators import RegexValidator
from core.models import TimestampedModel 

class Seat(TimestampedModel):
    seat_no = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^SEAT-\d+$',
                message='Seat No must be in format SEAT-101'
            )
        ],
        help_text="e.g., SEAT-101"
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(db_index=True)
    company = models.CharField(max_length=100, blank=True)
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9\s\-\(\)]+$',
                message='Enter a valid phone number'
            )
        ]
    )

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'
        PREFER_NOT_TO_SAY = 'prefer_not_to_say', 'Prefer not to say'

    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        blank=True
    )

    class PrintStatus(models.TextChoices):
        NOT_PRINTED = 'not_printed', 'Not Printed'
        PRINTED = 'printed', 'Printed'

    print_status = models.CharField(
        max_length=20,
        choices=PrintStatus.choices,
        default=PrintStatus.NOT_PRINTED,
        db_index=True
    )

    class Meta:
        verbose_name = 'Seat'
        verbose_name_plural = 'Seats'
        ordering = ['seat_no']
        indexes = [
            models.Index(fields=['seat_no']),
            models.Index(fields=['email']),
            models.Index(fields=['print_status']),
        ]

    def __str__(self):
        return f"{self.seat_no} - {self.name}"

    def clean(self):
        if self.seat_no:
            self.seat_no = self.seat_no.upper().strip()


from django.core.validators import FileExtensionValidator

class SeatCSVUpload(TimestampedModel):
    file = models.FileField(
        upload_to='seat_uploads/',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])]
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('processing', 'Processing'),
            ('success', 'Success'),
            ('partial', 'Partial Success'),
            ('failed', 'Failed')
        ],
        default='processing'
    )
    processed = models.BooleanField(default=False)
    processed_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    duplicate_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Seat CSV Upload'
        verbose_name_plural = 'Seat CSV Uploads'

    def __str__(self):
        return f"CSV Upload #{self.id} - {self.status}"
    



# from django.contrib.auth.models import User
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class BadgeTemplate(TimestampedModel):
    """
    Stores a saved badge layout for seat number printing.
    One global template (or per-event later).
    """
    name = models.CharField(
        max_length=100,
        default="Default Seat Template",
        help_text="Name of the template (e.g., Conference 2025)"
    )

    position_x = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        help_text="X offset in pixels"
    )
    position_y = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        help_text="Y offset in pixels"
    )

    # Text styling
    font_size = models.PositiveIntegerField(
        default=24,
        validators=[MinValueValidator(12), MaxValueValidator(100)],
        help_text="Font size in pixels"
    )
    is_bold = models.BooleanField(default=False)
    text_align = models.CharField(
        max_length=10,
        choices=[('left', 'Left'), ('center', 'Center'), ('right', 'Right')],
        default='left'
    )

    # Page size (in mm)
    page_width_mm = models.PositiveIntegerField(
        default=105,
        validators=[MinValueValidator(50), MaxValueValidator(500)]
    )
    page_height_mm = models.PositiveIntegerField(
        default=148,
        validators=[MinValueValidator(50), MaxValueValidator(500)]
    )

    # Optional: per-user or per-event
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='badge_templates'
    )

    class Meta:
        verbose_name = 'Badge Template'
        verbose_name_plural = 'Badge Templates'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.page_width_mm}×{self.page_height_mm}mm)"