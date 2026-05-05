from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['bio', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'profile']
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        UserProfile.objects.create(user=user)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']


class FormSummarySerializer(serializers.Serializer):
    id               = serializers.IntegerField()
    name             = serializers.CharField()
    version          = serializers.IntegerField()
    is_published     = serializers.BooleanField()
    submission_count = serializers.IntegerField()
    updated_at       = serializers.DateTimeField()


class RecentSubmissionSerializer(serializers.Serializer):
    id         = serializers.IntegerField()
    form_id    = serializers.IntegerField(source='form.id')
    form_name  = serializers.CharField(source='form.name')
    version    = serializers.IntegerField()
    data       = serializers.JSONField()
    created_at = serializers.DateTimeField()
