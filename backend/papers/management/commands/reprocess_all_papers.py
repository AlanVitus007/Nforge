from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Reprocess all papers in the database to populate PaperChunk page numbers."

    def handle(self, *args, **options):
        call_command("reprocess_paper", "--all")
