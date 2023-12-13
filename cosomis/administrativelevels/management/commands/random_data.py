from django.core.management.base import BaseCommand, CommandError
from investments.models import Investment


class Command(BaseCommand):

    def handle(self, *args, **options):

        investments = Investment.objects.all()
        print(investments.count())
        i = 0
        for investment in investments:
            if i % 8 == 0:
                investment.endorsed_by_youth = True
                investment.endorsed_by_women = True
                investment.endorsed_by_agriculturist = True
                investment.endorsed_by_pastoralist = True
                investment.sector__id = 2
            elif i % 8 == 1:
                investment.endorsed_by_youth = True
                investment.endorsed_by_women = True
                investment.endorsed_by_agriculturist = False
                investment.endorsed_by_pastoralist = False
                investment.sector__id = 1
            elif i % 8 == 2:
                investment.endorsed_by_youth = False
                investment.endorsed_by_women = True
                investment.endorsed_by_agriculturist = False
                investment.endorsed_by_pastoralist = False
                investment.sector__id = 3
            elif i % 8 == 3:
                investment.endorsed_by_youth = False
                investment.endorsed_by_women = False
                investment.endorsed_by_agriculturist = False
                investment.endorsed_by_pastoralist = False
                investment.sector__id = 2
            elif i % 8 == 4:
                investment.endorsed_by_youth = False
                investment.endorsed_by_women = True
                investment.endorsed_by_agriculturist = True
                investment.endorsed_by_pastoralist = True
                investment.sector__id = 1
            elif i % 8 == 5:
                investment.endorsed_by_youth = False
                investment.endorsed_by_women = True
                investment.endorsed_by_agriculturist = False
                investment.endorsed_by_pastoralist = True
                investment.sector__id = 2
            elif i % 8 == 6:
                investment.endorsed_by_youth = True
                investment.endorsed_by_women = True
                investment.endorsed_by_agriculturist = False
                investment.endorsed_by_pastoralist = True
                investment.sector__id = 1
            elif i % 8 == 7:
                investment.endorsed_by_youth = False
                investment.endorsed_by_women = False
                investment.endorsed_by_agriculturist = False
                investment.endorsed_by_pastoralist = False
                investment.sector__id = 2
            else:
                investment.endorsed_by_youth = True
                investment.endorsed_by_women = True
                investment.endorsed_by_agriculturist = False
                investment.endorsed_by_pastoralist = False
                investment.sector__id = 3
            investment.save()
            i = i + 1
        self.stdout.write(self.style.SUCCESS('Successfully finish random!'))


