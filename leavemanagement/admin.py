from django.contrib import admin
from .models import Department, Employee, LeaveType, LeaveBalance, LeaveRequest, Holiday

admin.site.register(Department)
admin.site.register(Employee)
admin.site.register(LeaveType)
admin.site.register(LeaveBalance)
admin.site.register(LeaveRequest)
admin.site.register(Holiday)