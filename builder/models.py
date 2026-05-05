from django.db import models
from django.contrib.auth.models import User


class Form(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE,
                              related_name='forms')
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    schema = models.JSONField(default=dict)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} v{self.version}'


class Submission(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, 
                             related_name='submissions')
    version = models.PositiveIntegerField()
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Submission #{self.pk} for {self.form.name} v{self.version}'


class DraftSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                             blank=True, related_name='drafts')
    form = models.ForeignKey(Form, on_delete=models.CASCADE,
                             related_name='drafts')
    partial_data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'form']

    def __str__(self):
        return f'Draft for {self.form.name}'
