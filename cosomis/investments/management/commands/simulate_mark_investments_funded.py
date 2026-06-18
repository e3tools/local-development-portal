# yourapp/management/commands/mark_investments_funded.py
import json
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from investments.models import Investment, Project
from administrativelevels.models import Sector, Category

class Command(BaseCommand):
    help = 'Marks 843 investments as funded (excluding "Other" category)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulates the operation without modifying the database',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=843,
            help='Number of investments to process (default: 843)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_count = options['count']
        
        funding_project = Project.objects.first()
        if not funding_project:
            self.stdout.write(self.style.ERROR('No project found in the database'))
            return
        
        autre_category = Category.objects.filter(name__icontains='Autre').first()
        
        # Filter eligible investments
        eligible_investments = Investment.objects.filter(
            investment_status=Investment.PRIORITY,
            funded_by__isnull=True,
        )
        
        if autre_category:
            eligible_investments = eligible_investments.exclude(sector__category=autre_category)
        
        total_eligible = eligible_investments.count()
        self.stdout.write(f"Eligible investments found: {total_eligible}")
        
        if total_eligible < target_count:
            self.stdout.write(
                self.style.WARNING(
                    f"Only {total_eligible} eligible investments, "
                    f"less than the requested {target_count}"
                )
            )
            target_count = total_eligible
        
        selected_investments = eligible_investments.order_by('?')[:target_count]
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"*** SIMULATION (dry-run) ***"))
            self.stdout.write(f"Selected project for funding: {funding_project.name} (ID: {funding_project.id})")
            self.stdout.write(f"Investments that would be modified: {selected_investments.count()}")
            
            for inv in selected_investments[:10]:
                self.stdout.write(
                    f"  - {inv.title} | Sector: {inv.sector.name} | "
                    f"Status: {inv.investment_status} → funded by {funding_project.name}"
                )
            
            if selected_investments.count() > 10:
                self.stdout.write(f"  ... and {selected_investments.count() - 10} more")
            
            return
        
        with transaction.atomic():
            updated_count = 0
            
            for investment in selected_investments:
                investment._original_state = {
                    'funded_by_id': investment.funded_by_id,
                    'project_status': investment.project_status,
                }
                
                investment.funded_by = funding_project
                investment.project_status = Investment.FUNDED
                
                investment.save()
                updated_count += 1
                
                self.stdout.write(f"✓ {investment.title} funded (remains priority)", ending='\r')
            
            self.stdout.write("\n" + "="*50)
            self.stdout.write(self.style.SUCCESS(
                f"Success: {updated_count} investments have been marked as funded"
            ))
            self.stdout.write(f"Funding project: {funding_project.name} (ID: {funding_project.id})")
            
            newly_funded = Investment.objects.filter(
                funded_by=funding_project,
                investment_status=Investment.PRIORITY  
            ).count()
            
            self.stdout.write(f"Total funded priorities for this project: {newly_funded}")
            
            existing_subprojects = Investment.objects.filter(
                funded_by=funding_project,
                investment_status=Investment.SUBPROJECT
            ).count()
            
            if existing_subprojects > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Note: {existing_subprojects} SUBPROJECTs already exist for this project"
                    )
                )