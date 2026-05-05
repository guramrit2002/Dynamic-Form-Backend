from django.contrib import admin
from .models import Form, Submission, DraftSubmission

admin.site.register(Form)
admin.site.register(Submission)
admin.site.register(DraftSubmission)
