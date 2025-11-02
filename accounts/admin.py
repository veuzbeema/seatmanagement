# # seats/admin.py
# from django.contrib import admin
# from .models import User, UserPermission

# @admin.register(User)
# class UserAdmin(admin.ModelAdmin):
#     list_display = ('email', 'user_type', 'status', 'date_joined')
#     list_filter = ('user_type', 'status')
#     search_fields = ('email',)

# @admin.register(UserPermission)
# class UserPermissionAdmin(admin.ModelAdmin):
#     list_display = ('user', 'module', 'action')
#     list_filter = ('module', 'action')

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserPermission

class UserAdmin(BaseUserAdmin):
    # Fields to display in admin
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'status', 'is_staff', 'is_superuser')
    list_filter = ('user_type', 'status', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    # Fields for add/edit forms
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('user_type', 'status', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )

admin.site.register(User, UserAdmin)
admin.site.register(UserPermission)


