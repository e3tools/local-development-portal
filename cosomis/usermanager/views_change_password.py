# from django.http import HttpResponseRedirect
from django.conf import settings
from django.utils.translation import get_language
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
import logging
from django.http import Http404

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from usermanager.functions import user_manager_email_notification, generate_random_code_combine, validate_password
from usermanager.models import ValidationCode
from usermanager.functions import encoder_email

User = get_user_model()

class RestSendChangePasswordCode(APIView):
    def post(self, request, *args, **kwargs):

        email = self.request.POST.get('email', None)
        first_name = self.request.POST.get('first_name', None)
        last_name = self.request.POST.get('last_name', None)
        name = self.request.POST.get('name', None)
        username = self.request.POST.get('username', None)
        
        msg = _("We are encountering a few errors when sending you e-mails.")
        if email and username:
            code = generate_random_code_combine(email)
            
            now=timezone.now()
            minutes_to_add = 15
            new_time = now + timedelta(minutes=minutes_to_add)
            
            ValidationCode.objects.filter(email=email).update(already_use=True)
            
            validation_code = ValidationCode(
                code=code,
                email=email,
                asking_datetime=now,
                validation_code_ending_datetime=new_time,
                motif="Code de confirmation pour accéder au changement de mot de passe"
            )
            
            validation_code.save()

            msg = user_manager_email_notification(
                {'email': email, 'first_name': first_name, 'last_name': last_name, 'name': name, 'username': username},
                mail_type= "code_change_password",
                motif=code,
                deadline=f"{minutes_to_add} minitues"
            )

        messages.add_message(self.request, messages.ERROR, msg, extra_tags='error')

        return Response(
            render(self.request, 'common/messages.html').content.decode("utf-8"), status.HTTP_200_OK
        )
    



class RestChangePassword(APIView):
    def post(self, request, *args, **kwargs):

        # data = {}
        if request.method == 'POST':
            ok = False
            confirm_code = request.POST.get('confirm_code', None)
            current_password = request.POST.get('current_password', None)
            password_new = request.POST.get('password_new', None)
            password_new_confirm = request.POST.get('password_new_confirm', None)

            email = request.POST.get('email', None)
            csrfmiddlewaretoken = request.POST.get('csrfmiddlewaretoken', None)
            
            if email and confirm_code and current_password and password_new and password_new_confirm:

                is_validate_password = validate_password(password_new)
                validation_code = ValidationCode.objects.filter(code=confirm_code)

                if not validation_code:
                    msg = _("Code invalide")
                elif not validation_code.filter(validation_code_ending_datetime__gt=timezone.now()).exists():
                    msg = _("Code expired")
                elif not validation_code.filter(validation_code_ending_datetime__gt=timezone.now(), already_use=False).exists():
                    msg = _("Code already used")
                elif not is_validate_password:
                    msg = is_validate_password
                elif password_new != password_new_confirm:
                    msg = _("The password must be the same as the previous one.")
                else:
                    # data['email'] = email
                    print(email)
                    user = User.objects.filter(email=email, is_active=True).first()
                    
                    if not user or not check_password(current_password, user.password):
                        msg = _('Current password does not match.')
                    else:
                        password_new_hashed = make_password(password_new)

                        user.password = password_new_hashed
                        user.save()

                        msg = _('The password has been successfully changed.')
                        ok = True
                        validation_code.update(already_use=True)

            else:
                msg = _('You have to fill all the fields')
            
            messages.add_message(self.request, messages.INFO, msg, extra_tags='info')

            context = {
                'msg': render(self.request, 'common/messages.html').content.decode("utf-8"),
                'msg_text': msg,
                'ok': ok,
                # 'redirection_url': request.POST.get('redirection_url_origin_after_user_manage', None)
            }
            return Response(
                context, status.HTTP_200_OK
            )
            
        # elif request.method == "GET" and request.session.get('redirection_url_origin_after_user_manage'):
        #     redirection_url = request.session.get('redirection_url_origin_after_user_manage')
            
        #     return redirect(redirection_url)
        
        raise Http404