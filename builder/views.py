from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404

from .models import Form, Submission, DraftSubmission
from .serializers import FormSerializer, SubmissionSerializer, DraftSubmissionSerializer
from .engines.validation_engine import validate_submission
from .engines.navigation_engine import get_next_step
from .engines.rule_engine import execute_rules


class FormListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        forms = Form.objects.filter(owner=request.user)
        return Response(FormSerializer(forms, many=True).data)

    def post(self, request):
        serializer = FormSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FormDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_form(self, pk, user):
        return get_object_or_404(Form, pk=pk, owner=user)

    def get(self, request, pk):
        return Response(FormSerializer(self._get_form(pk, request.user)).data)

    def patch(self, request, pk):
        form = self._get_form(pk, request.user)
        serializer = FormSerializer(form, data=request.data, partial=True)
        if serializer.is_valid():
            # each schema update bumps the version
            new_version = form.version + 1 if 'schema' in request.data else form.version
            serializer.save(version=new_version)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self._get_form(pk, request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FormSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        form = get_object_or_404(Form, pk=pk)
        data = request.data.get('data', {})
        current_step = request.data.get('current_step')

        # validate
        is_valid, errors = validate_submission(form.schema, data)
        if not is_valid:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        # apply rules and determine navigation
        processed_data = execute_rules(form.schema, data)
        next_step = get_next_step(form.schema, current_step, processed_data) if current_step else None

        # only store submission when the form is complete (no next step)
        if next_step:
            return Response({
                'next_step': next_step,
                'data': processed_data,
            })

        submission = Submission.objects.create(
            form=form,
            version=form.version,
            data=processed_data,
        )
        return Response(SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)


class FormSubmissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        form = get_object_or_404(Form, pk=pk, owner=request.user)
        submissions = form.submissions.all().order_by('-created_at')
        return Response(SubmissionSerializer(submissions, many=True).data)


class DraftView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_form(self, pk):
        return get_object_or_404(Form, pk=pk)

    def get(self, request, pk):
        form = self._get_form(pk)
        draft = get_object_or_404(DraftSubmission, form=form, user=request.user)
        return Response(DraftSubmissionSerializer(draft).data)

    def post(self, request, pk):
        form = self._get_form(pk)
        draft, _ = DraftSubmission.objects.get_or_create(user=request.user, form=form)
        serializer = DraftSubmissionSerializer(draft, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        form = self._get_form(pk)
        draft = get_object_or_404(DraftSubmission, form=form, user=request.user)
        draft.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Public (no auth) ─────────────────────────────────────────────────────────

class PublicFormView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        form = get_object_or_404(Form, pk=pk)
        return Response(FormSerializer(form).data)


class PublicFormSubmitView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        form = get_object_or_404(Form, pk=pk)
        data = request.data.get('data', {})
        current_step = request.data.get('current_step')

        is_valid, errors = validate_submission(form.schema, data)
        if not is_valid:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        processed_data = execute_rules(form.schema, data)
        next_step = get_next_step(form.schema, current_step, processed_data) if current_step else None

        if next_step:
            return Response({'next_step': next_step, 'data': processed_data})

        submission = Submission.objects.create(
            form=form,
            version=form.version,
            data=processed_data,
        )
        return Response(SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)
