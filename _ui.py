import os
import random
import gui
import mh
import bpy
import wavefront

import log
from core import G
from numba import cuda
from getpath import formatPath
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QThread, pyqtSignal
from ._checkboxTreeView import CheckboxTreeView
from ._humanGenerator import HumanGenerator


class CreateUI:
    not_needed_params = ["neck", "torso", "hip", "stomach", "buttocks", "pelvis", "armslegs", "breast", "genitals",
                         "macrodetails", "macrodetails-universal", "macrodetails-height", "macrodetails-proportions",
                         "measure"]

    def __init__(self, task_view):
        self.task_view = task_view
        self.worker_thread = WorkerThread(self)
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
        self.__create_generation_box()

        self.__create_export_box()

    def __create_generation_box(self):
        box = self.task_view.addLeftWidget(QtWidgets.QGroupBox("Generation"))

        self.vertical_layout = QtWidgets.QVBoxLayout()
        box.setLayout(self.vertical_layout)

        # create step value slider
        self.value_slider = gui.Slider(value=0.25, label=["Step range:", " %.2f"])
        self.vertical_layout.addWidget(self.value_slider)

        @self.value_slider.mhEvent
        def onChange(value):
            self.value = value

        # create macrodetails area
        self.vertical_layout.addSpacing(20)
        self.__create_macrodetails_area()
        self.vertical_layout.addSpacing(20)

        self.__create_random_parameters_area()
        self.vertical_layout.addSpacing(20)

        # create toggle for gpu usage
        self.gpu_toggle = gui.CheckBox("Use gpu")
        # self.vertical_layout.addWidget(self.gpu_toggle)

        # create run button
        self.run_button = gui.Button("Run")
        self.vertical_layout.addWidget(self.run_button)

        # self.run_button.clicked.connect(self.on_run_button_clicked)

        @self.run_button.mhEvent
        def onClicked(event):
            message_box = QtWidgets.QMessageBox()

            if self.gpu_toggle.isChecked() and len(cuda.list_devices() == 0):
                self.gpu_toggle.setChecked(False)
                message_box.setText("No Nvidia card detected, it's impossible to run the code with GPU.")
                message_box.exec()
                return

            if len(self.checkbox_tree_view.choices) == 0:
                message_box.setText("No choice made, choice some parameters")
                message_box.exec()
                return

            message_box.setText(f"Launched with value {self.value} and choice: {self.checkbox_tree_view.choices}")
            message_box.exec()

            self.task_view.gui3d.app.statusPersist(
                "While the plugin is creating humans it's not possible to use the application")
            human_generator = HumanGenerator(self.task_view, self.__get_macrodetails_string())
            human_generator.create_humans(self.checkbox_tree_view.choices, self.value)
            self.task_view.gui3d.app.statusPersist("")

    def __create_export_box(self):
        box = self.task_view.addLeftWidget(gui.GroupBox("Image Generation"))

        self.file_entry = box.addWidget(gui.FileEntryView(label='Select Folder', buttonLabel='Browse', mode='dir'))
        self.file_entry.filter = 'MakeHuman Models (*.mhm)'

        self.task_view.gui3d.app.addSetting('exportpath', mh.getPath("models"))
        self.file_entry.directory = self.task_view.gui3d.app.getSetting('exportpath')

        self.progress_label = box.addWidget(gui.TextView("Generated -/- images"))

        self.export_button = box.addWidget(gui.Button("Generate Image"))

        @self.file_entry.mhEvent
        def onFileSelected(event):
            self.task_view.gui3d.app.setSetting('exportpath', formatPath(event.path))

        @self.export_button.mhEvent
        def onClicked(event):
            self.__generate_images()

    def __generate_images(self):
        tmp_fbx = self.file_entry.directory + "/tmp.fbx"
        # tmp_obj = self.file_entry.directory + "tmp.obj"
        self.__set_camera_parameters()

        generated_images = 0
        number_of_files = self.__count_files()
        self.progress_label.setTextFormat(f"Generated {generated_images}/{number_of_files} images")

        for element in os.listdir(self.file_entry.directory):
            if element.endswith(".mhm"):
                self.__export_to_fbx(element, tmp_fbx)
                self.__generate_image(element, tmp_fbx)
                generated_images += 1
                self.progress_label.setTextFormat(f"Generated {generated_images}/{number_of_files} images")

        self.__remove_tmp_object(tmp_fbx)
        self.progress_label.setTextFormat("Generated -/- images")

    def __count_files(self):
        counter = 0
        for element in os.listdir(self.file_entry.directory):
            if element.endswith(".mhm"):
                counter += 1

        return counter

    @staticmethod
    def __set_camera_parameters():
        camera = bpy.data.objects['Camera']
        camera.location = (0, -6.5, 13.37)
        camera.rotation_euler = (1.57079, 0, 0)

        light = bpy.data.objects['Light']
        light.location = (0, -10, 13.37)

    def __export_to_obj(self, element, tmp_obj):
        G.app.loadHumanMHM(self.file_entry.directory + "/" + element)
        wavefront.writeObjFile(tmp_obj, G.app.selectedHuman.mesh)

    def __export_to_fbx(self, element, tmp_fbx):
        G.app.loadHumanMHM(self.file_entry.directory + "/" + element)
        G.app.mhapi.exports.exportAsFBX(tmp_fbx, False)

    def __generate_image(self, element, tmp_fbx):
        # bpy.ops.wm.obj_import(filepath=tmp_obj)
        bpy.ops.import_scene.fbx(filepath=tmp_fbx)
        obj = bpy.context.selected_objects[0]
        bpy.context.scene.render.image_settings.file_format = 'PNG'
        bpy.context.scene.render.filepath = self.file_entry.directory + "/" + element.split(".")[0] + ".png"
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(obj, do_unlink=True)

    @staticmethod
    def __remove_tmp_object(tmp_fbx):
        if os.path.exists(tmp_fbx):
            os.remove(tmp_fbx)

    def __get_macrodetails_string(self):
        gender = "modifier macrodetails/Gender " + str(float(self.gender_combobox.currentIndex()))

        ethnicity = ""
        if self.combobox.currentIndex() == 0:
            ethnicity += "modifier macrodetails/Caucasian 1.000000\nmodifier macrodetails/African 0.000000\nmodifier macrodetails/Asian 0.000000"
        elif self.combobox.currentIndex() == 1:
            ethnicity += "modifier macrodetails/Caucasian 0.000000\nmodifier macrodetails/African 1.000000\nmodifier macrodetails/Asian 0.000000"
        else:
            ethnicity += "modifier macrodetails/Caucasian 0.000000\nmodifier macrodetails/African 0.000000\nmodifier macrodetails/Asian 1.000000"

        age = "modifier macrodetails/Age " + str(self.age_slider.value() / 100)

        weight = "modifier macrodetails-universal/Weight " + str(self.weight_slider.value() / 100)

        return gender + "\n" + ethnicity + "\n" + age + "\n" + weight

    def __create_macrodetails_area(self):
        self.vertical_layout.addWidget(QtWidgets.QLabel("Macrodetails"))

        self.__create_ethnicity_layout()
        self.__create_gender_layout()
        self.__create_age_layout()
        self.__create_weight_layout()

        self.__create_macrodetails_buttons()

    def __create_random_parameters_area(self):

        # create label
        self.parameters_label = QtWidgets.QLabel("Select the number of parameters to choose randomly: 5")
        font = QtGui.QFont(self.parameters_label.font())
        font.setPointSize(8)
        self.parameters_label.setFont(font)
        self.vertical_layout.addWidget(self.parameters_label)

        # create slider
        self.parameters_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.parameters_slider.setMinimum(2)
        self.parameters_slider.setMaximum(7)
        self.parameters_slider.setValue(5)
        self.vertical_layout.addWidget(self.parameters_slider)

        self.parameters_slider.valueChanged.connect(self.__paramters_slider_value_changed)

        horizontal_layout = QtWidgets.QHBoxLayout()

        # create buttons
        self.deselect_all_button = gui.Button("Deselect all parameters")
        horizontal_layout.addWidget(self.deselect_all_button)

        self.random_parameters_button = gui.Button("Select random parameters")
        horizontal_layout.addWidget(self.random_parameters_button)

        self.vertical_layout.addLayout(horizontal_layout)

        @self.deselect_all_button.mhEvent
        def onClicked(event):
            self.checkbox_tree_view.deselect_all_elements()

        @self.random_parameters_button.mhEvent
        def onClicked(event):
            self.checkbox_tree_view.select_random_children(self.parameters_slider.value())

    def __paramters_slider_value_changed(self, value):
        self.parameters_label.setText(f"Select the number of parameters to choose randomly: {value}")

    def __create_ethnicity_layout(self):
        ethnicity_layout = QtWidgets.QHBoxLayout()
        ethnicity_layout.addWidget(QtWidgets.QLabel("Ethnicity"))

        self.combobox = QtWidgets.QComboBox()
        self.combobox.addItem("Caucasian")
        self.combobox.addItem("African")
        self.combobox.addItem("Asian")
        self.combobox.setCurrentIndex(0)
        ethnicity_layout.addWidget(self.combobox)

        self.vertical_layout.addLayout(ethnicity_layout)

    def __create_gender_layout(self):
        gender_layout = QtWidgets.QHBoxLayout()
        gender_layout.addWidget(QtWidgets.QLabel("Gender"))

        self.gender_combobox = QtWidgets.QComboBox()
        self.gender_combobox.addItem("Female")
        self.gender_combobox.addItem("Male")
        self.gender_combobox.setCurrentIndex(1)
        gender_layout.addWidget(self.gender_combobox)

        self.vertical_layout.addLayout(gender_layout)

    def __create_age_layout(self):
        age_layout = QtWidgets.QHBoxLayout()
        self.age_label = QtWidgets.QLabel("Age: 26")
        age_layout.addWidget(self.age_label)

        self.age_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.age_slider.setMinimum(18)
        self.age_slider.setMaximum(90)
        self.age_slider.setValue(26)
        age_layout.addWidget(self.age_slider)

        self.age_slider.valueChanged.connect(self.__age_slider_value_changed)

        self.vertical_layout.addLayout(age_layout)

    def __age_slider_value_changed(self, value):
        age_label_text = f"Age: {value}"
        self.age_label.setText(age_label_text)

    def __create_weight_layout(self):
        weight_layout = QtWidgets.QHBoxLayout()
        self.weight_label = QtWidgets.QLabel("Weight: 80")
        weight_layout.addWidget(self.weight_label)

        self.weight_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.weight_slider.setMinimum(50)
        self.weight_slider.setMaximum(100)
        self.weight_slider.setValue(80)
        weight_layout.addWidget(self.weight_slider)

        self.weight_slider.valueChanged.connect(self.__weight_slider_value_changed)

        self.vertical_layout.addLayout(weight_layout)

    def __weight_slider_value_changed(self, value):
        weight_label_text = f"Weight: {value}"
        self.weight_label.setText(weight_label_text)

    def __create_macrodetails_buttons(self):
        horizontal_layout = QtWidgets.QHBoxLayout()

        self.reset_button = gui.Button("Reset Parameters")
        horizontal_layout.addWidget(self.reset_button)

        @self.reset_button.mhEvent
        def onClicked(event):
            self.combobox.setCurrentIndex(0)
            self.gender_combobox.setCurrentIndex(0)
            self.age_slider.setValue(26)
            self.weight_slider.setValue(80)

        self.randomize_button = gui.Button("Randomize Macrodetails")
        horizontal_layout.addWidget(self.randomize_button)

        @self.randomize_button.mhEvent
        def onClicked(event):
            # random ethnicity
            self.combobox.setCurrentIndex(random.randint(0, self.combobox.count() - 1))

            # random gender
            self.gender_combobox.setCurrentIndex(random.randint(0, self.gender_combobox.count() - 1))

            # random age
            self.age_slider.setValue(random.randint(18, 90))

            # random weight
            self.weight_slider.setValue(random.randint(50, 100))

        self.vertical_layout.addLayout(horizontal_layout)


class CustomDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Progress Dialog')

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 100)

        self.cancel_button = QtWidgets.QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.cancelButtonClicked)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def update(self):
        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def cancelButtonClicked(self):
        print('Cancel button clicked')
        self.close()


class WorkerThread(QThread):
    progress = pyqtSignal(int)

    def __init__(self, create_ui_instance):
        super().__init__()
        self.create_ui_instance = create_ui_instance

    def run(self):
        log.message("Inside Qthread")
        self.create_ui_instance.generate_images()