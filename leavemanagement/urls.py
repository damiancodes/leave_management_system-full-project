
from django.urls import path
from . import views

app_name = 'leavemanagement'

urlpatterns = [
    # Employee profile creation
    path('create-profile/', views.create_profile, name='create_profile'),

    # Employee views
    path('', views.dashboard, name='dashboard'),
    path('apply-leave/', views.apply_leave, name='apply_leave'),
    path('my-leaves/', views.my_leaves, name='my_leaves'),
    path('leave-details/<int:leave_id>/', views.leave_details, name='leave_details'),
    path('cancel-leave/<int:leave_id>/', views.cancel_leave, name='cancel_leave'),

    # Manager/Admin views
    path('pending-leaves/', views.pending_leaves, name='pending_leaves'),
    path('approve-leave/<int:leave_id>/', views.approve_leave, name='approve_leave'),
    path('reject-leave/<int:leave_id>/', views.reject_leave, name='reject_leave'),

    # Admin only views
    path('employees/', views.employees_list, name='employees_list'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('leaves-report/', views.leaves_report, name='leaves_report'),

    # Leave type management
    path('leave-types/', views.add_leave_type, name='add_leave_type'),
    path('edit-leave-type/<int:type_id>/', views.edit_leave_type, name='edit_leave_type'),
    path('delete-leave-type/<int:type_id>/', views.delete_leave_type, name='delete_leave_type'),


    path('holidays/', views.add_holiday, name='add_holiday'),
    path('delete-holiday/<int:holiday_id>/', views.delete_holiday, name='delete_holiday'),

    path('edit-profile/', views.edit_profile, name='edit_profile'),


   path('edit-employee/<int:employee_id>/', views.edit_employee, name='edit_employee'),
   path('delete-employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
]