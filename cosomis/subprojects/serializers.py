from rest_framework import serializers
from subprojects.models import Subproject


class SubprojectSerializer(serializers.ModelSerializer):
	class Meta:
		"""docstring for Meta"""
		model = Subproject
		fields = '__all__'


