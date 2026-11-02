from django.core.management.base import BaseCommand
from portal.uploads import retry_resume_deletions
from portal.models import PendingResumeDeletion
class Command(BaseCommand):
    help = 'Retry deletion of superseded resumes whose storage cleanup previously failed.'
    def handle(self, *args, **kwargs):
        retry_resume_deletions()
        self.stdout.write(f'{PendingResumeDeletion.objects.count()} resume cleanup item(s) remain pending.')
