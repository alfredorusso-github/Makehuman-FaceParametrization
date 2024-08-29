import itertools
import random
import re
import os
import time

import numpy as np

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

    def __init__(self, task_view, macrodetails, path):
        self.path = path
        self.task_view = task_view
        self.macrodetails = macrodetails

    def __create_path(self):
        # Future version: create a path according to the operating system

        self.path = os.path.expanduser("~") + "/Documenti/makehuman/v1py3/models"
        dir_number = [int(name) for name in os.listdir(self.path) if re.search(r"^\d+\.?\d*$", name)]
        self.path = self.path + "/" + str(max(dir_number) + 1) if len(dir_number) > 0 else self.path + "/1"

        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def create_humans(self, choices, step, n, is_random=False):
        if len(choices) == 0:
            modifierGroups = ['eyebrows', 'eyes', 'chin', 'forehead', 'head', 'mouth', 'nose', 'ears', 'cheek']
            human = G.app.selectedHuman
            choices = [mod.fullName for mGroup in modifierGroups for mod in human.getModifiersByGroup(mGroup)]
            # log.message(choices)

        self.__write_info_file(choices)

        log.message(f'Random generation: {is_random}')

        if is_random:
            start = time.time()
            self.__create_humans_random(n, choices)
            log.message(f"human gen time: {time.time() - start}")
        else:
            self.__create_humans_step(choices, step)

        G.app.progress(0)
        G.app.statusPersist("")

    def __create_humans_step(self, choices, step):

        values = [[i / 100 for i in range(-100, 101, int(step * 100))] for _ in range(len(choices))]

        number = 1
        combinations = list(itertools.product(*[value for value in values]))

        random.shuffle(combinations)
        n = len(combinations)

        log.message(f'80% = {round(n * 8 / 10)}  20% = {round(n * 2 / 10)}  combinations = {n}')

        train_length = round(n * 7 / 10)
        test_length = round(n * 15 / 100)

        tmp_path = self.path
        self.path = self.path + '/train'
        os.makedirs(self.path)

        for idx, combination in enumerate(combinations):
            if idx > train_length + test_length:
                self.path = tmp_path + "/validation"
            elif idx > train_length:
                self.path = tmp_path + "/test"

            if not os.path.exists(self.path):
                os.makedirs(self.path)

            self.__write_human(list(zip([choice for choice in choices], combination)), number)
            G.app.progress(number / n)
            G.app.statusPersist(f'{number}/{n}')
            number += 1

    def __create_humans_random(self, n, choices):
        train_length = round(n * 7 / 10)
        test_length = round(n * 15 / 100)

        tmp_path = self.path
        self.path = self.path + '/train'
        os.makedirs(self.path)

        for idx in range(n):
            if idx > train_length + test_length:
                self.path = tmp_path + "/validation"
            elif idx > train_length:
                self.path = tmp_path + "/test"

            if not os.path.exists(self.path):
                os.makedirs(self.path)

            parameters = self.__random_face_generation(choices)

            self.__write_human(parameters, idx)
            G.app.progress((idx + 1) / n)
            G.app.statusPersist(f'{idx + 1}/{n}')

    def __random_face_generation(self, choices):
        human = G.app.selectedHuman
        symmetry = 0

        if len(choices) == 138:
            modifierGroups = ['eyebrows', 'eyes', 'chin', 'forehead', 'head', 'mouth', 'nose', 'ears', 'cheek']

            modifiers = []
            for mGroup in modifierGroups:
                modifiers = modifiers + human.getModifiersByGroup(mGroup)

            random.shuffle(modifiers)
            choices = modifiers
        else:
            choices = [human.getModifier(modifier) for modifier in choices]

        randomValues = {}
        for m in choices:
            if m.fullName not in randomValues:
                randomValue = None

                if m.fullName in ["forehead/forehead-nubian-less|more", "forehead/forehead-scale-vert-less|more"]:
                    sigma = 0.02

                elif m.fullName in ["head/head-trans-in|out", "nose/nose-trans-in|out", "mouth/mouth-trans-in|out"]:
                    if symmetry == 1:
                        randomValue = m.getDefaultValue()
                    else:
                        mMin = m.getMin()
                        mMax = m.getMax()
                        w = float(abs(mMax - mMin) * (1 - symmetry))
                        mMin = max(mMin, m.getDefaultValue() - w / 2)
                        mMax = min(mMax, m.getDefaultValue() + w / 2)
                        randomValue = self.getRandomValue(mMin, mMax, m.getDefaultValue(), 0.1)
                        randomValues[m.fullName] = randomValue

                elif m.groupName in ["head", "forehead", "eyebrows", "eyes", "nose", "ears", "chin", "cheek",
                                     "mouth"]:
                    sigma = 0.1

                else:
                    # sigma = 0.2
                    sigma = 0.1

                if randomValue is None:
                    randomValue = self.getRandomValue(m.getMin(), m.getMax(), m.getDefaultValue(), sigma)
                    randomValues[m.fullName] = randomValue
                    # symm = m.getSymmetricOpposite()
                    # if symm and symm not in randomValues:
                    #     if symmetry == 1:
                    #         randomValues[symm] = randomValue
                    #     else:
                    #         m2 = human.getModifier(symm)
                    #         symmDeviation = float((1 - symmetry) * abs(m2.getMax() - m2.getMin())) / 2
                    #         symMin = max(m2.getMin(), min(randomValue - (symmDeviation), m2.getMax()))
                    #         symMax = max(m2.getMin(), min(randomValue + (symmDeviation), m2.getMax()))
                    #         randomValues[symm] = self.getRandomValue(symMin, symMax, randomValue, sigma)

        result = [(key, value) for key, value in randomValues.items()]
        return result

    def getRandomValue(self, minValue, maxValue, middleValue, sigmaFactor=0.2):
        rangeWidth = float(abs(maxValue - minValue))
        sigma = sigmaFactor * rangeWidth
        randomVal = random.gauss(middleValue, sigma)
        if randomVal < minValue:
            randomVal = minValue + abs(randomVal - minValue)
        elif randomVal > maxValue:
            randomVal = maxValue - abs(randomVal - maxValue)
        return max(minValue, min(randomVal, maxValue))

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

    def __write_info_file(self, choices):
        file = open(self.path + "/info.csv", "x")

        text = "Parameters chosen\n"

        for params in choices:
            text += params + "\n"

        file.write(text)
        file.close()


if __name__ == '__main__':
    params = [f'param_{i}' for i in range(8)]
    human_generator = HumanGenerator('task_view', 'macrodetails', 'path')
    human_generator.create_humans_step(params, 0.25)




