from django_unicorn.components import UnicornView
from subprojects.models import VillageGoal


class GoalsView(UnicornView):
    goals: list  = []
    GOALS_FOCUS_GROUP: list = []
    administrativelevel_village: object = None
    # show_button: bool = False
    def __init__(self, administrativelevel_village: object, goals: list, GOALS_FOCUS_GROUP: list,   *args, **kwargs):
        super().__init__(**kwargs)  # calling super is required
        self.administrativelevel_village = administrativelevel_village
        self.goals = list(goals)
        self.GOALS_FOCUS_GROUP = GOALS_FOCUS_GROUP

    def add(self):
        goal = VillageGoal()
        goal.focus_group = self.GOALS_FOCUS_GROUP[0]
        goal.description = ""
        goal.administrative_level = self.administrativelevel_village
        goal.meeting_id = 1
        goal = goal.save_and_return_object()
        self.goals.append(goal)
    
    def remove(self, pk):
        for i in range(len(self.goals)):
            if self.goals[i].get('pk') == pk:
                del self.goals[i]
                VillageGoal.objects.get(id=pk).delete()
                break

    # def toggle_button(self):
    #     self.show_button_x = not self.show_button_x