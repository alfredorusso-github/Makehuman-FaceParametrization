import gui
from core import G
from PyQt5 import QtWidgets
from ._checkboxTreeView import CheckboxTreeView
from ._humanGenerator import HumanGenerator


class CreateUI:
    not_needed_params = ["neck", "torso", "hip", "stomach", "buttocks", "pelvis", "armslegs", "breast", "genitals",
                         "macrodetails", "macrodetails-universal", "macrodetails-height", "macrodetails-proportions",
                         "measure"]

    def __init__(self, task_view):
        self.task_view = task_view
        self.value = 0.25

        self.__create_treeview()
        self.__create_left_widgets()

    def __create_treeview(self):
        scroll = self.task_view.addTopWidget(gui.VScrollArea())
        self.tree_box = gui.GroupBox('Parameters')
        self.tree_box.setSizePolicy(gui.SizePolicy.MinimumExpanding, gui.SizePolicy.Expanding)

        self.paramsDict = {}
        self.checkbox_tree_view = CheckboxTreeView()
        self.__populate_treeview()
        self.tree_box.addWidget(self.checkbox_tree_view)

        scroll.setWidget(self.tree_box)

    def __populate_treeview(self):
        parameters = G.app.selectedHuman.getModifierNames()

        for modifier in parameters:
            split_line = modifier.split("/")
            if split_line[0] not in self.not_needed_params:
                self.paramsDict.setdefault(split_line[0], []).append(split_line[1])

        for key in self.paramsDict.keys():
            item = self.checkbox_tree_view.addTopLevel(key)
            item.addChildren(self.paramsDict[key])

    def __create_left_widgets(self):
        box = self.task_view.addLeftWidget(gui.GroupBox("Face parametrization"))

        # create slider
        self.value_slider = box.addWidget(gui.Slider(value=0.25, label=["Step range:", " %.2f"]))

        @self.value_slider.mhEvent
        def onChange(value):
            self.value = value

        # create toggle for gpu usage
        self.gpu_toggle = box.addWidget(gui.CheckBox("Use gpu"))

        # create run button
        self.run_button = box.addWidget(gui.Button("Run"))
        # self.run_button.clicked.connect(self.on_run_button_clicked)

        @self.run_button.mhEvent
        def onClicked(event):
            message_box = QtWidgets.QMessageBox()

            if len(self.checkbox_tree_view.choices) == 0:
                message_box.setText("No choice made, choice some parameters")
                message_box.exec()
                return

            message_box.setText(f"Launched with value {self.value} and choice: {self.checkbox_tree_view.choices}")
            message_box.exec()

            self.task_view.gui3d.app.statusPersist("While the plugin is creating humans it's not possible to use the application")
            human_generator = HumanGenerator(self.task_view)
            human_generator.create_humans(self.checkbox_tree_view.choices, self.value)
            self.task_view.gui3d.app.statusPersist("")
