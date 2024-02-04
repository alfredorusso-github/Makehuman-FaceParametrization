import os

import bpy

bpy.ops.preferences.addon_enable(module='mpfb')

from mpfb.services.humanservice import HumanService
from core import G


class ImageGenerator:

    def __init__(self, path):
        self.path = path
        self.__initialize_settings()
        self.__set_camera_parameters()

    def __initialize_settings(self):
        self.settings = HumanService.get_default_deserialization_settings()
        self.settings["bodypart_deep_search"] = False
        self.settings["clothes_deep_search"] = False
        self.settings["scale"] = 1.0

    @staticmethod
    def __set_camera_parameters():
        camera = bpy.data.objects['Camera']
        camera.location = (0, -6.5, 13.4)
        camera.rotation_euler = (1.57079, 0, 0)

        light = bpy.data.objects['Light']
        light.location = (0, -10, 5.2)

    def generate_images(self):

        self.set_image_format()

        progress = 1
        elements_to_process = len(os.listdir(self.path))

        for filename in os.listdir(self.path):
            if filename.endswith('.mhm'):
                base_mesh = HumanService.deserialize_from_mhm(self.path + "/" + filename, self.settings)
                bpy.context.view_layer.objects.active = base_mesh
                base_mesh.select_set(True)

                bpy.ops.object.select_all(action='DESELECT')
                bpy.context.scene.render.filepath = self.path + "/" + filename.split('.')[0] + ".png"
                bpy.ops.render.render(write_still=True)

                obj_to_remove = bpy.data.objects[filename.split(".")[0]]
                bpy.data.objects.remove(obj_to_remove, do_unlink=True)

                obj_to_remove = bpy.data.objects[filename.split(".")[0] + ".body"]
                bpy.data.objects.remove(obj_to_remove, do_unlink=True)

                G.app.progress(progress / elements_to_process)
                progress += 1
        
        G.app.progress(0)

    @staticmethod
    def set_image_format():
        bpy.context.scene.render.image_settings.file_format = 'PNG'
