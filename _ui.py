import json
import os.path
import random
from builtins import classmethod

import gui
import log
import mh
import getpath

from core import G
from numba import cuda
from getpath import formatPath
from PyQt5 import QtWidgets, QtCore, QtGui
from ._checkboxTreeView import CheckboxTreeView
from ._humanGenerator import HumanGenerator
from ._imageGenerator import ImageGenerator


class CreateUI:
    not_needed_params = ["neck", "torso", "hip", "stomach", "buttocks", "pelvis", "armslegs", "breast", "genitals",
                         "macrodetails", "macrodetails-universal", "macrodetails-height", "macrodetails-proportions",
                         "measure", "bodyshapes"]

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
        self.__create_generation_box()
        self.__create_image_generation_box()

    def __create_generation_box(self):
        box = self.task_view.addLeftWidget(QtWidgets.QGroupBox("Human Generation"))

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

        self.__create_load_choice_from_file_area()
        self.vertical_layout.addSpacing(20)

        # Random checker
        toggle_vertical_layout = QtWidgets.QVBoxLayout()

        self.random_toggle = gui.CheckBox('Random Generation')
        self.is_random_selected = False
        toggle_vertical_layout.addWidget(self.random_toggle)

        toggle_horizontal_layout = QtWidgets.QHBoxLayout()
        self.random_label = gui.TextView('Number of files to generate: ')
        self.random_label.hide()
        toggle_horizontal_layout.addWidget(self.random_label)

        self.n_files = QtWidgets.QSpinBox()
        self.n_files.setMaximum(10000000)
        toggle_horizontal_layout.addWidget(self.n_files)
        self.n_files.hide()
        toggle_vertical_layout.addLayout(toggle_horizontal_layout)

        @self.random_toggle.mhEvent
        def onClicked(event):
            if self.random_toggle.selected:
                self.is_random_selected = True
                self.random_label.show()
                self.n_files.show()
            else:
                self.is_random_selected = False
                self.random_label.hide()
                self.n_files.hide()

        self.vertical_layout.addLayout(toggle_vertical_layout)

        # create path chooser for saving files
        horizontal_layout = QtWidgets.QHBoxLayout()
        file_entry_label = QtWidgets.QLabel("Select Folder:")
        horizontal_layout.addWidget(file_entry_label)
        self.file_entry = gui.FileEntryView(buttonLabel='Browse', mode='dir')
        horizontal_layout.addWidget(self.file_entry)
        self.file_entry.filter = 'MakeHuman Models (*.mhm)'
        self.vertical_layout.addLayout(horizontal_layout)

        self.task_view.gui3d.app.addSetting('human_path', mh.getPath("models"))
        self.file_entry.directory = self.task_view.gui3d.app.getSetting('human_path')

        # create run button
        self.run_button = gui.Button("Run")
        self.vertical_layout.addWidget(self.run_button)

        # self.random_button = gui.Button("Print")
        # self.vertical_layout.addWidget(self.random_button)
        #
        # @self.random_button.mhEvent
        # def onClicked(event):
        #     human_generator = HumanGenerator(self.task_view, self.__get_macrodetails_string(),
        #                                      self.file_entry.directory)
        #     human_generator.random_face_generation()

        @self.file_entry.mhEvent
        def onFileSelected(event):
            self.task_view.gui3d.app.setSetting('human_path', formatPath(event.path))
            self.file_entry.directory = G.app.getSetting('human_path')

        @self.run_button.mhEvent
        def onClicked(event):
            message_box = QtWidgets.QMessageBox()

            if len(self.checkbox_tree_view.choices) == 0 and not self.random_toggle.selected:
                message_box.setText("No choice made, choice some parameters")
                message_box.exec()
                return

            message_box.setText(f"Launched with value {self.value} and choice: {self.checkbox_tree_view.choices}")
            message_box.exec()

            log.message('human_path = ' + G.app.getSetting('human_path') + f'\t {self.file_entry.directory}')
            human_generator = HumanGenerator(self.task_view, self.__get_macrodetails_string(), self.file_entry.directory)
            human_generator.create_humans(self.checkbox_tree_view.choices, self.value, self.n_files.value(), self.is_random_selected)
            self.task_view.gui3d.app.statusPersist("")

    def __create_image_generation_box(self):
        box = self.task_view.addLeftWidget(gui.GroupBox("Image Generation"))

        file_entry_label = QtWidgets.QLabel("Select Folder:")
        box.addWidget(file_entry_label, 0, 0)
        self.file_entry = box.addWidget(gui.FileEntryView(buttonLabel='Browse', mode='dir'), 0,  1)
        self.file_entry.filter = 'MakeHuman Models (*.mhm)'

        resolution_label = QtWidgets.QLabel("Resolution")
        resolution_combobox = QtWidgets.QComboBox()
        resolution_combobox.addItem("32x32")
        resolution_combobox.addItem("64x64")
        resolution_combobox.addItem("128x128")
        resolution_combobox.addItem("256x256")
        resolution_combobox.addItem("512x512")
        resolution_combobox.setCurrentIndex(2)

        box.addWidget(resolution_label, 1, 0)
        box.addWidget(resolution_combobox, 1, 1)

        self.standard_resolution_toggle = gui.CheckBox('Standard resolution')
        box.addWidget(self.standard_resolution_toggle)

        self.task_view.gui3d.app.addSetting('exportpath', mh.getPath("models"))
        self.file_entry.directory = self.task_view.gui3d.app.getSetting('exportpath')

        self.export_button = box.addWidget(gui.Button("Generate Image"), columnSpan=2)

        # self.tmp_button = box.addWidget(gui.Button("TMP button"), columnSpan=2)

        @self.file_entry.mhEvent
        def onFileSelected(event):
            self.task_view.gui3d.app.setSetting('exportpath', formatPath(event.path))

        @self.export_button.mhEvent
        def onClicked(event):
            image_generator = ImageGenerator(self.file_entry.directory, resolution_combobox.currentText(), self.standard_resolution_toggle.isChecked())
            image_generator.generate_images()

        # @self.tmp_button.mhEvent
        # def onClicked(event):
        #     image_generator = ImageGenerator(self.file_entry.directory, resolution_combobox.currentText(), self.standard_resolution_toggle.isChecked())
        #     image_generator.generate_images_from_obj()

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

    def __create_load_choice_from_file_area(self):
        self.vertical_layout.addWidget(gui.TextView("Load choices from json"))

        horizontal_layout = QtWidgets.QHBoxLayout()
        file_entry_label = QtWidgets.QLabel("Select json file:")
        horizontal_layout.addWidget(file_entry_label)
        self.json_entry = gui.FileEntryView(mode='open')
        horizontal_layout.addWidget(self.json_entry)
        self.json_entry.filter = 'Json File (*.json)'
        self.vertical_layout.addLayout(horizontal_layout)

        self.task_view.gui3d.app.addSetting('json_path', os.path.expanduser("~"))
        self.json_entry.path = self.task_view.gui3d.app.getSetting('json_path')

        @self.json_entry.mhEvent
        def onFileSelected(event):
            self.task_view.gui3d.app.setSetting('json_path', formatPath(event.path))
            self.json_entry.path = G.app.getSetting('json_path')
            self.__load_choices()

        # print_button = gui.Button("Print")
        # self.vertical_layout.addWidget(print_button)
        #
        # @print_button.mhEvent
        # def onClicked(event):
        #     pass

    def __read_choices_from_json(self):

        with open(self.json_entry.path, 'r') as f:
            data = json.load(f)

        return data

    def __load_choices(self):
        json_choices = self.__read_choices_from_json()
        choices = [value for l in json_choices.values() for value in l]

        self.checkbox_tree_view.select_children(choices)

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
