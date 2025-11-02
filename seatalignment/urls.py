from django.urls import path
from . import views

app_name = 'seats'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('manage-seat/', views.manage_seat, name='manage_seat'),
    path('api/add/', views.add_seat, name='add_seat'),
    path('api/edit/', views.edit_seat, name='edit_seat'),
    path('api/delete/', views.delete_seat, name='delete_seat'),
    path('api/print/', views.print_seat, name='print_seat'),
    path('api/reprint/', views.reprint_seat, name='reprint_seat'),
    path('print-badge/', views.print_badge, name='print_badge'),
    path('user-management/', views.user_management, name='user_management'),
    path('badge-alignment/', views.badge_alignment, name='badge_alignment'),


    path('api/bulk-upload/', views.bulk_upload_seats, name='bulk_upload_seats'),
    path('api/upload-status/<int:upload_id>/', views.upload_status, name='upload_status'),
    path('download-sample/', views.download_sample, name='download_sample'),

    path('api/search/', views.search_seats, name='search_seats'),

    path("print/<int:seat_id>/", views.print_seat, name="print_seat"),

    # path('badge-alignment/', views.badge_alignment, name='badge_alignment'),
    path('api/save-badge-template/', views.save_badge_template, name='save_badge_template'),
    path('api/get-badge-template/', views.get_badge_template, name='get_badge_template'),
    
]
