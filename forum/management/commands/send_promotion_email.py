from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from forum.models import User

class Command(BaseCommand):
    help = 'Send promotion emails to all users'

    def handle(self, *args, **kwargs):
        # Get the recipient list
        recipient_list = User.objects.values_list('personal_email', flat=True).exclude(personal_email__isnull=True).exclude(personal_email__exact='')
        
        # Render the email content
        subject = "WolfKey Updates – Celebrating 40 Users!"
        html_content = render_to_string('forum/newsletters/Promotion2.html')  # Path to your email template
        
        # Send the email
        email = EmailMessage(subject, html_content, 'chunghugo99994@gmail.com', recipient_list)
        email.content_subtype = "html"  # Set the email content type to HTML
        email.send()

        # Output success message
        self.stdout.write(self.style.SUCCESS(f'Successfully sent promotion email to {len(recipient_list)} users.'))