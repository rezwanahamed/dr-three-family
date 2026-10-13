"""Staff account management for the website dashboard."""
from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods


class AdminAccountForm(forms.Form):
    name = forms.CharField(max_length=150)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    password_confirm = forms.CharField(label='Confirm password', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        data = super().clean()
        password = data.get('password')
        if password and password != data.get('password_confirm'):
            self.add_error('password_confirm', 'Passwords do not match.')
        if password:
            user = get_user_model()(email=data.get('email', ''), first_name=data.get('name', ''))
            try:
                password_validation.validate_password(password, user)
            except ValidationError as error:
                self.add_error('password', error)
        return data


@never_cache
@csrf_protect
@user_passes_test(lambda user: user.is_active and user.is_staff)
@require_http_methods(['GET', 'POST'])
def admin_accounts(request):
    users = get_user_model().objects
    form = AdminAccountForm()
    error = ''
    if request.method == 'POST':
        action = request.POST.get('action')
        # Serialize account changes, including duplicate-email checks.
        with transaction.atomic():
            admins = list(users.select_for_update().filter(is_staff=True).order_by('pk'))
            actor = next((user for user in admins if user.pk == request.user.pk), None)
            if actor is None or not actor.is_active:
                error = 'Your account no longer has permission to manage admins.'
            elif action == 'create':
                form = AdminAccountForm(request.POST)
                if form.is_valid():
                    users.create_user(
                        username=uuid4().hex,
                        email=form.cleaned_data['email'],
                        first_name=form.cleaned_data['name'],
                        password=form.cleaned_data['password'],
                        is_staff=True,
                        is_superuser=False,
                    )
                    return redirect('dental_family:admin-accounts')
            elif action in {'freeze', 'unfreeze', 'delete', 'change_role'}:
                target = next((user for user in admins if str(user.pk) == request.POST.get('account_id')), None)
                if target is None:
                    error = 'Admin account not found.'
                elif action == 'change_role' and not actor.is_superuser:
                    error = 'Only a superadmin can change account roles.'
                elif target.pk == actor.pk:
                    error = 'You cannot change your own role, freeze, or delete your own account.'
                elif target.is_superuser and not actor.is_superuser:
                    error = 'Only a superadmin can change another superadmin account.'
                elif action == 'change_role' and request.POST.get('role') not in {'admin', 'superadmin'}:
                    error = 'Choose Admin or Superadmin.'
                elif action == 'delete' and request.POST.get('confirm_email') != target.email:
                    error = 'Enter the admin’s email address to confirm deletion.'
                else:
                    if action == 'delete':
                        target.delete()
                    elif action == 'change_role':
                        target.is_superuser = request.POST['role'] == 'superadmin'
                        target.save(update_fields=['is_superuser'])
                    else:
                        target.is_active = action == 'unfreeze'
                        target.save(update_fields=['is_active'])
                    return redirect('dental_family:admin-accounts')
            else:
                error = 'Choose a valid account action.'
    accounts = list(users.filter(is_staff=True).order_by('email', 'pk'))
    for account in accounts:
        account.can_manage = account.pk != request.user.pk and (request.user.is_superuser or not account.is_superuser)
    return render(request, 'dental_family/dashboard/admin_accounts.html', {
        'form': form, 'accounts': accounts, 'error': error,
    })
