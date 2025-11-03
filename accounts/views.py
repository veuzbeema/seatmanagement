import re
from django.shortcuts import render
from .models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import update_session_auth_hash
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import User, UserPermission
import json

from .utils import get_permissions

def user_list(request):
    
    users = User.objects.all().order_by('email')
    return render(request, 'users/user_list.html', {'users': users})

@login_required
def dashboard_view(request):
    user = request.user
    user_permissions = get_permissions(user=user)
    
    context = {
        'user': user,
        'permissions': user_permissions
    }
    return render(request, 'dashboard.html', context)


from django.contrib.auth import authenticate, login, logout

def login_page(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    

from django.contrib import messages
from django.shortcuts import redirect    

def logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login_page')


@csrf_exempt
def login_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')


        print("Login attempt:", email, password)
        
        user = authenticate(request, username=email, password=password)

        print("Authenticated user:", user)


        if user is None:
            return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

        if user.status != 'active':
            return JsonResponse({'success': False, 'error': 'User is inactive'}, status=403)

        login(request, user)

        perms = [{'module': p.module, 'action': p.action} for p in user.permissions.all()]

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.user_type,
                'permissions': perms
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)



# accounts/views.py
@login_required
@require_http_methods(["GET"])
def list_users(request):
    users = User.objects.all().prefetch_related('permissions')
    
    total = users.count()
    admins = users.filter(user_type='admin').count()
    managers = users.filter(user_type='manager').count()
    staff = users.filter(user_type='staff').count()

    user_list = []
    for u in users:
        full_name = f"{u.first_name} {u.last_name}".strip()
        display_name = full_name if full_name else u.email.split('@')[0].replace('.', ' ').title()
        
        perms = {f"{p.module}_{p.action}": True for p in u.permissions.all()}
        user_list.append({
            'id': u.id,
            'email': u.email,
            'name': display_name,
            'role': u.user_type,
            'status': 'active' if str(u.status).lower() in ['active', 'true', '1'] else 'inactive',
            'permissions': perms
        })

    return JsonResponse({
        'stats': {'total': total, 'admins': admins, 'managers': managers, 'staff': staff},
        'users': user_list
    })


# Validation helper functions
def validate_name(name):
    if not name or not name.strip():
        return "Name is required."
    if len(name) > 100:
        return "Name cannot exceed 100 characters."
    if not re.match(r'^[a-zA-Z\s]+$', name):
        return "Name can only contain letters and spaces."
    return None

def validate_email_format(email):
    if not email or not email.strip():
        return "Email is required."
    try:
        validate_email(email)
    except ValidationError:
        return "Invalid email format."
    return None

def validate_password(password):
    if not password:
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$', password):
        return "Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character."
    return None


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def create_user(request):
    data = json.loads(request.body)

    name_error = validate_name(data.get('name'))
    if name_error:
            return JsonResponse({'success': False, 'error': name_error}, status=400)
    
    email_error = validate_email_format(data.get('email'))
    if email_error:
            return JsonResponse({'success': False, 'error': email_error}, status=400)
    if User.objects.filter(email=data['email']).exists():
            return JsonResponse({'success': False, 'error': 'Email already exists'}, status=400)
    
    password_error = validate_password(data.get('password'))
    if password_error:
            return JsonResponse({'success': False, 'error': password_error}, status=400)
    
    if not data.get('role'):
            return JsonResponse({'success': False, 'error': 'Role is required'}, status=400)
    
    try:
        user = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            user_type=data['role'],
            status=data.get('status', 'active')
        )
        # Save permissions
        for perm in data.get('permissions', []):
            UserPermission.objects.create(
                user=user,
                module=perm['module'],
                action=perm['action']
            )
        return JsonResponse({'success': True, 'id': user.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)



@csrf_exempt
@login_required
@require_http_methods(["POST"])
def update_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        data = json.loads(request.body)

        if 'name' in data:
            name_error = validate_name(data['name'])
            if name_error:
                return JsonResponse({'success': False, 'error': name_error}, status=400)
            user.first_name = data['name']  # Adjust if name is stored differently

        # Validate email
        if 'email' in data:
            email_error = validate_email_format(data['email'])
            if email_error:
                return JsonResponse({'success': False, 'error': email_error}, status=400)
            if data['email'] != user.email and User.objects.filter(email=data['email']).exists():
                return JsonResponse({'success': False, 'error': 'Email already exists'}, status=400)
            user.email = data['email']
            user.username = data['email']  # Adjust if username is handled differently

        # Validate password (only if provided)
        if data.get('password'):
            password_error = validate_password(data['password'])
            if password_error:
                return JsonResponse({'success': False, 'error': password_error}, status=400)
            user.set_password(data['password'])

        # Validate role
        if 'role' in data:
            if not data['role']:
                return JsonResponse({'success': False, 'error': 'Role is required'}, status=400)
            user.user_type = data['role']

        user.user_type = data['role']
        user.status = data.get('status', user.status)
        if data.get('password'):
            user.set_password(data['password'])
        user.save()
        update_session_auth_hash(request, user)

        # Replace permissions
        user.permissions.all().delete()
        for perm in data.get('permissions', []):
            UserPermission.objects.create(user=user, module=perm['module'], action=perm['action'])

        return JsonResponse({'success': True})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def has_permission(user, module, action):
    return user.permissions.filter(module=module, action=action).exists()


@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def delete_user(request, user_id):
    if not has_permission(request.user, 'users', 'delete'):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        return JsonResponse({'success': True})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    
