from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Authenticate by a single case-insensitive email match."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or password is None:
            return None
        user_model = get_user_model()
        try:
            user = user_model._default_manager.get(email__iexact=email.strip())
        except (user_model.DoesNotExist, user_model.MultipleObjectsReturned):
            # Match password hashing work without choosing between duplicate emails.
            user_model().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
