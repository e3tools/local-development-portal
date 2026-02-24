from fileinput import filename
from django.core.management.base import BaseCommand, CommandError
from administrativelevels.models import Project, AdministrativeLevel, Sector
from investments.models import Investment, Attachment
from cosomis.constants import STRUCTURE_COMPLETED_STATUS, STRUCTURE_IN_PROGRESS_STATUS, IMAGE_EXTENSIONS, STRUCTURE_COMPLETED_ONLY_STATUS
from django.conf import settings
import requests
from django.utils import timezone


class Command(BaseCommand):
    help = 'Reads an Excel file and processes it with a given project ID.'

    def is_image(self, url: str) -> bool:
        url = url.split("?")[0]  # Remove query parameters
        return url.lower().endswith(tuple(IMAGE_EXTENSIONS)) or '.kobotoolbox' in url.lower()

    def add_arguments(self, parser):
        parser.add_argument('project_id', type=int, help='The ID of the project.')
        parser.add_argument('url_default', type=str, help='The default URL of the MIS API.', default=None, nargs='?')

    def handle(self, *args, **kwargs):
        project_id = kwargs['project_id']
        url_default = kwargs.get('url_default', None)
        now = timezone.now()

        try:
            project = Project.objects.get(pk=project_id)
            print(f"Processing project: {project.name}")
        except Project.DoesNotExist:
            raise CommandError(f'Project with ID {project_id} does not exist.')

        MIS_API_KEY = settings.MIS_API_KEY
        MIS_URL = settings.MIS_URL

        url = f"{url_default}" if url_default else f"{MIS_URL}/api/subprojects/get-subprojects-simple-by-user/?page_size=1000"

        payload = {
            "token": MIS_API_KEY,
            # "infrastructures_status": STRUCTURE_COMPLETED_ONLY_STATUS
        }

        headers = {
            "Content-Type": "application/json"
        }

        all_results = []
        links_error = []

        while url:
            response = requests.post(
                url, 
                json=payload, 
                headers=headers
            )
            # response.raise_for_status()
            if response.status_code != 200:
                links_error.append(url)
                self.stdout.write(self.style.ERROR(f"Error fetching data from {url}: {response.status_code} - {response.text}"))
                url = None  # Stop the loop if there's an error
            else:
                data = response.json()
                all_results.extend(data["results"])
                url = data["next"]

        source = f"api_{project.name}"
        investments_bucket_update = []
        attachments = Attachment.objects.filter(source=source)
        attachments_bucket_create = []
        attachments_bucket_update = []
        investments_not_exists = []
        investments_multiple_objects = []
        urls = []
        for subproject in all_results:
            investment_id = f'{project.name}.{subproject["joint_subproject_number"]}.{subproject["number"]}' # PROJECT_NAME.SUBPROJECT_KIT_NUMBER.NUMBER_INFRASTRUCTURE
            investment = None
            try:
                investment = Investment.objects.get(imported_project_id=investment_id)
            except Investment.DoesNotExist:
                investments_not_exists.append(investment_id)
                self.stdout.write(self.style.ERROR(f"Investment with imported_project_id {investment_id} does not exist."))
            except Investment.MultipleObjectsReturned:
                investments_multiple_objects.append(investment_id)
                self.stdout.write(self.style.ERROR(f"Multiple investments with imported_project_id {investment_id} exist."))
            
            if investment:
                print(investment_id, investment.title)

                physical_execution_rate = subproject.get("current_level_of_physical_realization_of_the_work_percent", 0)
                if physical_execution_rate:
                    investment.physical_execution_rate = float(physical_execution_rate)
                
                project_status = "P"
                if subproject["current_status_of_the_site"] == "Identifié":
                    project_status = "F"
                elif subproject["current_status_of_the_site"] in STRUCTURE_IN_PROGRESS_STATUS:
                    project_status = "P"
                elif not subproject["current_status_of_the_site"]:
                    project_status = "F"
                elif subproject["current_status_of_the_site"] == "Arrêt":
                    project_status = "PA"
                elif subproject["current_status_of_the_site"] in STRUCTURE_COMPLETED_STATUS: #row["status"] == "Achevé" or row["status"] == "Réception provisoire" or row["status"] == "Réception technique":
                    project_status = "C"

                investment.project_status = project_status

                #Latitude, Longitude
                if subproject["latitude"] and subproject["longitude"] and (investment.latitude != subproject["latitude"] or investment.longitude != subproject["longitude"]):
                    investment.latitude = subproject["latitude"] 
                    investment.longitude = subproject["longitude"]

                investments_bucket_update.append(investment)
                
                for file in subproject.get("files", []):
                    url = file.get("url", "")
                    if url and self.is_image(url):
                        
                        if file['name']:
                            description = f"{file['name']}" + (f' [{file["description"]}]' if file.get('description') else '')
                        else:
                            description = file.get('description', '')
                        
                        attachment = attachments.filter(url=url).first()
                        attachment_action = "update"
                        if not attachment:
                            attachment = Attachment()
                            attachment_action = "create"
                            attachment.adm = investment.administrative_level
                            attachment.investment = investment
                            attachment.url = url

                        attachment.type = Attachment.PHOTO
                        attachment.process_moment = (
                            Attachment.COMPLETED_INFRASTRUCTURE if file.get('subproject_step') in STRUCTURE_COMPLETED_STATUS else (
                                Attachment.INFRASTRUCTURE_IN_PROGRESS if file.get('subproject_step') in STRUCTURE_IN_PROGRESS_STATUS else Attachment.COMMUNITY_PROCESS
                            )
                        )
                        attachment.description = description
                        attachment.order = file.get('order', 0)
                        attachment.source = source

                        if attachment_action == "create":
                            attachments_bucket_create.append(attachment)
                        else:
                            attachments_bucket_update.append(attachment)
                        urls.append(url)

        if investments_bucket_update:
            Investment.objects.bulk_update(investments_bucket_update, ['physical_execution_rate', 'project_status', 'latitude', 'longitude'])
            Investment.objects.filter(id__in=[inv.id for inv in investments_bucket_update]).update(updated_date=now)
        if attachments_bucket_create:
            Attachment.objects.bulk_create(attachments_bucket_create)
        if attachments_bucket_update:
            Attachment.objects.bulk_update(attachments_bucket_update, ['type', 'process_moment', 'description', 'order', 'source'])

        print(f"Created {len(attachments_bucket_create)} attachments")
        print(f"Updated {len(attachments_bucket_update)} attachments")
        print(f"Investments not found for IDs: {len(investments_not_exists)} {investments_not_exists}")
        print(f"Investments with multiple objects for IDs: {len(investments_multiple_objects)} {investments_multiple_objects}")

        _count_delete, _dict_delete = attachments.exclude(url__in=urls).delete()
        print(f"Deleted { _count_delete } attachments")

        self.stdout.write(self.style.SUCCESS('Successfully updated attachments!'))


        
        self.stdout.write(self.style.SUCCESS('Successfully executed command!'))