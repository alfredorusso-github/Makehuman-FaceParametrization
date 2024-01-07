import random

from PyQt5 import QtCore

import log
from qtgui import TreeItem, TreeView


class CheckboxTreeItem(TreeItem):
    def __init__(self, text, parent=None, isDir=False):
        super(CheckboxTreeItem, self).__init__(text, parent, isDir)
        self.setFlags(self.flags() | QtCore.Qt.ItemIsUserCheckable)

        self.isFirstTime = True
        self.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

        if isDir:
            self.childSelected = 0

    def addChild(self, text, isDir=False):
        item = CheckboxTreeItem(text, self, isDir)
        super(TreeItem, self).addChild(item)
        return item

    def addChildren(self, strings):
        items = [CheckboxTreeItem(text, self) for text in strings]
        super(TreeItem, self).addChildren(items)
        return items

    def setData(self, column, role, value):
        super(CheckboxTreeItem, self).setData(column, role, value)

        if role == QtCore.Qt.CheckStateRole and column == 0:
            if value == QtCore.Qt.CheckState.Checked:
                if self.childCount() > 0:
                    for i in range(0, self.childCount()):
                        if self.child(i).checkState(0) != QtCore.Qt.CheckState.Checked:
                            self.child(i).setCheckState(0, QtCore.Qt.CheckState.Checked)
                else:
                    self.parent.childSelected += 1

                    text = self.parent.text + "/" + self.text
                    if text not in CheckboxTreeView.choices:
                        CheckboxTreeView.add_choice(text)

                    if 0 < self.parent.childSelected < self.parent.childCount() - 1:
                        self.parent.setCheckState(0, QtCore.Qt.CheckState.PartiallyChecked)
                        return

                    if self.parent.childSelected == self.parent.childCount() and self.parent.checkState != QtCore.Qt.CheckState.Checked:
                        self.parent.setCheckState(0, QtCore.Qt.CheckState.Checked)

            elif value == QtCore.Qt.CheckState.Unchecked:
                if self.childCount() > 0:
                    for i in range(0, self.childCount()):
                        if self.child(i).checkState(0) != QtCore.Qt.CheckState.Unchecked:
                            self.child(i).setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                else:
                    if self.isFirstTime:
                        self.isFirstTime = False
                        return

                    if self.parent is not None and not self.isFirstTime:
                        self.parent.childSelected -= 1

                        text = self.parent.text + "/" + self.text
                        if text in CheckboxTreeView.choices:
                            CheckboxTreeView.remove_choice(text)

                        if self.parent.childSelected == 0 and self.parent.checkState != QtCore.Qt.CheckState.Unchecked:
                            self.parent.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                            return

                        if self.parent.childSelected != self.parent.childCount() and self.parent.checkState != QtCore.Qt.CheckState.Unchecked:
                            self.parent.setCheckState(0, QtCore.Qt.CheckState.PartiallyChecked)


class CheckboxTreeView(TreeView):

    choices = []

    def __init__(self, parent=None):
        super(CheckboxTreeView, self).__init__(parent)

    def addTopLevel(self, text, isDir=True):
        item = CheckboxTreeItem(text, None, isDir)
        self.addTopLevelItem(item)
        return item

    def select_random_children(self, n):

        self.deselect_all_elements()

        for i in range(n):
            index = random.randint(0, self.invisibleRootItem().childCount() - 1)
            item = self.topLevelItem(index)

            index = random.randint(0, item.childCount() - 1)
            item = item.child(index)

            item.setCheckState(0, QtCore.Qt.CheckState.Checked)

    def deselect_all_elements(self):
        for i in range(self.topLevelItemCount()):
            top_level_item = self.topLevelItem(i)

            if top_level_item.checkState(0) == QtCore.Qt.CheckState.Checked:
                top_level_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

            for j in range(top_level_item.childCount()):
                child_item = top_level_item.child(j)

                if child_item.checkState(0) == QtCore.Qt.CheckState.Checked:
                    child_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

    @classmethod
    def add_choice(cls, choice):
        cls.choices.append(choice)

    @classmethod
    def remove_choice(cls, choice):
        cls.choices.remove(choice)
