from rest_framework import serializers

from investments.models import Investment


class InvestmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investment
        fields = '__all__'
