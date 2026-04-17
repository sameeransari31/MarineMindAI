"""
DRF serializers for vessel analytics APIs.
"""
from rest_framework import serializers
from administration.models import Vessel, NoonReport
from analytics.models import NoonReportImport, ImportRow


# ─────────────────────────────────────────────────────────────────────────────
# VESSEL SERIALIZERS
# ─────────────────────────────────────────────────────────────────────────────

class VesselListSerializer(serializers.ModelSerializer):
    noon_report_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Vessel
        fields = [
            'id', 'name', 'vessel_type', 'imo_number', 'call_sign',
            'flag_state', 'dwt', 'grt', 'year_built',
            'fleet_name', 'owner', 'manager',
            'operational_status', 'main_engine_type',
            'noon_report_count', 'document_count',
        ]

    def get_noon_report_count(self, obj):
        return obj.noon_reports.count()

    def get_document_count(self, obj):
        return obj.documents.count()


class VesselDetailSerializer(serializers.ModelSerializer):
    noon_report_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Vessel
        fields = '__all__'

    def get_noon_report_count(self, obj):
        return obj.noon_reports.count()

    def get_document_count(self, obj):
        return obj.documents.count()


class VesselCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vessel
        exclude = ['id', 'created_at', 'updated_at']


# ─────────────────────────────────────────────────────────────────────────────
# NOON REPORT SERIALIZERS
# ─────────────────────────────────────────────────────────────────────────────

class NoonReportListSerializer(serializers.ModelSerializer):
    vessel_name = serializers.CharField(source='vessel.name', read_only=True)

    class Meta:
        model = NoonReport
        fields = [
            'id', 'vessel', 'vessel_name', 'report_date', 'report_time',
            'voyage_number', 'latitude', 'longitude',
            'speed_avg', 'distance_sailed', 'rpm_avg',
            'fo_consumption', 'bf_consumption',
            'wind_force', 'sea_state',
            'cargo_condition', 'is_validated',
            'created_at',
        ]


class NoonReportDetailSerializer(serializers.ModelSerializer):
    vessel_name = serializers.CharField(source='vessel.name', read_only=True)

    class Meta:
        model = NoonReport
        fields = '__all__'


class NoonReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoonReport
        exclude = ['id', 'created_at', 'updated_at', 'uploaded_by', 'is_validated']


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT SERIALIZERS
# ─────────────────────────────────────────────────────────────────────────────

class ImportRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRow
        fields = ['id', 'row_number', 'status', 'raw_data', 'errors', 'noon_report']


class NoonReportImportSerializer(serializers.ModelSerializer):
    vessel_name = serializers.CharField(source='vessel.name', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = NoonReportImport
        fields = [
            'id', 'original_filename', 'file_type', 'vessel', 'vessel_name',
            'status', 'total_rows', 'successful_rows', 'failed_rows',
            'skipped_rows', 'error_summary',
            'uploaded_by', 'uploaded_by_username',
            'created_at', 'completed_at',
        ]
        read_only_fields = [
            'id', 'status', 'total_rows', 'successful_rows', 'failed_rows',
            'skipped_rows', 'error_summary', 'created_at', 'completed_at',
        ]


class NoonReportImportDetailSerializer(NoonReportImportSerializer):
    rows = ImportRowSerializer(many=True, read_only=True)

    class Meta(NoonReportImportSerializer.Meta):
        fields = NoonReportImportSerializer.Meta.fields + ['rows']
