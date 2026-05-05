from rest_framework import serializers
from .models import Form, Submission, DraftSubmission
from .engines.schema_parser import parse_and_validate


class FormSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Form
        fields = ['id', 'owner', 'name', 'version', 'schema', 'is_published', 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'version', 'created_at', 'updated_at']

    def validate_schema(self, value):
        is_valid, errors = parse_and_validate(value)
        if not is_valid:
            raise serializers.ValidationError(errors)
        return value


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ['id', 'form', 'version', 'data', 'created_at']
        read_only_fields = ['id', 'form', 'version', 'created_at']


class DraftSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DraftSubmission
        fields = ['id', 'form', 'partial_data', 'updated_at']
        read_only_fields = ['id', 'form', 'updated_at']
