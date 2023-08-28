from rest_framework import serializers
from subprojects.models import *
from administrativelevels.serializers import AdministrativeLevelSerializer, CVDSerializer


class ComponentSerializer(serializers.ModelSerializer):
	class Meta:
		"""docstring for Meta"""
		model = Component
		fields = '__all__'

class FinancierSerializer(serializers.ModelSerializer):
	class Meta:
		"""docstring for Meta"""
		model = Financier
		fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
	financier = FinancierSerializer(many=False)
	class Meta:
		"""docstring for Meta"""
		model = Project
		fields = '__all__'

class VillagePrioritySerializer(serializers.ModelSerializer):
	class Meta:
		"""docstring for Meta"""
		model = VillagePriority
		fields = '__all__'


class StepSerializer(serializers.ModelSerializer):
	class Meta:
		"""docstring for Meta"""
		model = Step
		fields = '__all__'


class LevelSerializer(serializers.ModelSerializer):
	class Meta:
		"""docstring for Meta"""
		model = Level
		fields = '__all__'


class SubprojectStepSerializer(serializers.ModelSerializer):
	class Meta:
		"""docstring for Meta"""
		model = SubprojectStep
		fields = '__all__'

	def to_representation(self, instance):
		data = super().to_representation(instance)
		
		data['levels'] = LevelSerializer(instance.get_levels(), many=True).data
			
		return data



class SubprojectSerializer(serializers.ModelSerializer):
	location_subproject_realized = AdministrativeLevelSerializer(many=False)
	cvd = CVDSerializer(many=False)
	canton = AdministrativeLevelSerializer(many=False)
	component = ComponentSerializer(many=False)
	priorities = VillagePrioritySerializer(many=True)
	projects = ProjectSerializer(many=True)
	financiers = FinancierSerializer(many=True)
	class Meta:
		"""docstring for Meta"""
		model = Subproject
		fields = '__all__'

class SubprojectWithParentLinkSerializer(SubprojectSerializer):

	def to_representation(self, instance):
		data = super().to_representation(instance)
		if instance.link_to_subproject:
			data['link_to_subproject'] = SubprojectSerializer(instance.link_to_subproject).data
			
		data['current_subproject_step_and_level'] = instance.get_current_subproject_step_and_level

		return data

class SubprojectWithChildrenLinkedSerializer(SubprojectSerializer):

	def to_representation(self, instance):
		data = super().to_representation(instance)
		print(instance.subproject_set.get_queryset())
		if instance.subproject_set.get_queryset():
			data['subprojects_linked'] = SubprojectSerializer(instance.subproject_set.get_queryset(), many=True).data
			
		data['current_subproject_step_and_level'] = instance.get_current_subproject_step_and_level
			
		return data
	
