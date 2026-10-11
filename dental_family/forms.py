from django import forms
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
