import re
from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch
from urllib.parse import urlsplit
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=get_user_model().objects.create_user(username='reset-editor',email='editor@example.com',password='OldPassword!937',is_staff=True)
        cls.member=get_user_model().objects.create_user(username='registered-member',email='member@example.com',password='MemberPassword!937')
        cls.inactive=get_user_model().objects.create_user(username='inactive-member',email='inactive@example.com',password='OldPassword!937',is_active=False)

    def request_reset(self,email='editor@example.com'):
        return self.client.post(reverse('dental_family:password-reset'),{'email':email})

    def reset_path(self):
        return urlsplit(re.search(r'https?://\S+',mail.outbox[-1].body).group()).path

    def test_registered_email_reset_and_login(self):
        self.assertContains(self.client.get(reverse('dental_family:login')),'Forgot password?')
        self.assertRedirects(self.request_reset('EDITOR@example.com'),reverse('dental_family:password-reset-done'))
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].to,['editor@example.com'])
        original=self.reset_path()
        response=self.client.get(original)
        self.assertEqual(response.status_code,302)
        confirmation=response.url
        self.assertContains(self.client.get(confirmation),'A fresh start.')
        self.assertRedirects(self.client.post(confirmation,{'new_password1':'FreshPassword!572','new_password2':'FreshPassword!572'}),reverse('dental_family:password-reset-complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('FreshPassword!572'))
        self.assertContains(self.client.get(original),'This reset link has expired')
        login=self.client.post(reverse('dental_family:login'),{'email':'editor@example.com','password':'FreshPassword!572'})
        self.assertRedirects(login,reverse('dental_family:dashboard'))

    def test_ineligible_emails_show_error_without_sending_mail(self):
        get_user_model().objects.create_user(
            username='external-login', email='external@example.com', password=None,
        )
        for email in ['unknown@example.com', 'inactive@example.com', 'external@example.com']:
            with self.subTest(email=email), patch.object(
                mail.EmailMultiAlternatives, 'send',
            ) as send:
                response = self.request_reset(email)
                self.assertContains(
                    response,
                    'No active account eligible for password reset was found',
                )
                self.assertEqual(
                    response.context['form'].errors.as_data()['email'][0].code,
                    'no_reset_account',
                )
                send.assert_not_called()
        self.assertEqual(len(mail.outbox),0)

    def test_registered_nonstaff_user_can_reset_password(self):
        self.assertRedirects(self.request_reset('member@example.com'),reverse('dental_family:password-reset-done'))
        self.assertEqual(mail.outbox[0].to,['member@example.com'])

    def test_invalid_expired_and_weak_password(self):
        invalid=reverse('dental_family:password-reset-confirm',kwargs={'uidb64':'invalid','token':'invalid'})
        self.assertContains(self.client.get(invalid),'Request a new link')
        self.request_reset()
        original=self.reset_path()
        with override_settings(PASSWORD_RESET_TIMEOUT=1),patch.object(default_token_generator,'_now',return_value=default_token_generator._now()+timedelta(seconds=10)):
            self.assertContains(self.client.get(original),'This reset link has expired')
        confirmation=self.client.get(original).url
        response=self.client.post(confirmation,{'new_password1':'123','new_password2':'123'})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'This password is too short')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPassword!937'))

    def test_reset_request_requires_csrf(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('dental_family:password-reset'),{'email':'editor@example.com'}).status_code,403)
        client.get(reverse('dental_family:password-reset'))
        self.assertEqual(client.post(reverse('dental_family:password-reset'),{'email':'editor@example.com'},HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code,302)

    def test_email_delivery_error_is_displayed(self):
        with patch('django.core.mail.message.EmailMultiAlternatives.send',side_effect=SMTPException('SMTP not configured')):
            self.assertContains(self.request_reset(),'We could not send the reset email right now.')

    def test_network_error_is_not_reported_as_success(self):
        with patch('django.core.mail.backends.locmem.EmailBackend.send_messages',side_effect=OSError('Connection unreachable')):
            response=self.request_reset()
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'We could not send the reset email right now.')
        self.assertEqual(len(mail.outbox),0)

    def test_zero_messages_sent_is_reported_as_failure(self):
        with patch('django.core.mail.backends.locmem.EmailBackend.send_messages',return_value=0):
            self.assertContains(self.request_reset(),'We could not send the reset email right now.')

    @override_settings(PASSWORD_RESET_BASE_URL='https://clinic.example.com',PASSWORD_RESET_TIMEOUT=1800)
    def test_reset_origin_and_expiry_follow_configuration(self):
        self.assertContains(self.client.get(reverse('dental_family:password-reset')),'30 minutes')
        self.request_reset()
        self.assertIn('https://clinic.example.com/dashboard/reset-password/',mail.outbox[0].body)
        self.assertIn('30 minutes',mail.outbox[0].body)
        self.assertNotIn('testserver',mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',EMAIL_HOST='mail.example.com',EMAIL_PORT=465,EMAIL_USE_SSL=True,EMAIL_USE_TLS=False,EMAIL_HOST_USER='smtp-user',EMAIL_HOST_PASSWORD='test-password',DEFAULT_FROM_EMAIL='Clinic <sender@example.com>')
    def test_smtp_ssl_backend_connects_authenticates_and_sends(self):
        with patch('django.core.mail.backends.smtp.smtplib.SMTP_SSL') as connection_class:
            connection=connection_class.return_value
            connection.sendmail.return_value={}
            response=self.request_reset()
            self.assertEqual(response.status_code,302)
            self.assertEqual(connection_class.call_args.args,('mail.example.com',465))
            self.assertIsNotNone(connection_class.call_args.kwargs['context'])
            connection.login.assert_called_once_with('smtp-user','test-password')
            connection.starttls.assert_not_called()
            self.assertEqual(connection.sendmail.call_args.args[:2],('sender@example.com',['editor@example.com']))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',EMAIL_HOST='mail.example.com',EMAIL_PORT=465,EMAIL_USE_SSL=True,EMAIL_USE_TLS=False,EMAIL_HOST_USER='smtp-user',EMAIL_HOST_PASSWORD='test-password')
    def test_real_smtp_backend_network_failure_reaches_view(self):
        with patch('django.core.mail.backends.smtp.smtplib.SMTP_SSL',side_effect=OSError('Connection unreachable')):
            self.assertContains(self.request_reset(),'We could not send the reset email right now.')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',EMAIL_HOST='smtp.example.com',EMAIL_PORT=587,EMAIL_USE_SSL=False,EMAIL_USE_TLS=True,EMAIL_HOST_USER='smtp-user',EMAIL_HOST_PASSWORD='test-password',DEFAULT_FROM_EMAIL='"Dr. Teeth" <sender@example.com>')
    def test_quoted_sender_name_with_period_sends_through_smtp(self):
        with patch('django.core.mail.backends.smtp.smtplib.SMTP') as connection_class:
            connection=connection_class.return_value
            connection.sendmail.return_value={}
            response=self.request_reset()
            self.assertEqual(response.status_code,302)
            connection.starttls.assert_called_once()
            connection.login.assert_called_once_with('smtp-user','test-password')
            self.assertEqual(connection.sendmail.call_args.args[:2],('sender@example.com',['editor@example.com']))
            message=connection.sendmail.call_args.args[2]
            self.assertIn(b'From: "Dr. Teeth" <sender@example.com>',message)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',EMAIL_HOST='smtp.example.com',EMAIL_PORT=587,EMAIL_USE_SSL=False,EMAIL_USE_TLS=True,DEFAULT_FROM_EMAIL='Dr. Teeth <sender@example.com>')
    def test_invalid_sender_reports_error_without_server_crash(self):
        with patch('django.core.mail.backends.smtp.smtplib.SMTP'):
            self.assertContains(self.request_reset(),'We could not send the reset email right now.')
