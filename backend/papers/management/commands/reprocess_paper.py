from django.core.management.base import BaseCommand, CommandError
from papers.models import Paper
from papers.views import extract_page_texts
from ai.services import create_paper_chunks


class Command(BaseCommand):
    help = "Reprocess one or all papers to extract page-by-page text and populate PaperChunk page numbers."

    def add_arguments(self, parser):
        parser.add_argument(
            "paper_id",
            nargs="?",
            type=int,
            help="ID of the paper to reprocess.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Reprocess all papers in the database.",
        )

    def handle(self, *args, **options):
        reprocess_all = options["all"]
        paper_id = options["paper_id"]

        if not reprocess_all and paper_id is None:
            raise CommandError("Please specify a paper_id or pass --all to reprocess all papers.")

        if reprocess_all:
            papers = Paper.objects.all()
        else:
            try:
                papers = [Paper.objects.get(pk=paper_id)]
            except Paper.DoesNotExist:
                raise CommandError(f"Paper with ID {paper_id} does not exist.")

        success_count = 0

        for paper in papers:
            if not paper.file:
                self.stdout.write(self.style.WARNING(f"Paper ID {paper.id} ({paper.title}) has no PDF file attached. Skipping."))
                continue

            try:
                page_texts, full_text = extract_page_texts(paper.file.path)
                paper.extracted_text = full_text
                paper.save(update_fields=["extracted_text"])

                chunks = create_paper_chunks(paper, page_texts=page_texts)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully reprocessed Paper ID {paper.id} ('{paper.title}'): "
                        f"{len(page_texts)} pages processed, {len(chunks)} chunks created with page numbers."
                    )
                )
                success_count += 1
            except Exception as err:
                self.stdout.write(
                    self.style.ERROR(f"Failed to reprocess Paper ID {paper.id}: {err}")
                )

        self.stdout.write(self.style.SUCCESS(f"Finished reprocessing {success_count} paper(s)."))
