from django.contrib.auth.models import User
from django.db.models import Count
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    UserSerializer, UserUpdateSerializer, UserProfileSerializer,
    FormSummarySerializer, RecentSubmissionSerializer,
)
from .models import UserProfile
from builder.models import Form, Submission


class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        forms = Form.objects.filter(owner=request.user)
        all_submissions = Submission.objects.filter(form__owner=request.user)

        forms_summary = forms.annotate(
            submission_count=Count('submissions')
        ).order_by('-updated_at')

        recent_submissions = (
            all_submissions
            .select_related('form')
            .order_by('-created_at')[:10]
        )

        return Response({
            'stats': {
                'total_forms':       forms.count(),
                'published_forms':   forms.filter(is_published=True).count(),
                'draft_forms':       forms.filter(is_published=False).count(),
                'total_submissions': all_submissions.count(),
            },
            'forms_summary':      FormSummarySerializer(forms_summary, many=True).data,
            'recent_submissions': RecentSubmissionSerializer(recent_submissions, many=True).data,
        })


class UserSubmissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        form_id = request.query_params.get('form_id')
        qs = (
            Submission.objects
            .filter(form__owner=request.user)
            .select_related('form')
            .order_by('-created_at')
        )
        if form_id:
            qs = qs.filter(form_id=form_id)
        return Response(RecentSubmissionSerializer(qs, many=True).data)
