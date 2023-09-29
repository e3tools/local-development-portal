from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password

class PassCodeAuthBackend:
    """
    Custom authentication backend using a pass code.

    Allows users to log in using their email address and a pass code.
    """

    def authenticate(self, request, username=None, password=None):
        """
        Overrides the authenticate method to allow users to log in 
        using their email address and a pass code.
        """
        try:   
            user = User.objects.get(email=username)
            if check_pass_code(user, password):
                return user
            return None
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        """
        Overrides the get_user method to allow users to log in using their email address.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

def check_pass_code(user, plain_pass_code):
    try:
        hashed_pass_code = user.userpasscode.pass_code
        print(hashed_pass_code)
        print("EVAN", hashed_pass_code)
        return check_password(plain_pass_code, hashed_pass_code) 
    except:
        return False
    
