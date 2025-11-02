from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_page, name='login_page'), 
    path('login/verify/', views.login_view, name='login_view'),  
    path('dashboard/', views.dashboard_view, name='dashboard'), 

    path('users/', views.user_list, name='user_list'),

    path('api/users/', views.list_users, name='list_users'),
    path('api/users/create/', views.create_user, name='create_user'),
    path('api/users/<int:user_id>/update/', views.update_user, name='update_user'),
    path('api/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
]