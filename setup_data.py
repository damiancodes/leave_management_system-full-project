import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kiriko.settings')
django.setup()

from django.contrib.auth.models import User
from leavemanagement.models import Department, LeaveType, Employee

# Create departments if they don't exist
def create_departments():
    departments = [
        {'name': 'Human Resources', 'description': 'HR Department'},
        {'name': 'Finance', 'description': 'Finance Department'},
        {'name': 'IT', 'description': 'Information Technology Department'},
        {'name': 'Marketing', 'description': 'Marketing Department'},
        {'name': 'Operations', 'description': 'Operations Department'}
    ]
    
    for dept in departments:
        Department.objects.get_or_create(
            name=dept['name'],
            defaults={'description': dept['description']}
        )
    
    print(f"Created {len(departments)} departments")

# Create leave types if they don't exist
def create_leave_types():
    leave_types = [
        {'name': 'Annual Leave', 'description': 'Regular vacation leave', 'default_days': 20, 'is_paid': True},
        {'name': 'Sick Leave', 'description': 'Leave for medical reasons', 'default_days': 10, 'is_paid': True},
        {'name': 'Maternity Leave', 'description': 'Leave for childbirth and care', 'default_days': 90, 'is_paid': True},
        {'name': 'Paternity Leave', 'description': 'Leave for fathers after childbirth', 'default_days': 14, 'is_paid': True},
        {'name': 'Study Leave', 'description': 'Leave for educational purposes', 'default_days': 10, 'is_paid': False}
    ]
    
    for lt in leave_types:
        LeaveType.objects.get_or_create(
            name=lt['name'],
            defaults={
                'description': lt['description'],
                'default_days': lt['default_days'],
                'is_paid': lt['is_paid']
            }
        )
    
    print(f"Created {len(leave_types)} leave types")

if __name__ == "__main__":
    print("Setting up initial data for Leave Management System...")
    create_departments()
    create_leave_types()
    print("Setup complete!")

