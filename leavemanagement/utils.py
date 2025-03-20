from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_profile_creation_email(user):
    """Send an email notification when a user profile is created"""
    subject = 'Welcome to Leave Management System'
    html_message = render_to_string('leavemanagement/emails/profile_created.html', {
        'user': user,
    })
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_leave_status_email(leave_request, status_changed_by=None):
    """Send an email notification when a leave request status changes"""
    user = leave_request.employee.user
    subject = f'Leave Request {leave_request.status.capitalize()}'
    site_url = "http://localhost:8000"
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')

    context = {
        'user': user,
        'leave_request': leave_request,
        'status_changed_by': status_changed_by,
        'site_url': "http://localhost:8000",
    }

    html_message = render_to_string(f'leavemanagement/emails/leave_{leave_request.status}.html', context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )