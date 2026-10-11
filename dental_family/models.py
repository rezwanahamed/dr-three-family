from django.db import models


class WebsiteWorkspace(models.Model):
    """One shared editorial workspace and the last published website snapshot."""
    draft = models.JSONField(default=dict)
    published = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
