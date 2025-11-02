from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.db.models import Q
import json
import pandas as pd
from io import BytesIO


from accounts.utils import get_permissions
from django.contrib.auth import get_user_model
from accounts.models import UserPermission
from .models import Seat, SeatCSVUpload, BadgeTemplate
from .tasks import process_seat_csv_upload



@login_required
def dashboard(request):
    print('request...user', request.user)
    user_permissions = get_permissions(request.user)
    
    context = {
        'total_seats': 250,
        'assigned_seats': 187,
        'printed_badges': 142,
        'available_seats': 63,
        'permissions':  user_permissions
    }
    return render(request, 'dashboard.html', context)


@login_required
def manage_seat(request):
    print('request...user', request.user)
    user_permissions = get_permissions(request.user)

    seats = Seat.objects.all().select_related().order_by('seat_no')
    context = {
        'seats': seats,
        'permissions':  user_permissions.get('seats', [])
    } 
    return render(request, 'manage-seat.html', context)



@login_required
@require_POST
@csrf_exempt
def add_seat(request):
    user_permissions = get_permissions(request.user)
    if 'create' not in user_permissions.get('seats', []):
        return JsonResponse({'success': False, 'error': 'No create permission for seats'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        seat = Seat(
            seat_no=data.get('seat_no', '').strip().upper(),
            name=data.get('name', '').strip(),
            email=data.get('email', '').strip(),
            company=data.get('company', '').strip(),
            phone=data.get('phone', '').strip(),
            gender=data.get('gender', ''),
            print_status=Seat.PrintStatus.NOT_PRINTED
        )
        
        seat.full_clean()  
        seat.save()

        return JsonResponse({
            'success': True,
            'seat': {
                'id': seat.id,
                'seat_no': seat.seat_no,
                'name': seat.name,
                'email': seat.email,
                'company': seat.company or '—',
                'phone': seat.phone or '—',
                'gender': seat.get_gender_display(),
                'print_status': seat.print_status,
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    

@login_required
@require_POST
@csrf_exempt
def edit_seat(request):
    user_permissions = get_permissions(request.user)
    if 'edit' not in user_permissions.get('seats', []):
        return JsonResponse({'success': False, 'error': 'No edit permission for seats'}, status=403)
    
    try:
        data = json.loads(request.body)
        seat_id = data.get('id')
        seat = get_object_or_404(Seat, id=seat_id)

        seat.seat_no = data.get('seat_no', seat.seat_no).upper().strip()
        seat.name = data.get('name', seat.name)
        seat.email = data.get('email', seat.email)
        seat.company = data.get('company', seat.company) or ''  # Allow empty
        seat.phone = data.get('phone', seat.phone) or ''        # Allow empty
        seat.gender = data.get('gender', seat.gender)
        seat.print_status = data.get('print_status', seat.print_status)  # ADD THIS

        seat.full_clean()
        seat.save()

        return JsonResponse({
            'success': True,
            'seat': {
                'id': seat.id,
                'seat_no': seat.seat_no,
                'name': seat.name,
                'email': seat.email,
                'company': seat.company,
                'phone': seat.phone,
                'gender': seat.get_gender_display(),
                'print_status': seat.print_status,
                'get_gender_display': seat.get_gender_display(),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def print_badge(request):
    user_permissions = get_permissions(request.user)
    has_print_permission = True if 'print' in user_permissions.get('badges',[]) else False
    return render(request, 'scan-print.html', {'permissions': user_permissions.get('badges',[]),'has_print_permission':has_print_permission})

@login_required
def user_management(request):
    user_permissions = get_permissions(request.user)
    return render(request, 'user-management.html',{'permissions': user_permissions.get('users',[])})

@login_required
def badge_alignment(request):
    user_permissions = get_permissions(request.user)
    return render(request, 'badge-alignment.html', {'permissions': user_permissions.get('alignment',[])})

@require_POST
@csrf_exempt
def print_seat(request):
    """Mark seat as printed via AJAX."""
    try:
        data = json.loads(request.body)
        seat_id = data.get('id')
        seat = get_object_or_404(Seat, id=seat_id)
        
        seat.print_status = Seat.PrintStatus.PRINTED
        seat.save(update_fields=['print_status'])

        return JsonResponse({
            'success': True,
            'message': 'Badge printed successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
@csrf_exempt
def reprint_seat(request):
    """Reprint (same as print, but logs action)"""
    return print_seat(request)  # Same logic


@login_required
@require_POST
@csrf_exempt
def delete_seat(request):
    """Delete a seat."""
    try:
        data = json.loads(request.body)
        seat_id = data.get('id')
        seat = get_object_or_404(Seat, id=seat_id)
        seat.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)





@login_required
@csrf_exempt
@require_http_methods(["POST"])
def bulk_upload_seats(request):
    """
    Unified endpoint for CSV/Excel upload.
    - Small files: processed immediately
    - Large files: offloaded to Celery
    """
    user_permissions = get_permissions(request.user)
    # Use 'upload' if you added it, else 'create'
    if 'upload' not in user_permissions.get('seats', []) and 'create' not in user_permissions.get('seats', []):
        return JsonResponse({'success': False, 'error': 'No upload/create permission for seats'}, status=403)
        
    csv_file = request.FILES.get('file')  # <-- matches <input name="file">
    is_large_file = request.POST.get('isLargeFile', 'false').lower() == 'true'

    if not csv_file:
        return JsonResponse({'success': False, 'error': 'Missing file'}, status=400)

    # Save upload record
    csv_upload = SeatCSVUpload.objects.create(
        file=csv_file,
        status='processing',
        processed=False
    )

    if is_large_file:
        # Offload to Celery
        process_seat_csv_upload.delay(csv_upload.id)
        return JsonResponse({
            'success': True,
            'message': 'Large file is being processed in the background.',
            'csv_upload_id': csv_upload.id,
            'check_status_url': f"/manage-seat/api/upload-status/{csv_upload.id}/"
        })

    else:
        # Process immediately
        result = process_seat_csv_upload(csv_upload.id)
        return JsonResponse(result)


# views.py
@login_required
def upload_status(request, upload_id):
    try:
        upload = SeatCSVUpload.objects.get(id=upload_id)
        if upload.processed:
            return JsonResponse({
                'status': 'completed',
                'result': {
                    'added': upload.added or 0,
                    'updated': upload.updated or 0,
                    'failed': upload.failed or 0,
                    'errors': upload.errors or []
                }
            })
        else:
            return JsonResponse({
                'status': upload.status,
                'processed_rows': upload.processed_rows or 0
            })
    except SeatCSVUpload.DoesNotExist:
        return JsonResponse({'status': 'not_found'}, status=404)



@login_required
def download_sample(request):
    data = {
        'seat_no': ['SEAT-101', 'SEAT-102'],
        'name': ['John Doe', 'Jane Smith'],
        'email': ['john@example.com', 'jane@example.com'],
        'company': ['TechCorp', 'DesignHub'],
        'phone': ['+1234567890', '+0987654321'],
        'gender': ['male', 'female']
    }
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Seats')
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=sample_seats.xlsx'
    return response



@require_http_methods(["GET"])
def search_seats(request):
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    # Search across name, email, company, phone
    seats = Seat.objects.filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(company__icontains=query) |
        Q(phone__icontains=query)
    ).values('id', 'seat_no', 'name', 'email', 'company', 'phone', 'print_status')[:10]

    results = [
        {
            'id': s['id'],
            'seat_no': s['seat_no'],
            'name': s['name'],
            'email': s['email'],
            'company': s['company'] or '',
            'phone': s['phone'] or '',
            'print_status': s['print_status'],
            'print_status_display': s['print_status'] == 'printed' and 'Printed' or 'Not Printed'
        }
        for s in seats
    ]
    return JsonResponse({'results': results})


@require_http_methods(["POST"])
@login_required
def print_seat(request, seat_id):
    try:
        seat = Seat.objects.get(id=seat_id)
        seat.print_status = "printed"
        seat.save()

        return JsonResponse({
            "success": True,
            "seat_no": seat.seat_no,
            "name":    seat.name
        })
    except Seat.DoesNotExist:
        return JsonResponse({"success": False, "error": "Seat not found"}, status=404)
    


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def save_badge_template(request):
    try:
        data = json.loads(request.body)
        template = BadgeTemplate.objects.order_by('-created_at').first()

        if not template:
            template = BadgeTemplate(created_by=request.user)
        else:
            # Don't allow editing others' templates unless admin
            if template.created_by != request.user and not request.user.is_staff:
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        template.name = data.get('name', template.name)
        template.position_x = int(data.get('position_x', template.position_x))
        template.position_y = int(data.get('position_y', template.position_y))
        template.font_size = int(data.get('font_size', template.font_size))
        template.is_bold = data.get('is_bold', template.is_bold)
        template.text_align = data.get('text_align', template.text_align)
        template.page_width_mm = int(data.get('page_width_mm', template.page_width_mm))
        template.page_height_mm = int(data.get('page_height_mm', template.page_height_mm))
        template.created_by = request.user
        template.save()

        return JsonResponse({'success': True, 'id': template.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["GET"])
@login_required
def get_badge_template(request):
    template = BadgeTemplate.objects.order_by('-created_at').first()
    if not template:
        return JsonResponse({'success': False, 'error': 'No template found'})
    return JsonResponse({
        'success': True,
        'template': {
            'position_x': template.position_x,
            'position_y': template.position_y,
            'font_size': template.font_size,
            'is_bold': template.is_bold,
            'text_align': template.text_align,
            'page_width_mm': template.page_width_mm,
            'page_height_mm': template.page_height_mm,
        }
    })



User = get_user_model()

@require_POST
def create_user_api(request):
    data = json.loads(request.body)

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

    return JsonResponse({'success': True, 'user_id': user.id})
    