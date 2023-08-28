from rest_framework import serializers
from administrativelevels.models import *



class GeographicalUnitSerializer(serializers.ModelSerializer):
	class Meta:
		"""docstring for Meta"""
		model = GeographicalUnit
		fields = '__all__'


class CVDSerializer(serializers.ModelSerializer):
	geographical_unit = GeographicalUnitSerializer(many=False)
	
	class Meta:
		"""docstring for Meta"""
		model = CVD
		fields = '__all__'



class AdministrativeLevelSerializer(serializers.ModelSerializer):
	geographical_unit = GeographicalUnitSerializer(many=False)
	cvd = CVDSerializer(many=False)
	class Meta:
		"""docstring for Meta"""
		model = AdministrativeLevel
		fields = '__all__'

	def to_representation(self, instance):
		data = super().to_representation(instance)
		if instance.parent:
			data['parent'] = AdministrativeLevelSerializer(instance.parent).data
		return data

class CVDWithAdministrativeLevelSerializer(serializers.ModelSerializer):
	geographical_unit = GeographicalUnitSerializer(many=False)
	administrativelevels = AdministrativeLevelSerializer(source='administrativelevel_set', many=True) 
	class Meta:
		"""docstring for Meta"""
		model = CVD
		fields = '__all__'
		extra_kwargs = {'administrativelevels': {'read_only': True}}