from django_unicorn.components import UnicornView
from subprojects.models import VillageObstacle


class ObstaclesView(UnicornView):
    obstacles = []
    OBSTACLES_FOCUS_GROUP = []
    administrativelevel_village = None
    def __init__(self, administrativelevel_village: object, obstacles: list, OBSTACLES_FOCUS_GROUP: list,   *args, **kwargs):
        super().__init__(**kwargs)  # calling super is required
        self.administrativelevel_village = administrativelevel_village
        self.obstacles = list(obstacles)
        self.OBSTACLES_FOCUS_GROUP = OBSTACLES_FOCUS_GROUP

    def add(self):
        obstacle = VillageObstacle()
        obstacle.focus_group = self.OBSTACLES_FOCUS_GROUP[0]
        obstacle.description = ""
        obstacle.administrative_level = self.administrativelevel_village
        obstacle.meeting_id = 1
        obstacle = obstacle.save_and_return_object()
        self.obstacles.append(obstacle)
    

    def remove(self, pk):
        for i in range(len(self.obstacles)):
            if self.obstacles[i]['pk'] == pk:
                del self.obstacles[i]
                VillageObstacle.objects.get(id=pk).delete()
                break