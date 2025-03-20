
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib import messages
from .forms import EmployeeProfileForm, ProfilePictureForm
from .models import Employee, LeaveType, LeaveRequest, LeaveBalance, Holiday, Department
from django.contrib.auth.models import User
from django.db.models import Q
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .forms import RegistrationForm


# Helper function to calculate working days (excluding weekends and holidays)
def calculate_working_days(start_date, end_date, holidays=None):
    if holidays is None:
        holidays = Holiday.objects.filter(date__range=[start_date, end_date]).values_list('date', flat=True)

    working_days = 0
    current_date = start_date
    while current_date <= end_date:
        # If the current date is not a weekend (5=Saturday, 6=Sunday) and not a holiday
        if current_date.weekday() < 5 and current_date not in holidays:
            working_days += 1
        current_date += timedelta(days=1)

    return working_days


@login_required
def dashboard(request):
    try:
        employee = Employee.objects.get(user=request.user)
        leave_balances = LeaveBalance.objects.filter(employee=employee, year=datetime.now().year)
        recent_leaves = LeaveRequest.objects.filter(employee=employee).order_by('-applied_on')[:5]

        # For managers, get count of pending approvals
        pending_approvals_count = 0
        if request.user.is_staff or Employee.objects.filter(manager=employee).exists():
            pending_approvals_count = LeaveRequest.objects.filter(
                employee__manager=employee,
                status='pending'
            ).count()

        context = {
            'employee': employee,
            'leave_balances': leave_balances,
            'recent_leaves': recent_leaves,
            'pending_approvals_count': pending_approvals_count,
        }
        return render(request, 'leavemanagement/dashboard.html', context)
    except Employee.DoesNotExist:
        # If the user doesn't have an employee record and is staff/admin
        if request.user.is_staff:
            # Calculate stats for admin dashboard
            user_count = User.objects.count()
            department_count = Department.objects.count()
            pending_count = LeaveRequest.objects.filter(status='pending').count()
            leave_count = LeaveRequest.objects.count()

            context = {
                'user_count': user_count,
                'department_count': department_count,
                'pending_count': pending_count,
                'leave_count': leave_count,
            }

            # Show a special admin dashboard with stats
            return render(request, 'leavemanagement/admin_dashboard.html', context)
        else:
            # Show a message that the employee profile needs to be created
            messages.warning(request, "Your employee profile hasn't been set up yet. Please contact an administrator.")
            return render(request, 'leavemanagement/incomplete_profile.html')


@login_required
def apply_leave(request):
    try:
        employee = Employee.objects.get(user=request.user)
        leave_types = LeaveType.objects.all()
        leave_balances = LeaveBalance.objects.filter(employee=employee, year=datetime.now().year)

        # Get upcoming holidays for the next 30 days
        today = timezone.now().date()
        upcoming_holidays = Holiday.objects.filter(
            date__gte=today,
            date__lte=today + timedelta(days=30)
        ).order_by('date')

        if request.method == 'POST':
            leave_type_id = request.POST.get('leave_type')
            start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
            requested_days = int(request.POST.get('requested_days'))
            reason = request.POST.get('reason')

            # Validate dates
            if start_date > end_date:
                messages.error(request, "Start date cannot be after end date.")
                return redirect('leavemanagement:apply_leave')

            if start_date < today:
                messages.error(request, "Cannot apply for leave in the past.")
                return redirect('leavemanagement:apply_leave')

            # Get leave type and check balance
            leave_type = get_object_or_404(LeaveType, id=leave_type_id)
            try:
                balance = LeaveBalance.objects.get(
                    employee=employee,
                    leave_type=leave_type,
                    year=today.year
                )

                if balance.remaining_days() < requested_days:
                    messages.error(request, f"Insufficient leave balance for {leave_type.name}.")
                    return redirect('leavemanagement:apply_leave')

            except LeaveBalance.DoesNotExist:
                messages.error(request, f"No leave balance found for {leave_type.name}.")
                return redirect('leavemanagement:apply_leave')

            # Check for overlapping leave requests
            overlapping_leaves = LeaveRequest.objects.filter(
                employee=employee,
                status__in=['pending', 'approved'],
                start_date__lte=end_date,
                end_date__gte=start_date
            )

            if overlapping_leaves.exists():
                messages.error(request, "You already have leave request(s) that overlap with these dates.")
                return redirect('leavemanagement:apply_leave')

            # Create leave request
            leave_request = LeaveRequest.objects.create(
                employee=employee,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                requested_days=requested_days,
                reason=reason,
                status='pending'
            )

            messages.success(request, "Leave request submitted successfully.")
            return redirect('leavemanagement:my_leaves')

        context = {
            'employee': employee,
            'leave_types': leave_types,
            'leave_balances': leave_balances,
            'upcoming_holidays': upcoming_holidays,
        }
        return render(request, 'leavemanagement/apply_leave.html', context)
    except Employee.DoesNotExist:
        messages.warning(request, "Your employee profile hasn't been set up yet. Please contact an administrator.")
        return redirect('leavemanagement:dashboard')


@login_required
def my_leaves(request):
    try:
        employee = Employee.objects.get(user=request.user)
        leaves = LeaveRequest.objects.filter(employee=employee).order_by('-applied_on')

        context = {
            'leaves': leaves,
        }
        return render(request, 'leavemanagement/my_leaves.html', context)
    except Employee.DoesNotExist:
        messages.warning(request, "Your employee profile hasn't been set up yet. Please contact an administrator.")
        return redirect('leavemanagement:dashboard')


@login_required
def leave_details(request, leave_id):
    try:
        # First check if the user has an employee record
        employee = None
        if not request.user.is_staff:
            try:
                employee = Employee.objects.get(user=request.user)
            except Employee.DoesNotExist:
                messages.warning(request,
                                 "Your employee profile hasn't been set up yet. Please contact an administrator.")
                return redirect('leavemanagement:dashboard')

        leave = get_object_or_404(LeaveRequest, id=leave_id)

        # Security check - only allow view if it's the user's own leave, they are the manager, or they are admin
        if not request.user.is_staff and (
                employee != leave.employee and
                (not hasattr(leave.employee, 'manager') or leave.employee.manager != employee)
        ):
            messages.error(request, "You do not have permission to view this leave request.")
            return redirect('leavemanagement:my_leaves')

        # Get employee leave history
        employee_leave_history = LeaveRequest.objects.filter(
            employee=leave.employee
        ).exclude(id=leave_id).order_by('-applied_on')[:5]

        # Get employee leave balance
        employee_leave_balance = LeaveBalance.objects.filter(
            employee=leave.employee,
            year=datetime.now().year
        )

        context = {
            'leave': leave,
            'employee_leave_history': employee_leave_history,
            'employee_leave_balance': employee_leave_balance,
        }
        return render(request, 'leavemanagement/leave_details.html', context)
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('leavemanagement:dashboard')


@login_required
def cancel_leave(request, leave_id):
    try:
        # Check if user has an employee record
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            messages.warning(request, "Your employee profile hasn't been set up yet. Please contact an administrator.")
            return redirect('leavemanagement:dashboard')

        leave = get_object_or_404(LeaveRequest, id=leave_id)

        # Security check - only the employee who applied can cancel
        if leave.employee.user != request.user:
            return HttpResponseForbidden("You don't have permission to cancel this leave.")

        # Only pending leaves can be cancelled
        if leave.status != 'pending':
            messages.error(request, "Only pending leave requests can be cancelled.")
            return redirect('leavemanagement:my_leaves')

        if request.method == 'POST':
            leave.status = 'cancelled'
            leave.save()
            messages.success(request, "Leave request cancelled successfully.")

        return redirect('leavemanagement:my_leaves')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('leavemanagement:dashboard')


@login_required
def pending_leaves(request):
    try:
        # Check if user is a manager or admin
        is_manager = False

        try:
            employee = Employee.objects.get(user=request.user)
            # Check if any employees report to this employee
            is_manager = Employee.objects.filter(manager=employee).exists()
        except Employee.DoesNotExist:
            # If admin but no employee record
            if request.user.is_staff:
                is_manager = False  # No manager role, but still will show pending as admin
            else:
                messages.warning(request,
                                 "Your employee profile hasn't been set up yet. Please contact an administrator.")
                return redirect('leavemanagement:dashboard')

        if is_manager or request.user.is_staff:
            # If admin, show all pending requests
            if request.user.is_staff:
                pending_requests = LeaveRequest.objects.filter(status='pending').order_by('-applied_on')
            else:
                # If manager, show only subordinates' requests
                pending_requests = LeaveRequest.objects.filter(
                    status='pending',
                    employee__manager=employee
                ).order_by('-applied_on')

            context = {
                'pending_requests': pending_requests,
            }
            return render(request, 'leavemanagement/pending_leaves.html', context)
        else:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('leavemanagement:dashboard')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('leavemanagement:dashboard')


# @login_required
# def approve_leave(request, leave_id):
#     try:
#         # Check if user has an employee record
#         if not request.user.is_staff:
#             try:
#                 employee = Employee.objects.get(user=request.user)
#             except Employee.DoesNotExist:
#                 messages.warning(request,
#                                  "Your employee profile hasn't been set up yet. Please contact an administrator.")
#                 return redirect('leavemanagement:dashboard')
#
#         leave = get_object_or_404(LeaveRequest, id=leave_id, status='pending')
#
#         # Security check - only manager or admin can approve
#         if not request.user.is_staff:
#             if leave.employee.manager != employee:
#                 return HttpResponseForbidden("You don't have permission to approve this leave.")
#
#         if request.method == 'POST':
#             comments = request.POST.get('comments', '')
#
#             # Update leave request
#             leave.status = 'approved'
#
#             # Only set approved_by if employee record exists for current user
#             try:
#                 approver = Employee.objects.get(user=request.user)
#                 leave.approved_by = approver
#             except Employee.DoesNotExist:
#                 # Admin without employee record can still approve
#                 pass
#
#             leave.comments = comments
#             leave.save()
#
#             # Update leave balance
#             try:
#                 balance = LeaveBalance.objects.get(
#                     employee=leave.employee,
#                     leave_type=leave.leave_type,
#                     year=leave.start_date.year
#                 )
#                 balance.used_days += leave.requested_days
#                 balance.save()
#             except LeaveBalance.DoesNotExist:
#                 # If no balance exists, just ignore the update
#                 pass
#
#             messages.success(request, f"Leave request for {leave.employee.user.get_full_name()} has been approved.")
#
#         return redirect('leavemanagement:pending_leaves')
#     except Exception as e:
#         messages.error(request, f"An error occurred: {str(e)}")
#         return redirect('leavemanagement:dashboard')
#


@login_required
def approve_leave(request, leave_id):
    try:
        # Check if user has an employee record
        if not request.user.is_staff:
            try:
                employee = Employee.objects.get(user=request.user)
            except Employee.DoesNotExist:
                messages.warning(request,
                                 "Your employee profile hasn't been set up yet. Please contact an administrator.")
                return redirect('leavemanagement:dashboard')

        leave = get_object_or_404(LeaveRequest, id=leave_id, status='pending')

        # Security check - only manager or admin can approve
        if not request.user.is_staff:
            if leave.employee.manager != employee:
                return HttpResponseForbidden("You don't have permission to approve this leave.")

        if request.method == 'POST':
            comments = request.POST.get('comments', '')

            # Update leave request
            leave.status = 'approved'

            # Only set approved_by if employee record exists for current user
            try:
                approver = Employee.objects.get(user=request.user)
                leave.approved_by = approver
            except Employee.DoesNotExist:
                # Admin without employee record can still approve
                pass

            leave.comments = comments
            leave.save()

            # Update leave balance
            try:
                balance = LeaveBalance.objects.get(
                    employee=leave.employee,
                    leave_type=leave.leave_type,
                    year=leave.start_date.year
                )
                balance.used_days += leave.requested_days
                balance.save()
            except LeaveBalance.DoesNotExist:
                # If no balance exists, just ignore the update
                pass

            # Send email notification
            try:
                from .utils import send_leave_status_email
                send_leave_status_email(leave, status_changed_by=request.user)
            except Exception as e:
                # Log the error but don't prevent leave approval
                print(f"Error sending leave approval email: {str(e)}")

            messages.success(request, f"Leave request for {leave.employee.user.get_full_name()} has been approved.")

        return redirect('leavemanagement:pending_leaves')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('leavemanagement:dashboard')


@login_required
def reject_leave(request, leave_id):
    try:
        # Check if user has an employee record
        if not request.user.is_staff:
            try:
                employee = Employee.objects.get(user=request.user)
            except Employee.DoesNotExist:
                messages.warning(request,
                                 "Your employee profile hasn't been set up yet. Please contact an administrator.")
                return redirect('leavemanagement:dashboard')

        leave = get_object_or_404(LeaveRequest, id=leave_id, status='pending')

        # Security check - only manager or admin can reject
        if not request.user.is_staff:
            if leave.employee.manager != employee:
                return HttpResponseForbidden("You don't have permission to reject this leave.")

        if request.method == 'POST':
            comments = request.POST.get('comments', '')

            # Update leave request
            leave.status = 'rejected'

            # Only set approved_by if employee record exists for current user
            try:
                reviewer = Employee.objects.get(user=request.user)
                leave.approved_by = reviewer  # Using the same field to track who rejected
            except Employee.DoesNotExist:
                # Admin without employee record can still reject
                pass

            leave.comments = comments
            leave.save()

            # Send email notification
            try:
                from .utils import send_leave_status_email
                send_leave_status_email(leave, status_changed_by=request.user)
            except Exception as e:
                # Log the error but don't prevent leave rejection
                print(f"Error sending leave rejection email: {str(e)}")

            messages.success(request, f"Leave request for {leave.employee.user.get_full_name()} has been rejected.")

        return redirect('leavemanagement:pending_leaves')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('leavemanagement:dashboard')


@login_required
def employees_list(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    # Get search parameter
    search_query = request.GET.get('search', '')

    # Base query
    employees = Employee.objects.all().select_related('user', 'department', 'manager')

    # Apply search filter if provided
    if search_query:
        employees = employees.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(position__icontains=search_query) |
            Q(department__name__icontains=search_query)
        )

    # Get department statistics
    from django.db.models import Count
    departments = Department.objects.annotate(employee_count=Count('employee'))

    # Get managers count
    managers_count = Employee.objects.exclude(employee=None).distinct().count()

    # Get recent employees (joined in the last 30 days)
    recent_employees = Employee.objects.filter(
        date_joined__gte=datetime.now().date() - timedelta(days=30)
    ).order_by('-date_joined')[:5]

    context = {
        'employees': employees,
        'departments': departments,
        'managers_count': managers_count,
        'recent_employees': recent_employees,
        'search_query': search_query,
    }
    return render(request, 'leavemanagement/employees_list.html', context)


@login_required
def add_employee(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    departments = Department.objects.all()
    managers = Employee.objects.all()

    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        employee_id = request.POST.get('employee_id')
        department_id = request.POST.get('department')
        position = request.POST.get('position')
        manager_id = request.POST.get('manager')

        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Get department and manager
            department = Department.objects.get(id=department_id) if department_id else None
            manager = Employee.objects.get(id=manager_id) if manager_id else None

            # Create employee
            employee = Employee.objects.create(
                user=user,
                employee_id=employee_id,
                department=department,
                position=position,
                manager=manager
            )

            # Create leave balances for this employee for all leave types
            current_year = datetime.now().year
            for leave_type in LeaveType.objects.all():
                LeaveBalance.objects.create(
                    employee=employee,
                    leave_type=leave_type,
                    allocated_days=leave_type.default_days,
                    year=current_year
                )

            messages.success(request, f"Employee {first_name} {last_name} created successfully.")
            return redirect('leavemanagement:employees_list')
        except Exception as e:
            messages.error(request, f"Error creating employee: {str(e)}")

    context = {
        'departments': departments,
        'managers': managers,
    }
    return render(request, 'leavemanagement/add_employee.html', context)



@login_required
def leaves_report(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    # Get filter parameters
    department_id = request.GET.get('department')
    leave_type_id = request.GET.get('leave_type')
    status = request.GET.get('status')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # Base query
    leaves = LeaveRequest.objects.all().select_related(
        'employee', 'employee__user', 'employee__department', 'leave_type'
    )

    # Apply filters
    if department_id:
        leaves = leaves.filter(employee__department_id=department_id)

    if leave_type_id:
        leaves = leaves.filter(leave_type_id=leave_type_id)

    if status:
        leaves = leaves.filter(status=status)

    if from_date:
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        leaves = leaves.filter(start_date__gte=from_date)

    if to_date:
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        leaves = leaves.filter(end_date__lte=to_date)

    # Count leaves by status
    total_leaves = leaves.count()
    pending_count = leaves.filter(status='pending').count()
    approved_count = leaves.filter(status='approved').count()
    rejected_count = leaves.filter(status='rejected').count()

    # Get departments and leave types for filter dropdowns
    departments = Department.objects.all()
    leave_types = LeaveType.objects.all()

    context = {
        'leaves': leaves,
        'departments': departments,
        'leave_types': leave_types,
        'selected_department': department_id,
        'selected_leave_type': leave_type_id,
        'selected_status': status,
        'from_date': from_date,
        'to_date': to_date,
        'total_leaves': total_leaves,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'leavemanagement/leaves_report.html', context)


@login_required
def add_leave_type(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    leave_types = LeaveType.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        default_days = int(request.POST.get('default_days', 0))
        is_paid = request.POST.get('is_paid') == 'on'

        # Create or update leave type
        leave_type_id = request.POST.get('leave_type_id')
        if leave_type_id:
            # Update existing
            leave_type = get_object_or_404(LeaveType, id=leave_type_id)
            leave_type.name = name
            leave_type.description = description
            leave_type.default_days = default_days
            leave_type.is_paid = is_paid
            leave_type.save()
            messages.success(request, f"Leave type '{name}' updated successfully.")
        else:
            # Create new
            LeaveType.objects.create(
                name=name,
                description=description,
                default_days=default_days,
                is_paid=is_paid
            )
            messages.success(request, f"Leave type '{name}' created successfully.")

        return redirect('leavemanagement:add_leave_type')

    context = {
        'leave_types': leave_types,
    }
    return render(request, 'leavemanagement/add_leave_type.html', context)


@login_required
def edit_leave_type(request, type_id):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    leave_type = get_object_or_404(LeaveType, id=type_id)

    context = {
        'leave_type': leave_type,
    }
    return render(request, 'leavemanagement/edit_leave_type.html', context)


@login_required
def delete_leave_type(request, type_id):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    leave_type = get_object_or_404(LeaveType, id=type_id)

    if request.method == 'POST':
        # Check if any leave requests use this type
        if LeaveRequest.objects.filter(leave_type=leave_type).exists():
            messages.error(request, f"Cannot delete '{leave_type.name}' as it has associated leave requests.")
        else:
            leave_type.delete()
            messages.success(request, f"Leave type '{leave_type.name}' deleted successfully.")

    return redirect('leavemanagement:add_leave_type')


@login_required
def add_holiday(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    holidays = Holiday.objects.all().order_by('date')

    # Calculate summary statistics
    total_holidays = holidays.count()

    # Count holidays in first half (Jan-Jun) and second half (Jul-Dec) of the year
    first_half_count = holidays.filter(date__month__lte=6).count()
    second_half_count = holidays.filter(date__month__gt=6).count()

    if request.method == 'POST':
        name = request.POST.get('name')
        date = request.POST.get('date')
        description = request.POST.get('description')

        date_obj = datetime.strptime(date, '%Y-%m-%d').date()

        # Create or update holiday
        holiday_id = request.POST.get('holiday_id')
        if holiday_id:
            # Update existing
            holiday = get_object_or_404(Holiday, id=holiday_id)
            holiday.name = name
            holiday.date = date_obj
            holiday.description = description
            holiday.save()
            messages.success(request, f"Holiday '{name}' updated successfully.")
        else:
            # Create new
            Holiday.objects.create(
                name=name,
                date=date_obj,
                description=description
            )
            messages.success(request, f"Holiday '{name}' created successfully.")

        return redirect('leavemanagement:add_holiday')

    context = {
        'holidays': holidays,
        'total_holidays': total_holidays,
        'first_half_count': first_half_count,
        'second_half_count': second_half_count,
    }
    return render(request, 'leavemanagement/add_holiday.html', context)


@login_required
def delete_holiday(request, holiday_id):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    holiday = get_object_or_404(Holiday, id=holiday_id)

    if request.method == 'POST':
        holiday_name = holiday.name
        holiday.delete()
        messages.success(request, f"Holiday '{holiday_name}' deleted successfully.")

    return redirect('leavemanagement:add_holiday')


# @login_required
# def create_profile(request):
#     """Allow users to create their own employee profile."""
#     # Print debug information
#     print("Creating profile view called")
#     print(f"Request method: {request.method}")
#
#     # Check if user already has an employee profile
#     try:
#         employee = Employee.objects.get(user=request.user)
#         messages.info(request, "You already have an employee profile.")
#         return redirect('leavemanagement:dashboard')
#     except Employee.DoesNotExist:
#         print("No employee profile found, continuing...")
#
#     # Check if there are any departments
#     departments = Department.objects.all()
#     if not departments.exists():
#         # Create a default department if none exists
#         print("No departments found, creating default department")
#         department = Department.objects.create(name="General", description="Default Department")
#         departments = Department.objects.all()
#
#     managers = Employee.objects.filter(user__is_staff=True)
#
#     if request.method == 'POST':
#         print("POST request received")
#         print(f"POST data: {request.POST}")
#
#         # Get form data
#         employee_id = request.POST.get('employee_id')
#         department_id = request.POST.get('department')
#         position = request.POST.get('position')
#         phone_number = request.POST.get('phone_number', '')
#         date_joined = request.POST.get('date_joined')
#         manager_id = request.POST.get('manager', None)
#
#         # Validate the data is present
#         if not employee_id or not department_id or not position:
#             print("Missing required fields")
#             messages.error(request, "Please fill out all required fields.")
#             return render(request, 'leavemanagement/create_profile.html', {
#                 'departments': departments,
#                 'managers': managers
#             })
#
#         # Validate employee_id is unique
#         if Employee.objects.filter(employee_id=employee_id).exists():
#             print(f"Employee ID {employee_id} already exists")
#             messages.error(request, "This Employee ID is already in use. Please use a different one.")
#             return render(request, 'leavemanagement/create_profile.html', {
#                 'departments': departments,
#                 'managers': managers
#             })
#
#         try:
#             # Get department
#             department = None
#             if department_id:
#                 try:
#                     department = Department.objects.get(id=department_id)
#                     print(f"Found department: {department}")
#                 except Department.DoesNotExist:
#                     print(f"Department with ID {department_id} not found")
#                     messages.error(request, "Selected department does not exist.")
#                     return render(request, 'leavemanagement/create_profile.html', {
#                         'departments': departments,
#                         'managers': managers
#                     })
#
#             # Get manager if provided
#             manager = None
#             if manager_id:
#                 try:
#                     manager = Employee.objects.get(id=manager_id)
#                     print(f"Found manager: {manager}")
#                 except Employee.DoesNotExist:
#                     print(f"Manager with ID {manager_id} not found")
#                     # Not blocking, just informing
#                     messages.warning(request, "Selected manager does not exist. Profile created without manager.")
#
#             # Convert date_joined to date object
#             try:
#                 date_joined_obj = datetime.strptime(date_joined,
#                                                     "%Y-%m-%d").date() if date_joined else datetime.now().date()
#                 print(f"Date joined: {date_joined_obj}")
#             except ValueError:
#                 print(f"Invalid date format: {date_joined}")
#                 messages.error(request, "Invalid date format. Please use YYYY-MM-DD format.")
#                 return render(request, 'leavemanagement/create_profile.html', {
#                     'departments': departments,
#                     'managers': managers
#                 })
#
#             # Create employee record
#             employee = Employee.objects.create(
#                 user=request.user,
#                 employee_id=employee_id,
#                 department=department,
#                 position=position,
#                 phone_number=phone_number,
#                 date_joined=date_joined_obj,
#                 manager=manager
#             )
#             print(f"Employee created: {employee}")
#
#             # Create leave balances for this employee for all leave types
#             current_year = datetime.now().year
#             leave_types = LeaveType.objects.all()
#
#             # Create a default leave type if none exists
#             if not leave_types.exists():
#                 print("No leave types found, creating default leave types")
#                 LeaveType.objects.create(
#                     name="Annual Leave",
#                     description="Regular annual vacation leave",
#                     default_days=20,
#                     is_paid=True
#                 )
#                 LeaveType.objects.create(
#                     name="Sick Leave",
#                     description="Leave for medical reasons",
#                     default_days=10,
#                     is_paid=True
#                 )
#                 leave_types = LeaveType.objects.all()
#
#             # Create leave balances
#             for leave_type in leave_types:
#                 LeaveBalance.objects.create(
#                     employee=employee,
#                     leave_type=leave_type,
#                     allocated_days=leave_type.default_days,
#                     year=current_year
#                 )
#                 print(f"Created leave balance for {leave_type.name}")
#
#             messages.success(request, "Your employee profile has been created successfully!")
#             print("Profile creation successful, redirecting to dashboard")
#             return redirect('leavemanagement:dashboard')
#
#         except Exception as e:
#             print(f"Error creating profile: {str(e)}")
#             messages.error(request, f"Error creating profile: {str(e)}")
#
#     print("Rendering create_profile template")
#     context = {
#         'departments': departments,
#         'managers': managers
#     }
#
#     return render(request, 'leavemanagement/create_profile.html', context)
#
#
# class RegistrationForm(UserCreationForm):
#     first_name = forms.CharField(max_length=30, required=True)
#     last_name = forms.CharField(max_length=30, required=True)
#     email = forms.EmailField(max_length=254, required=True)
#
#     class Meta:
#         model = User
#         fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')



@login_required
def create_profile(request):
    """Allow users to create their own employee profile."""
    # Check if user already has an employee profile
    try:
        employee = Employee.objects.get(user=request.user)
        messages.info(request, "You already have an employee profile.")
        return redirect('leavemanagement:dashboard')
    except Employee.DoesNotExist:
        pass

    # Check if there are any departments
    departments = Department.objects.all()
    if not departments.exists():
        # Create a default department if none exists
        department = Department.objects.create(name="General", description="Default Department")
        departments = Department.objects.all()

    managers = Employee.objects.filter(user__is_staff=True)

    if request.method == 'POST':
        # Get form data
        employee_id = request.POST.get('employee_id')
        department_id = request.POST.get('department')
        position = request.POST.get('position')
        phone_number = request.POST.get('phone_number', '')
        date_joined = request.POST.get('date_joined')
        manager_id = request.POST.get('manager', None)

        # Validate the data is present
        if not employee_id or not department_id or not position:
            messages.error(request, "Please fill out all required fields.")
            return render(request, 'leavemanagement/create_profile.html', {
                'departments': departments,
                'managers': managers
            })

        # Validate employee_id is unique
        if Employee.objects.filter(employee_id=employee_id).exists():
            messages.error(request, "This Employee ID is already in use. Please use a different one.")
            return render(request, 'leavemanagement/create_profile.html', {
                'departments': departments,
                'managers': managers
            })

        try:
            # Get department
            department = None
            if department_id:
                try:
                    department = Department.objects.get(id=department_id)
                except Department.DoesNotExist:
                    messages.error(request, "Selected department does not exist.")
                    return render(request, 'leavemanagement/create_profile.html', {
                        'departments': departments,
                        'managers': managers
                    })

            # Get manager if provided
            manager = None
            if manager_id:
                try:
                    manager = Employee.objects.get(id=manager_id)
                except Employee.DoesNotExist:
                    # Not blocking, just informing
                    messages.warning(request, "Selected manager does not exist. Profile created without manager.")

            # Convert date_joined to date object
            try:
                date_joined_obj = datetime.strptime(date_joined,
                                                    "%Y-%m-%d").date() if date_joined else datetime.now().date()
            except ValueError:
                messages.error(request, "Invalid date format. Please use YYYY-MM-DD format.")
                return render(request, 'leavemanagement/create_profile.html', {
                    'departments': departments,
                    'managers': managers
                })

            # Create employee record
            employee = Employee.objects.create(
                user=request.user,
                employee_id=employee_id,
                department=department,
                position=position,
                phone_number=phone_number,
                date_joined=date_joined_obj,
                manager=manager
            )

            # Create leave balances for this employee for all leave types
            current_year = datetime.now().year
            leave_types = LeaveType.objects.all()

            # Create a default leave type if none exists
            if not leave_types.exists():
                LeaveType.objects.create(
                    name="Annual Leave",
                    description="Regular annual vacation leave",
                    default_days=20,
                    is_paid=True
                )
                LeaveType.objects.create(
                    name="Sick Leave",
                    description="Leave for medical reasons",
                    default_days=10,
                    is_paid=True
                )
                leave_types = LeaveType.objects.all()

            # Create leave balances
            for leave_type in leave_types:
                LeaveBalance.objects.create(
                    employee=employee,
                    leave_type=leave_type,
                    allocated_days=leave_type.default_days,
                    year=current_year
                )

            # Send welcome email notification
            from .utils import send_profile_creation_email
            try:
                send_profile_creation_email(request.user)
            except Exception as e:
                # Log the error but don't prevent account creation
                print(f"Error sending welcome email: {str(e)}")

            messages.success(request, "Your employee profile has been created successfully!")
            return redirect('leavemanagement:dashboard')

        except Exception as e:
            messages.error(request, f"Error creating profile: {str(e)}")

    context = {
        'departments': departments,
        'managers': managers
    }

    return render(request, 'leavemanagement/create_profile.html', context)



def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


# In views.py
@login_required
@login_required
def edit_profile(request):
    try:
        employee = Employee.objects.get(user=request.user)

        if request.method == 'POST':
            form = EmployeeProfileForm(request.POST, request.FILES, instance=employee)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('leavemanagement:dashboard')
        else:
            form = EmployeeProfileForm(instance=employee)

        return render(request, 'leavemanagement/edit_profile.html', {'form': form, 'employee': employee})
    except Employee.DoesNotExist:
        messages.error(request, "Employee profile not found.")
        return redirect('leavemanagement:dashboard')


@login_required
def update_profile_picture(request):
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user.employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile picture updated successfully!")
            return redirect('leavemanagement:dashboard')
    else:
        form = ProfilePictureForm(instance=request.user.employee)

    return render(request, 'leavemanagement/update_profile_picture.html', {'form': form})


# Add these functions to your existing views.py file

@login_required
def employees_list(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    # Get search parameter
    search_query = request.GET.get('search', '')

    # Base query
    employees = Employee.objects.all().select_related('user', 'department', 'manager')

    # Apply search filter if provided
    if search_query:
        employees = employees.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(position__icontains=search_query) |
            Q(department__name__icontains=search_query)
        )

    # Get departments and managers for the form
    departments = Department.objects.all()
    managers = Employee.objects.all()

    context = {
        'employees': employees,
        'departments': departments,
        'managers': managers,
        'search_query': search_query,
    }
    return render(request, 'leavemanagement/employees_list.html', context)


@login_required
def edit_employee(request, employee_id):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    employee = get_object_or_404(Employee, id=employee_id)
    departments = Department.objects.all()
    managers = Employee.objects.exclude(id=employee_id)  # Exclude self from managers list

    if request.method == 'POST':
        try:
            # Update user info
            user = employee.user
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('email')

            # Update password if provided
            password = request.POST.get('password')
            if password:
                user.set_password(password)

            user.save()

            # Update employee info
            employee.employee_id = request.POST.get('employee_id')

            department_id = request.POST.get('department')
            employee.department = get_object_or_404(Department, id=department_id) if department_id else None

            employee.position = request.POST.get('position')

            manager_id = request.POST.get('manager')
            employee.manager = get_object_or_404(Employee, id=manager_id) if manager_id else None

            employee.phone_number = request.POST.get('phone_number', '')

            date_joined = request.POST.get('date_joined')
            if date_joined:
                employee.date_joined = datetime.strptime(date_joined, '%Y-%m-%d').date()

            employee.save()

            messages.success(request, f"Employee {user.get_full_name()} updated successfully.")
            return redirect('leavemanagement:employees_list')
        except Exception as e:
            messages.error(request, f"Error updating employee: {str(e)}")

    context = {
        'employee': employee,
        'departments': departments,
        'managers': managers,
    }
    return render(request, 'leavemanagement/edit_employee.html', context)


@login_required
def delete_employee(request, employee_id):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('leavemanagement:dashboard')

    employee = get_object_or_404(Employee, id=employee_id)

    if request.method == 'POST':
        try:
            user = employee.user
            employee_name = user.get_full_name()

            # Delete the employee record
            employee.delete()

            # Delete the user account
            user.delete()

            messages.success(request, f"Employee {employee_name} deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting employee: {str(e)}")

    return redirect('leavemanagement:employees_list')

