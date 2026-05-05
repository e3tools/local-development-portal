import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import time

from usermanager.models import User, Organization
from usermanager.functions import user_manager_email_notification
from usermanager.api.auth.login import CheckUserSerializer


class RegisterUsersByUploadingExcelAPIView(APIView):
    throttle_classes = ()
    permission_classes = ()
    serializer_class = CheckUserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        authorized_emails = [email.strip() for email in settings.AUTHORIZED_USERS_FOR_USER_REGISTRATION_VIA_API.split(',') if '@' in email.strip()]

        if user.email not in authorized_emails:
            return Response(
                {"error": "You are not authorized to register users via this API."},
                status=status.HTTP_403_FORBIDDEN
            )

        # récupérer le fichier envoyé
        file = request.FILES.get('file')
        organization_type = request.POST.get('organization_type')

        if not file:
            return Response(
                {"error": "Aucun fichier envoyé"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            users_saved_emails = []
            mails_not_sent_to = []
            users_emails_already_exist = []
            users_cant_see_organization = []

            # lire le fichier Excel
            df = pd.read_excel(file)

            # convertir en JSON
            data = df.to_dict(orient="records")
            
            for row in data:
                email = row.get('ADRESSE MAIL').strip() if row.get('ADRESSE MAIL') else None
                password = row.get('MOT DE PASSE')
                if email and any(_elt for _elt in ['.', '@'] if _elt in email) and password:
                    if not User.objects.filter(email=email).exists():
                        username = email
                        password = password.strip()
                        full_name = row.get('NOM ET PRENOMS').strip() if row.get('NOM ET PRENOMS') else ''
                        last_name = (full_name.split(' ')[0] if full_name else '').upper()
                        first_name = (' '.join(full_name.split(' ')[1:]) if full_name and len(full_name.split(' ')) > 1 else '').title()
                        title = row.get('TITRE').strip() if row.get('TITRE') else ''


                        if organization_type == 'commune':
                            commune = row.get('COMMUNE').strip() if row.get('COMMUNE') else ''
                            organization = Organization.objects.filter(name__icontains='Mairie ').filter(name__icontains=commune).first()
                        elif organization_type == 'prefecture':
                            prefecture = row.get('PREFECTURE').strip() if row.get('PREFECTURE') else ''
                            organization = Organization.objects.filter(name__icontains='Préfecture ').filter(name__icontains=prefecture).first()
                        elif organization_type == 'region':
                            region = row.get('REGION').strip() if row.get('REGION') else ''
                            organization = Organization.objects.filter(name__icontains='Gouvernorat ').filter(name__icontains=region).first()
                        else:
                            organization = Organization.objects.filter(name__iexact=organization_type).first()
                        
                        if organization:
                            user = User.objects.create_user(
                                    email=email,
                                    username=username,
                                    password=password,
                                    
                                )
                            user.first_name = first_name
                            user.last_name = last_name
                            user.is_approved = True
                            user.is_active = True
                            user.password_changed_once = False
                            user.organization = organization

                            user.save()
                            
                            users_saved_emails.append(email)

                            msg = user_manager_email_notification(
                                {'email': email, 'first_name': f"{last_name} {first_name}" if last_name else first_name, 'last_name': last_name, 'username': username},
                                "user_created_notification", 
                                motif=password, 
                                deadline=None, 
                                user_position=(f"l'{str(title)}" if any(elt for elt in ['a', 'e', 'i', 'o', 'u'] if str(title).lower().startswith(elt)) else f"le {str(title)}") if title else None
                            )

                            if msg == 'error':
                                mails_not_sent_to.append(email)

                            time.sleep(2)  # Pause de 2 secondes entre les envois d'e-mails pour éviter de surcharger le serveur de messagerie
                        else:
                            users_cant_see_organization.append(email)

                    else:
                        users_emails_already_exist.append(email)


            return Response({
                "number_of_users_created": len(users_saved_emails),
                "number_of_users_already_exist": len(users_emails_already_exist),
                "number_of_mails_not_sent_to": len(mails_not_sent_to),
                "users_saved_emails": users_saved_emails,
                "users_emails_already_exist": users_emails_already_exist,
                "mails_not_sent_to": mails_not_sent_to
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {
                    "error": str(e),
                    "number_of_users_created": len(users_saved_emails),
                    "number_of_users_already_exist": len(users_emails_already_exist),
                    "number_of_mails_not_sent_to": len(mails_not_sent_to),
                    "number_of_users_cant_see_organization": len(users_cant_see_organization),
                    "users_saved_emails": users_saved_emails,
                    "users_emails_already_exist": users_emails_already_exist,
                    "mails_not_sent_to": mails_not_sent_to,
                    "users_cant_see_organization": users_cant_see_organization
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )