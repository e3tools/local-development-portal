from datetime import datetime
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings


def package_status_email_notification(package):
    context = {
        'user_name': package.user.first_name if package.user.first_name else package.user.username.split('@')[0],
        'package_submission_date': package.created_date.strftime("%m/%d/%Y, %H:%M:%S"),
        'package_tracking_url': reverse("administrativelevels:commune_detail", args=[package.id]),
        'current_year': datetime.now().year,
    }
    if package.status == package.PENDING_APPROVAL:
        template_name = 'email/package/pending_approval.html'
        subject = '[%s] The status of your investments package changed' % package.PENDING_APPROVAL
    elif package.status == package.APPROVED:
        template_name = 'email/package/approved.html'
        subject = '[%s] The status of your investments package changed' % package.APPROVED
    elif package.status == package.REJECTED:
        template_name = 'email/package/rejected.html'
        subject = '[%s] The status of your investments package changed' % package.REJECTED
    elif package.status == package.PARTIALLY_APPROVED:
        template_name = 'email/package/partially_approved.html'
        subject = '[%s] The status of your investments package changed' % package.PARTIALLY_APPROVED
    else:
        return
    # Render the HTML content
    html_content = render_to_string(template_name, context)

    # Create the email
    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[package.user.email],
    )

    # Specify the content type as HTML
    email.content_subtype = 'html'

    # Send the email
    email.send()


def sign_up_email_notification(user):
    context = {
        'user_name': user.first_name if user.first_name else user.username.split('@')[0],
        'current_year': datetime.now().year,
    }
    template_name = 'email/welcome.html'
    subject = 'Welcome to the emergency program to strengthen community resilience and security'
    # Render the HTML content
    html_content = render_to_string(template_name, context)

    # Create the email
    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email],
    )

    # Specify the content type as HTML
    email.content_subtype = 'html'

    # Send the email
    email.send()
