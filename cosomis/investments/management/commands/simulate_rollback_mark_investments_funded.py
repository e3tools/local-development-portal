# yourapp/management/commands/rollback_funded_investments.py
from django.core.management.base import BaseCommand
from django.db import transaction
from investments.models import Investment, Project

class Command(BaseCommand):
    help = 'Rolls back modifications made by simulate_mark_investments_funded'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            help='ID of the funding project to target',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulates the operation without modifying the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        project_id = options.get('project-id')
        
        if project_id:
            try:
                funding_project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Project with ID {project_id} not found'))
                return
        else:
            funding_project = Project.objects.filter(name="COSO").first()
            if not funding_project:
                self.stdout.write(self.style.ERROR('No project found in the database'))
                return
        
        self.stdout.write(f"Targeted project: {funding_project.name} (ID: {funding_project.id})")
        
        investments_to_rollback = Investment.objects.filter(
            funded_by=funding_project,
        )
        
        count = investments_to_rollback.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No investments found to rollback'))
            return
        
        self.stdout.write(f"Investments found to rollback: {count}")
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"*** SIMULATION (dry-run) ***"))
            for inv in investments_to_rollback[:10]:
                self.stdout.write(
                    f"  - {inv.title} | Status: {inv.investment_status} | "
                    f"Funded by: {inv.funded_by.name}"
                )
            
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")
            
            return
        
        with transaction.atomic():
            restored_count = 0
            
            for investment in investments_to_rollback:
                investment.funded_by = None
                investment.project_status = Investment.NOT_FUNDED
                
                investment.save()
                restored_count += 1
                
                self.stdout.write(f"↺ {investment.title} restored", ending='\r')
            
            self.stdout.write("\n" + "="*50)
            self.stdout.write(self.style.SUCCESS(
                f"Success: {restored_count} investments have been restored"
            ))