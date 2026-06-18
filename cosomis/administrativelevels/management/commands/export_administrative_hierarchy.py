from openpyxl import Workbook
from django.core.management.base import BaseCommand
from administrativelevels.models import AdministrativeLevel


class Command(BaseCommand):
    help = (
        "Export all villages and their hierarchy "
        "(Département > Commune > Arrondissement > Village) "
        "to an Excel file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="administrative_hierarchy.xlsx",
            help="Output Excel file path",
        )

    def handle(self, *args, **options):
        output_file = options["output"]

        villages = AdministrativeLevel.objects.filter(
            AdministrativeLevel.type_filter_q(
                AdministrativeLevel.VILLAGE
            )
        ).select_related("parent")

        village_count = villages.count()

        self.stdout.write(
            f"Found {village_count} village(s)."
        )

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Administrative Hierarchy"

        worksheet.append([
            "Département",
            "Commune",
            "Arrondissement",
            "Village",
        ])

        exported_rows = 0

        for village in villages:

            prefecture = ""
            commune = ""
            canton = ""

            current = village

            while current:

                if current.is_prefecture():
                    prefecture = current.name

                elif current.is_commune():
                    commune = current.name

                elif current.is_canton():
                    canton = current.name

                current = current.parent

            worksheet.append([
                prefecture,
                commune,
                canton,
                village.name,
            ])

            exported_rows += 1

        # Optional column sizing
        for column in worksheet.columns:
            max_length = max(
                len(str(cell.value or ""))
                for cell in column
            )
            worksheet.column_dimensions[
                column[0].column_letter
            ].width = max(max_length + 2, 15)

        workbook.save(output_file)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully exported "
                f"{exported_rows} village(s) "
                f"to '{output_file}'."
            )
        )
