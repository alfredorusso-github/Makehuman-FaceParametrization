import itertools
import re
import os

import log
from core import G


class HumanGenerator:
    VERSION = "version v1.2.0"
    CAMERA = "camera 0.0 0.0 0.0 0.0 0.0 1.225"
    STANDARD_PARAMETERS = """modifier macrodetails-universal/Muscle 0.500000
        modifier macrodetails-height/Height 0.500000
        modifier macrodetails-proportions/BodyProportions 0.500000"""
    SUFFIX = """eyes HighPolyEyes 2c12f43b-1303-432c-b7ce-d78346baf2e6
        clothesHideFaces True
        skinMaterial skins/default.mhmat
        material HighPolyEyes 2c12f43b-1303-432c-b7ce-d78346baf2e6 eyes/materials/brown.mhmat
        subdivide False"""

    def __init__(self, task_view, macrodetails):
        self.__create_path()
        self.task_view = task_view
        self.macrodetails = macrodetails

    def __create_path(self):
        # Future version: create a path according to the operating system

        self.path = os.path.expanduser("~") + "/Documenti/makehuman/v1py3/models"
        dir_number = [int(name) for name in os.listdir(self.path) if re.search(r"^\d+\.?\d*$", name)]
        self.path = self.path + "/" + str(max(dir_number) + 1) if len(dir_number) > 0 else self.path + "/1"

        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def create_humans(self, choices, step):

        values = [[i / 100 for i in range(-100, 101, int(step * 100))] for _ in range(len(choices))]

        number = 1
        combinations = list(itertools.product(*[value for value in values]))
        n = len(combinations)

        for combination in combinations:
            self.__write_human(list(zip([choice for choice in choices], combination)), number)
            G.app.progress(number / n)
            number += 1

        G.app.progress(0)

    def __write_human(self, parameters, number):
        file_name = "human_" + str(number) + ".mhm"
        file = open(self.path + "/" + file_name, "x")
        name = "name human_" + str(number)

        pattern = r"\n\s+"
        result = (self.VERSION + "\n" + name + "\n" + self.CAMERA + "\n" + self.macrodetails + "\n" +
                  re.sub(pattern, "\n", self.STANDARD_PARAMETERS) + "\n")

        for param in parameters:
            result += "modifier " + param[0] + " " + str(param[1]) + "\n"

        result += re.sub(pattern, "\n", self.SUFFIX)
        file.write(result)
        file.close()
