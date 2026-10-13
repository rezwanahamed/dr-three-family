from django import forms
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from urllib.parse import urlsplit
from smtplib import SMTPException
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError


class DashboardAuthenticationForm(forms.Form):
    email = forms.EmailField(label='Email address', max_length=254)
    password = forms.CharField(widget=forms.PasswordInput)
    remember = forms.BooleanField(required=False)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email, password = cleaned.get('email'), cleaned.get('password')
        if email and password:
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                raise ValidationError('Enter a valid email address and password.', code='invalid_login')
            if not self.user_cache.is_staff:
                raise ValidationError('This account does not have dashboard access.', code='no_staff_access')
        return cleaned

    def get_user(self):
        return self.user_cache


from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm


def reset_expiry_label():
    minutes = settings.PASSWORD_RESET_TIMEOUT / 60
    count = f'{minutes:.2f}'.rstrip('0').rstrip('.')
    return f'{count} minute' + ('' if minutes == 1 else 's')


class DashboardPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label='Registered email address', max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete':'email','autocapitalize':'none','spellcheck':'false','autofocus':True,'placeholder':'you@example.com'}))

    def clean_email(self):
        email = self.cleaned_data['email']
        # Reuse Django's case-insensitive lookup and account eligibility checks.
        if not any(self.get_users(email)):
            raise ValidationError(
                'No active account eligible for password reset was found with this '
                'email address. Check your registered email or contact your administrator.',
                code='no_reset_account',
            )
        return email


    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        # Django's default reset form suppresses backend errors; let the view handle them.
        context={**context,'reset_expiry':reset_expiry_label()}
        base_url=getattr(settings,'PASSWORD_RESET_BASE_URL','')
        if base_url:
            parsed=urlsplit(base_url)
            context.update(domain=parsed.netloc,protocol=parsed.scheme)
        subject=''.join(render_to_string(subject_template_name,context).splitlines())
        body=render_to_string(email_template_name,context)
        message=EmailMultiAlternatives(subject,body,from_email,[to_email])
        if html_email_template_name:
            message.attach_alternative(render_to_string(html_email_template_name,context),'text/html')
        if message.send(fail_silently=False)!=1:
            raise SMTPException('Email backend did not accept the reset email.')


class DashboardSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['autocomplete'] = 'new-password'
        self.fields['new_password1'].widget.attrs['autofocus'] = True
