import logging
from django.db.models import F
from .models import User, PendingResumeDeletion
logger = logging.getLogger(__name__)

def retry_resume_deletions(names=None):
    pending = PendingResumeDeletion.objects.order_by('pk')
    if names is not None: pending = pending.filter(name__in=names)
    storage = User._meta.get_field('resume').storage
    for item in pending.iterator():
        # Never delete an upload which is still someone's current resume.
        if User.objects.filter(resume=item.name).exists(): continue
        try:
            storage.delete(item.name)
        except OSError as error:
            PendingResumeDeletion.objects.filter(pk=item.pk).update(attempts=F('attempts') + 1, last_error=str(error))
            logger.warning('Resume cleanup will be retried: %s', item.name)
        else:
            item.delete()

def discard_rolled_back_upload(name):
    if not name: return
    PendingResumeDeletion.objects.get_or_create(name=name)
    retry_resume_deletions([name])
