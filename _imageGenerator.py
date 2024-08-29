import os
import bpy
import time

import gui3d
import log

from ._mhmImporter import MhmImporter
from core import G


class ImageGenerator:

    def __init__(self, path, resolution_string, standard_resolution):
        self.path = path
        self.width, self.height = self.get_resolution_from_string(resolution_string)
        self.standard_resolution = standard_resolution
        self.__initialize_settings()
        self.__set_camera_parameters()
        self.__find_files_path()

    def __initialize_settings(self):
        self.settings = MhmImporter.get_default_deserialization_settings()
        self.settings["bodypart_deep_search"] = False
        self.settings["clothes_deep_search"] = False
        self.settings["scale"] = 0.1

    @staticmethod
    def __set_camera_parameters():
        camera = bpy.data.objects['Camera']

        # camera.location = (0, -6.5, 13.4)
        camera.location = (0, -0.44, 1.34)
        # camera.location = (0, -7, 5.14)

        camera.rotation_euler = (1.57079, 0, 0)

        light = bpy.data.objects['Light']
        light.location = (0, -10, 5.2)

    def __find_files_path(self):
        paths = []
        self.elements_to_process = 0

        for folder in os.listdir(self.path):
            if os.path.isdir(os.path.join(self.path, folder)):
                paths.append(os.path.join(self.path, folder))
                self.elements_to_process += self.__count_mhm_files(os.path.join(self.path, folder))

        if not len(paths) == 0:
            self.path = paths
        else:
            self.elements_to_process = self.__count_mhm_files(self.path)
            paths.append(self.path)
            self.path = paths

    @staticmethod
    def __count_mhm_files(path):
        counter = 0

        for file in os.listdir(path):
            if file.endswith('mhm'):
                counter += 1

        return counter

    def generate_images(self):

        start = time.time()

        self.set_image_resolution()
        self.set_image_format()

        progress = 1

        for path in self.path:
            for filename in os.listdir(path):
                if filename.endswith('.mhm'):
                    base_mesh = MhmImporter.deserialize_from_mhm(path + "/" + filename, self.settings)
                    bpy.context.view_layer.objects.active = base_mesh
                    base_mesh.select_set(True)

                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.context.scene.render.filepath = path + "/" + filename.split('.')[0] + ".png"
                    bpy.ops.render.render(write_still=True)

                    # obj_to_remove = bpy.data.objects[filename.split(".")[0]]
                    # bpy.data.objects.remove(obj_to_remove, do_unlink=True)

                    obj_to_remove = bpy.data.objects[filename.split(".")[0] + ".body"]
                    bpy.data.objects.remove(obj_to_remove, do_unlink=True)

                    bpy.ops.outliner.orphans_purge()

                    G.app.progress(progress / self.elements_to_process)
                    G.app.statusPersist(f'{progress}/{self.elements_to_process}')
                    progress += 1

        G.app.progress(0)
        G.app.statusPersist("")

        log.message(f"Execution time: {time.time() - start} s")

    def generate_images_from_obj(self):

        bpy.ops.preferences.addon_enable(module="io_scene_obj")
        bpy.ops.wm.save_userpref()

        start = time.time()

        self.set_image_resolution()
        self.set_image_format()

        progress = 1

        for path in self.path:
            for filename in os.listdir(path):
                if filename.endswith('.mhm'):
                    gui3d.app.selectedHuman.load(os.path.join(path, filename), True)

                    import wavefront
                    wavefront.writeObjFile(os.path.join(path, filename[:-4] + ".obj"), gui3d.app.selectedHuman.mesh)

                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.ops.import_scene.obj(filepath=os.path.join(path, filename[:-4] + ".obj"))

                    bpy.context.scene.render.filepath = path + "/" + filename.split('.')[0] + ".png"
                    bpy.ops.render.render(write_still=True)

                    obj_to_remove = bpy.data.objects[filename.split(".")[0]]
                    bpy.data.objects.remove(obj_to_remove, do_unlink=True)
                    bpy.ops.outliner.orphans_purge()

                    G.app.statusPersist(f'{progress}/{self.elements_to_process}')
                    progress += 1

        log.message(f"Execution time: {time.time() - start} s")

    @staticmethod
    def get_resolution_from_string(resolution_string):
        resolution_splitted = resolution_string.split('x')
        width = int(resolution_splitted[0])
        height = int(resolution_splitted[1])

        return width, height

    @staticmethod
    def set_image_format():
        bpy.context.scene.render.image_settings.file_format = 'PNG'

    def set_image_resolution(self):

        if self.standard_resolution:
            bpy.context.scene.render.resolution_x = 1024
            bpy.context.scene.render.resolution_y = 1024
            return

        bpy.context.scene.render.resolution_x = self.width
        bpy.context.scene.render.resolution_y = self.height


if __name__ == '__main__':
    generator = ImageGenerator("/home/alfredo/Documenti/makehuman/v1py3/models/1")
    generator.generate_images()
