from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AdminAccountTests(TestCase):
    def setUp(self):
        self.users = get_user_model().objects
        self.admin = self.users.create_user(username='admin', email='admin@example.com', password='Password!937', is_staff=True)
        self.other = self.users.create_user(username='other', email='other@example.com', password='Password!937', is_staff=True)
        self.url = reverse('dental_family:admin-accounts')
        self.client.force_login(self.admin)

    def test_create_and_login(self):
        response = self.client.post(self.url, {'action': 'create', 'name': 'New Admin', 'email': 'NEW@example.com', 'password': 'FreshPassword!937', 'password_confirm': 'FreshPassword!937', 'is_superuser': 'true'})
        self.assertRedirects(response, self.url)
        user = self.users.get(email='new@example.com')
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('FreshPassword!937'))
        self.assertTrue(Client().login(email='new@example.com', password='FreshPassword!937'))

    def test_invalid_creation(self):
        for email, confirmation in [('ADMIN@example.com', 'Password!937'), ('bad@example.com', 'different')]:
            response = self.client.post(self.url, {'action': 'create', 'name': 'Name', 'email': email, 'password': 'Password!937', 'password_confirm': confirmation})
            self.assertTrue(response.context['form'].errors)
        self.assertEqual(self.users.count(), 2)

    def test_freeze_blocks_existing_session_login_and_reset_then_unfreeze(self):
        other_client = Client()
        other_client.force_login(self.other)
        self.client.post(self.url, {'action': 'freeze', 'account_id': self.other.pk})
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_active)
        self.assertFalse(Client().login(email=self.other.email, password='Password!937'))
        self.assertEqual(other_client.get(reverse('dental_family:dashboard')).status_code, 302)
        self.assertContains(Client().post(reverse('dental_family:password-reset'), {'email': self.other.email}), 'No active account eligible')
        self.client.post(self.url, {'action': 'unfreeze', 'account_id': self.other.pk})
        self.assertTrue(Client().login(email=self.other.email, password='Password!937'))

    def test_delete_requires_confirmation(self):
        self.client.post(self.url, {'action': 'delete', 'account_id': self.other.pk})
        self.assertTrue(self.users.filter(pk=self.other.pk).exists())
        self.client.post(self.url, {'action': 'delete', 'account_id': self.other.pk, 'confirm_email': self.other.email})
        self.assertFalse(self.users.filter(pk=self.other.pk).exists())
        self.assertFalse(Client().login(email=self.other.email, password='Password!937'))

    def test_protected_accounts(self):
        superuser = self.users.create_superuser(username='owner', email='owner@example.com', password='Password!937')
        member = self.users.create_user(username='member', email='member@example.com', password='Password!937')
        for target in [self.admin, superuser, member]:
            for action in ['freeze', 'delete']:
                response = self.client.post(self.url, {'action': action, 'account_id': target.pk, 'confirm_email': target.email})
                self.assertTrue(response.context['error'])
                target.refresh_from_db()
                self.assertTrue(target.is_active)

    def test_permissions_methods_and_csrf(self):
        self.assertEqual(Client().get(self.url).status_code, 302)
        member = self.users.create_user(username='member', password='Password!937')
        client = Client()
        client.force_login(member)
        self.assertEqual(client.post(self.url, {'action': 'freeze', 'account_id': self.other.pk}).status_code, 302)
        self.assertEqual(self.client.get(self.url, {'action': 'delete', 'account_id': self.other.pk}).status_code, 200)
        self.assertTrue(self.users.filter(pk=self.other.pk).exists())
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        self.assertEqual(csrf_client.post(self.url, {'action': 'freeze', 'account_id': self.other.pk}).status_code, 403)
        self.assertEqual(self.client.put(self.url).status_code, 405)

    def test_superadmin_can_promote_and_demote(self):
        self.admin.is_superuser = True
        self.admin.save()
        self.assertContains(self.client.get(self.url), 'Save role')
        for role, expected in [('superadmin', True), ('admin', False)]:
            response = self.client.post(self.url, {'action': 'change_role', 'account_id': self.other.pk, 'role': role})
            self.assertRedirects(response, self.url)
            self.other.refresh_from_db()
            self.assertEqual(self.other.is_superuser, expected)
            self.assertTrue(self.other.is_staff)

    def test_admin_cannot_change_roles_including_self_promotion(self):
        self.assertNotContains(self.client.get(self.url), 'Save role')
        for target in [self.admin, self.other]:
            response = self.client.post(self.url, {'action': 'change_role', 'account_id': target.pk, 'role': 'superadmin'})
            self.assertContains(response, 'Only a superadmin can change account roles.')
            target.refresh_from_db()
            self.assertFalse(target.is_superuser)

    def test_role_change_rejects_self_invalid_roles_and_preserves_frozen_status(self):
        self.admin.is_superuser = True
        self.admin.save()
        for target, role in [(self.admin, 'admin'), (self.other, 'invalid')]:
            response = self.client.post(self.url, {'action': 'change_role', 'account_id': target.pk, 'role': role})
            self.assertTrue(response.context['error'])
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_superuser)
        self.other.is_active = False
        self.other.save()
        self.client.post(self.url, {'action': 'change_role', 'account_id': self.other.pk, 'role': 'superadmin'})
        self.other.refresh_from_db()
        self.assertTrue(self.other.is_superuser)
        self.assertFalse(self.other.is_active)
