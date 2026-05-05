from django.urls import path
from .views import (
    FormListView,
    FormDetailView,
    FormSubmitView,
    FormSubmissionsView,
    DraftView,
    PublicFormView,
    PublicFormSubmitView,
)

urlpatterns = [
    # Authenticated
    path('forms/', FormListView.as_view(), name='form-list'),
    path('forms/<int:pk>/', FormDetailView.as_view(), name='form-detail'),
    path('forms/<int:pk>/submit/', FormSubmitView.as_view(), name='form-submit'),
    path('forms/<int:pk>/submissions/', FormSubmissionsView.as_view(), name='form-submissions'),
    path('forms/<int:pk>/draft/', DraftView.as_view(), name='form-draft'),

    # Public (no auth)
    path('forms/<int:pk>/share/', PublicFormView.as_view(), name='form-share'),
    path('forms/<int:pk>/share/submit/', PublicFormSubmitView.as_view(), name='form-share-submit'),
]
