from django.core.management.base import BaseCommand, CommandError
import time
from dateutil import parser
from fuzzywuzzy import fuzz
from django.db.models import Q
from django.utils import timezone
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment, Project
from administrativelevels.models import AdministrativeLevel, Category, Sector
from administrativelevels.libraries.functions import safe_parse_date
from administrativelevels.utils.functions import normalize_text, safe_value

class Command(BaseCommand):
    help = 'Description of your command'

    def handle(self, *args, **options):
        # Your command logic here
        if input("Remove investments whose title is Other and they have no description [y/yes ou n:no] : ").upper() in ('Y', 'YES'):
            Investment.objects.filter(title="Autre").filter(Q(Q(description=None) | Q(description=""))).delete()

        if input("Ensures the compliance of securities and sectors [y/yes ou n:no] : ").upper() in ('Y', 'YES'):
            investments = Investment.objects.all()
            sectors = Sector.objects.all()
            similarity_threshold = 60
            investments_bucket_update = []
            now = timezone.now()

            for investment in investments:
                matched_sectors = [
                    sec for sec in sectors
                    if fuzz.token_set_ratio(normalize_text(sec.name), normalize_text(investment.title)) >= similarity_threshold
                ]
                matched_sectors.sort(key=lambda s: fuzz.token_set_ratio(normalize_text(s.name), normalize_text(investment.title)), reverse=True)

                if matched_sectors:
                    investment.sector = matched_sectors[0]
                    investment.updated_date = now
                    # if investment.funded_by:
                    #     investment.investment_status = Investment.SUBPROJECT
                    # else:
                    investment.investment_status = Investment.PRIORITY
                    investments_bucket_update.append(investment)

            if investments_bucket_update:
                Investment.objects.bulk_update(investments_bucket_update, ['sector', 'updated_date', 'investment_status'], batch_size=500)

        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))

