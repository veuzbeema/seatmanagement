from django.contrib import admin

# Register your models here.
from seatalignment.models import Seat, BadgeTemplate

admin.site.register(Seat)
admin.site.register(BadgeTemplate)
