from datetime import datetime
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
import re
import locale
import random
import zlib


def send_email(
        subject, template_path_without_extension, datas, 
        to,
        cc = []
    ):

    if settings.DEBUG:
        to = [settings.RECIPIENT_EMAIL_DEFAULT]
        cc = [settings.RECIPIENT_EMAIL_DEFAULT]
    
    try:
        plaintext = get_template(template_path_without_extension+'.txt')
        htmly     = get_template(template_path_without_extension+'.html')
        
        text_content = plaintext.render(datas)
        html_content = htmly.render(datas)
        msg = EmailMultiAlternatives(subject, text_content, to=to, cc=cc)
        msg.attach_alternative(html_content, "text/html")
        msg.content_subtype = 'html'
        result = msg.send()
        
        return "success"
    except Exception as e:
        return "error"
    

def generate_random_code(longueur=6):
    return ''.join(random.choices('0123456789', k=longueur))

def generate_random_code_by_element(seed, longueur=6):
    return str(zlib.adler32(str(seed).encode('utf-8')))[:longueur]

def generate_random_code_combine(seed, longueur=6):
    return str(
        int(generate_random_code(longueur)) + int(generate_random_code_by_element(seed, longueur))
    )[:longueur]

def encoder_email(email):
    partie_nom, domaine = email.split("@")
    
    partie_masquee = partie_nom[:2] + "*" * (len(partie_nom) - 2)
    
    email_encode = partie_masquee + "@" + domaine
    return email_encode


def validate_password(password):
    # Vérifier si le mot de passe contient uniquement des lettres et des chiffres
    # if not re.fullmatch("[A-Za-z0-9]+", password):
    #     return _("The password must contain only letters and numbers.")
    
    # Vérifier la longueur (au moins 8 caractères)
    if len(password) < 8:
        return _("The password must contain at least 8 characters.")
    
    # Vérifier si le mot de passe contient au moins une lettre
    if not re.search("[A-Za-z]", password):
        return _("The password must contain at least one letter.")
    
    # Vérifier si le mot de passe contient au moins un chiffre
    if not re.search("[0-9]", password):
        return _("The password must contain at least one digit.")
    
    return True


def user_manager_email_notification(user, mail_type, motif, deadline, user_position=None):
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    data = {
        'user_name': user['first_name'] if user.get('first_name') else (user['name'].split(' ')[0] if user.get('name') else (user['email'].split('@')[0] if user.get('email') else user['username'].split('@')[0])),
        'current_year': datetime.now().year,
    }
    if mail_type == "code_change_password":
        template_name = 'email/password_change'
        title = _('Password change confirmation code')
        subject = _(f"[PDL : {datetime.now().strftime('%Y-%m-%d')}]") + " " + title

        data['description'] = _('This code is only valid for %(deadline)s')
        data['description'] = data['description'] % {'deadline': deadline}

        data['motif'] = _('Code : %(code)s')
        data['motif'] = data['motif'] % {'code': motif}
    elif mail_type == "code_forget_password":
        template_name = 'email/password_change'
        title = _('Password reset confirmation code')
        subject = _(f"[PDL : {datetime.now().strftime('%Y-%m-%d')}]") + " " + title

        data['description'] = _('This code is only valid for %(deadline)s')
        data['description'] = data['description'] % {'deadline': deadline}

        data['motif'] = _('Code : %(code)s')
        data['motif'] = data['motif'] % {'code': motif}
    elif mail_type == "user_created_notification":
        template_name = 'email/user_created_notification'
        title = _('Account automatically created on PDL')
        subject = _(f"[PDL : {datetime.now().strftime('%Y-%m-%d')}]") + " " + title

        user_name = str(data['user_name'])
        data['user_name'] = _('Mr/Ms %(user_position)s  %(user_name)s')
        data['user_name'] = data['user_name'] % {'user_position': user_position if user_position else '', 'user_name': user_name}

        data['email'] = _('Email : %(email)s')
        data['email'] = data['email'] % {'email': user['email']}

        data['motif'] = _('Password : %(motif)s')
        data['motif'] = data['motif'] % {'motif': motif}

    else:
        return
    
    data['subject'] = subject
    data['title'] = title
    
    try:
        return send_email(
            subject,
            template_name,
            data,
            [user['email']], 
            [user['email']]
        )
    except Exception as exc:
        return "error"
        


def get_user_by_email(email):

    if email:

        return User.objects.filter(email=email, is_active=True).first()
    
    return None, None