from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailAuthBackend(ModelBackend):
    """Authenticate using an email address instead of username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username)  # Match with email
            print("User found:", user.email)  # Debugging
            if user.check_password(password):
                print("Password matched")  # Debugging
                return user
            else:
                print("Password incorrect")  # Debugging
        except User.DoesNotExist:
            print("User does not exist")  # Debugging

        return None
