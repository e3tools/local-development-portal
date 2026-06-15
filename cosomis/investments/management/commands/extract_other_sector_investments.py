import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import Q
from investments.models import Investment
from administrativelevels.models import Sector, Category

class Command(BaseCommand):
    help = 'Extracts all investments with sector "Other" to a JSON file for recategorization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='investments_other_sector.json',
            help='Output JSON file path (default: investments_other_sector.json)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'csv'],
            default='json',
            help='Output format (default: json)',
        )
        parser.add_argument(
            '--include-fields',
            type=str,
            nargs='+',
            default=['id', 'title', 'sector_name', 'administrative_level', 'estimated_cost', 'investment_status', 'project_status'],
            help='Fields to include in the output (default: basic fields)',
        )

    def handle(self, *args, **options):
        output_file = options['output']
        output_format = options['format']
        include_fields = options['include_fields']
        
        # Find the "Other" category and sector(s)
        other_category = Category.objects.filter(name__icontains='Autre').first()
        
        if not other_category:
            self.stdout.write(self.style.ERROR('Category "Autre" not found in database'))
            return
        
        # Find all sectors in the "Other" category
        other_sectors = Sector.objects.filter(category=other_category)
        
        if not other_sectors.exists():
            self.stdout.write(self.style.WARNING(f'No sectors found in category "{other_category.name}"'))
            return
        
        self.stdout.write(self.style.SUCCESS(
            f'Found category: "{other_category.name}" (ID: {other_category.id})'
        ))
        self.stdout.write(f'Sectors in this category:')
        for sector in other_sectors:
            self.stdout.write(f'  - {sector.name} (ID: {sector.id})')
        
        # Find all investments with these sectors
        investments = Investment.objects.filter(sector__in=other_sectors).select_related(
            'sector', 
            'sector__category',
            'administrative_level'
        ).order_by('sector__name', 'title')
        
        total_count = investments.count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No investments found in the "Other" sector'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\nFound {total_count} investments in "Other" sector'))
        
        # Display summary in terminal
        self.display_terminal_summary(investments, other_sectors)
        
        export_data = self.prepare_export_data(investments, include_fields)
        
        # Export to file
        if output_format == 'json':
            self.export_to_json(export_data, output_file)
        else:
            self.export_to_csv(export_data, output_file, include_fields)
        
        self.stdout.write(self.style.SUCCESS(
            f'\n Data exported to: {output_file}'
        ))
        
        # Save a backup with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'investments_other_sector_{timestamp}.json'
        self.export_to_json(export_data, backup_file)
        self.stdout.write(self.style.SUCCESS(
            f' Backup saved to: {backup_file}'
        ))
        
        # Additional statistics
        self.display_statistics(investments)
    
    def display_terminal_summary(self, investments, other_sectors):
        """Display a formatted summary in the terminal"""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SQL_FIELD('INVESTMENTS IN "OTHER" SECTOR - SUMMARY'))
        self.stdout.write('='*80)
        
        # Group by sector
        for sector in other_sectors:
            sector_investments = investments.filter(sector=sector)
            count = sector_investments.count()
            if count > 0:
                self.stdout.write(f'\n{self.style.SQL_COLTYPE(sector.name)} ({count} investments):')
                for inv in sector_investments[:5]:
                    adm_level = inv.administrative_level.name if inv.administrative_level else 'N/A'
                    self.stdout.write(
                        f'  • ID: {inv.id} | {inv.title[:50]}... | '
                        f'Cost: {inv.estimated_cost} | Status: {inv.project_status}'
                    )
                if count > 5:
                    self.stdout.write(f'  ... and {count - 5} more')
        
        self.stdout.write('\n' + '='*80)
    
    def prepare_export_data(self, investments, include_fields):
        """Prepare the data for export"""
        export_data = []
        
        for inv in investments:
            item = {
                'id': inv.id,
                'title': inv.title,
                'sector_name': inv.sector.name,
                'sector_id': inv.sector.id,
                'category_name': inv.sector.category.name if inv.sector.category else 'N/A',
                'administrative_level': inv.administrative_level.name if inv.administrative_level else 'N/A',
                'administrative_level_id': inv.administrative_level.id if inv.administrative_level else None,
                'estimated_cost': inv.estimated_cost,
                'investment_status': inv.investment_status,
                'project_status': inv.project_status,
                'funded_by': inv.funded_by.name if inv.funded_by else None,
                'funded_by_id': inv.funded_by.id if inv.funded_by else None,
                'latitude': inv.latitude,
                'longitude': inv.longitude,
                'created_at': inv.created_at.isoformat() if hasattr(inv, 'created_at') else None,
                'description': inv.description,
            }
            
            # Filter fields if specified
            if include_fields and 'all' not in include_fields:
                item = {k: v for k, v in item.items() if k in include_fields or k in ['id', 'title']}
            
            export_data.append(item)
        
        return export_data
    
    def export_to_json(self, data, filepath):
        """Export data to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_count': len(data),
                'investments': data
            }, f, ensure_ascii=False, indent=2)
    
    def export_to_csv(self, data, filepath, fields):
        """Export data to CSV file"""
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
    
    def display_statistics(self, investments):
        """Display additional statistics"""
        self.stdout.write('\n' + self.style.SQL_FIELD('ADDITIONAL STATISTICS:'))
        
        priority_count = investments.filter(investment_status=Investment.PRIORITY).count()
        subproject_count = investments.filter(investment_status=Investment.SUBPROJECT).count()
        
        self.stdout.write(f'  • Priorities: {priority_count}')
        self.stdout.write(f'  • Subprojects: {subproject_count}')
        
        status_counts = {}
        for inv in investments:
            status = inv.project_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        self.stdout.write('  • By project status:')
        for status, count in status_counts.items():
            status_display = dict(Investment.PROJECT_STATUS_CHOICES).get(status, status)
            self.stdout.write(f'    - {status_display}: {count}')
        
        # Total estimated cost
        total_cost = investments.aggregate(total=models.Sum('estimated_cost'))['total'] or 0
        self.stdout.write(f'  • Total estimated cost: {total_cost:,} FCFA')