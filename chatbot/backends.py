from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailBackend(ModelBackend):
    """Authenticate using email + password instead of username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # 'username' kwarg carries the email value from authenticate()
        email = kwargs.get('email', username)
        if email is None or password is None:
            return None
        try:
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            UserModel().set_password(password)  # constant-time comparison
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
