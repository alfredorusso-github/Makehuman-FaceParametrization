import gui3d

from ._ui import CreateUI


class FaceParametrizationTaskView(gui3d.TaskView):
    def __init__(self, category):
        self.gui3d = gui3d
        gui3d.TaskView.__init__(self, category, "Face Parametrization")
        self.__create_ui()

    def __create_ui(self):
        CreateUI(self)


def load(app):
    category = app.getCategory('Utilities')
    taskview = category.addTask(FaceParametrizationTaskView(category))

def unload(app):
    pass
