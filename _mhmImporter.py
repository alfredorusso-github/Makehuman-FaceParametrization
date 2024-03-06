import os
import re
import random

import bpy
from pathlib import Path

from ._blenderconfigset import BlenderConfigSet
from ._customTargetService import TargetService
from ._objectservice import ObjectService

_OPPOSITES = [
    "decr-incr",
    "down-up",
    "in-out",
    "backward-forward",
    "concave-convex",
    "compress-uncompress",
    "square-round",
    "pointed-triangle"
]


class MhmImporter:
    def __init__(self):
        raise RuntimeError("You should not instance HumanService. Use its static methods instead.")

    @staticmethod
    def get_default_deserialization_settings():
        default_settings = {
            "mask_helpers": True,
            "detailed_helpers": True,
            "extra_vertex_groups": True,
            "feet_on_ground": True,
            "scale": 1.0,
            "subdiv_levels": 1,
            "load_clothes": True,
            "override_skin_model": "PRESET",
            "override_rig": "PRESET"
        }

        return default_settings

    @staticmethod
    def deserialize_from_mhm(filename, deserialization_settings):
        if not os.path.exists(filename):
            raise IOError(str(filename) + " does not exist")

        mhm_string = Path(filename).read_text()

        human_info = MhmImporter._create_default_human_info_dict()
        name = None

        for line in mhm_string.splitlines():
            if line.startswith("modifier"):
                MhmImporter._parse_mhm_modifier_line(human_info, line)
            else:
                if line.startswith("skinMaterial"):
                    skinLine = line.replace("skinMaterial skins/", "")
                    skinLine = skinLine.replace("skinMaterial", "")
                    human_info["skin_mhmat"] = skinLine
                    human_info["skin_material_type"] = "ENHANCED_SSS"
                if line.startswith("name "):
                    name = line.replace("name ", "")

        if "rig" not in human_info or not human_info["rig"]:
            human_info["rig"] = "default"

        if not name:
            match = re.search(r'.*([^/\\]*)\.(mhm|MHM)$', filename)
            name = match.group(1)

        human_info["name"] = name
        basemesh = MhmImporter.deserialize_from_dict(human_info, deserialization_settings)

        return basemesh

    @staticmethod
    def deserialize_from_dict(human_info, deserialization_settings):
        mask_helpers = deserialization_settings["mask_helpers"]
        detailed_helpers = deserialization_settings["detailed_helpers"]
        extra_vertex_groups = deserialization_settings["extra_vertex_groups"]
        feet_on_ground = deserialization_settings["feet_on_ground"]
        scale = deserialization_settings["scale"]
        subdiv_levels = deserialization_settings["subdiv_levels"]
        load_clothes = deserialization_settings["load_clothes"]

        if human_info is None:
            raise ValueError('Cannot use None as human_info')
        if len(human_info.keys()) < 1:
            raise ValueError('The provided dict does not seem to be a valid human_info')

        if "alternative_materials" not in human_info:
            human_info["alternative_materials"] = dict()

        macro_detail_dict = human_info["phenotype"]
        basemesh = MhmImporter.create_human(mask_helpers, detailed_helpers, extra_vertex_groups, feet_on_ground, scale,
                                            macro_detail_dict)

        if "name" in human_info and human_info["name"]:
            basemesh.name = human_info["name"] + ".body"

        if subdiv_levels > 0:
            modifier = basemesh.modifiers.new("Subdivision", 'SUBSURF')
            modifier.levels = 0
            modifier.render_levels = subdiv_levels

        MhmImporter._load_targets(human_info, basemesh)

        if feet_on_ground:
            lowest_point = MhmImporter.get_lowest_point(basemesh)
            basemesh.location = (0.0, 0.0, abs(lowest_point))
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        basemesh.use_shape_key_edit_mode = True

        return basemesh

    @staticmethod
    def _load_targets(human_info, basemesh):
        if "targets" not in human_info:
            return

        TargetService.bulk_load_targets(basemesh, human_info["targets"])

    @staticmethod
    def create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True, feet_on_ground=True, scale=0.1,
                     macro_detail_dict=None):

        exclude = []

        ObjectService.deselect_and_deactivate_all()
        basemesh = ObjectService.load_base_mesh(context=bpy.context, scale_factor=scale, load_vertex_groups=True,
                                                exclude_vertex_groups=exclude)

        _ROOT = "/home/alfredo/.config/blender/4.0/scripts/addons/mpfb/entities/objectproperties/"
        _HUMAN_PROPERTIES_DIR = os.path.join(_ROOT, "humanproperties")
        _HUMAN_PROPERTIES = BlenderConfigSet.get_definitions_in_json_directory(_HUMAN_PROPERTIES_DIR)
        HumanObjectProperties = BlenderConfigSet(_HUMAN_PROPERTIES, bpy.types.Object, prefix="HUM_")

        for key in macro_detail_dict.keys():
            name = str(key)
            if name != "race":
                HumanObjectProperties.set_value(name, macro_detail_dict[key], entity_reference=basemesh)

        for key in macro_detail_dict["race"].keys():
            name = str(key)
            HumanObjectProperties.set_value(name, macro_detail_dict["race"][key], entity_reference=basemesh)

        TargetService.reapply_macro_details(basemesh, HumanObjectProperties)

        if mask_helpers:
            modifier = basemesh.modifiers.new("Hide helpers", 'MASK')
            modifier.vertex_group = "body"
            modifier.show_in_editmode = True
            modifier.show_on_cage = True

        HumanObjectProperties.set_value("is_human_project", True, entity_reference=basemesh)

        if feet_on_ground:
            lowest_point = MhmImporter.get_lowest_point(basemesh)
            basemesh.location = (0.0, 0.0, abs(lowest_point))
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        return basemesh

    @staticmethod
    def get_lowest_point(basemesh, take_shape_keys_into_account=True):
        lowest_point = 1000.0
        vertex_data = basemesh.data.vertices
        shape_key = None
        key_name = None

        if take_shape_keys_into_account and basemesh.data.shape_keys and basemesh.data.shape_keys.key_blocks and len(
                basemesh.data.shape_keys.key_blocks) > 0:
            key_name = "temporary_lowest_point_key." + str(random.randrange(1000, 9999))
            shape_key = TargetService.create_shape_key(basemesh, key_name, also_create_basis=True, create_from_mix=True)
            vertex_data = shape_key.data

        index = 0
        for vertex in vertex_data:
            if vertex.co[2] < lowest_point and index < 13380:
                lowest_point = vertex.co[2]
            index = index + 1

        if shape_key:
            basemesh.shape_key_remove(shape_key)

        return lowest_point

    @staticmethod
    def _parse_mhm_modifier_line(human_info, line):
        line = str(line).replace("modifier ", "")

        for simple_macro in ["Age", "Gender", "Muscle", "Weight", "Height", "BodyProportions", "Asian", "African",
                             "Caucasian", "BreastSize", "BreastFirmness"]:
            macroline = line
            macroline = macroline.replace("breast/", "")
            macroline = macroline.replace("macrodetails/", "")
            macroline = macroline.replace("macrodetails-height/", "")
            macroline = macroline.replace("macrodetails-universal/", "")
            macroline = macroline.replace("macrodetails-proportions/", "")

            if macroline.startswith(simple_macro + " "):
                target, weight = macroline.split(" ", 1)
                weight = float(weight)

                if simple_macro in ["Asian", "African", "Caucasian"]:
                    human_info["phenotype"]["race"][simple_macro.lower()] = weight
                    return
                if simple_macro in ["Age", "Gender", "Muscle", "Weight", "Height"]:
                    human_info["phenotype"][simple_macro.lower()] = weight
                    return
                if simple_macro == "BodyProportions":
                    human_info["phenotype"]["proportions"] = weight
                    return

        target = MhmImporter.translate_mhm_target_line_to_target_fragment(line)
        if not "targets" in human_info or not human_info["targets"]:
            human_info["targets"] = []
        human_info["targets"].append(target)

    @staticmethod
    def translate_mhm_target_line_to_target_fragment(mhm_line):
        if mhm_line.startswith("modifier "):
            mhm_line.replace("modifier ", "")
        name, weight = mhm_line.split(" ", 1)

        weight = float(weight)
        for opposite in _OPPOSITES:
            negative, positive = opposite.split("-", 1)
            mhm_term = negative + "|" + positive

            if mhm_term in mhm_line:

                if weight < 0.0:
                    name = name.replace(mhm_term, negative)
                    weight = -weight
                else:
                    name = name.replace(mhm_term, positive)
        if "/" in name:
            dirname, name = name.split("/", 1)

        return {"target": name, "value": weight}

    @staticmethod
    def _create_default_human_info_dict():
        human_info = dict()
        human_info["phenotype"] = MhmImporter.get_default_macro_info_dict()
        human_info["rig"] = ""
        human_info["eyes"] = ""
        human_info["eyebrows"] = ""
        human_info["eyelashes"] = ""
        human_info["tongue"] = ""
        human_info["teeth"] = ""
        human_info["hair"] = ""
        human_info["proxy"] = ""
        human_info["tongue"] = ""
        human_info["targets"] = []
        human_info["clothes"] = []
        human_info["skin_mhmat"] = ""
        human_info["skin_material_type"] = "NONE"
        human_info["eyes_material_type"] = "MAKESKIN"
        human_info["skin_material_settings"] = dict()
        human_info["eyes_material_settings"] = dict()
        return human_info

    @staticmethod
    def get_default_macro_info_dict():
        return {
            "gender": 0.5,
            "age": 0.5,
            "muscle": 0.5,
            "weight": 0.5,
            "proportions": 0.5,
            "height": 0.5,
            "cupsize": 0.5,
            "firmness": 0.5,
            "race": {
                "asian": 0.33,
                "caucasian": 0.33,
                "african": 0.33
            }
        }


if __name__ == '__main__':
    base_mesh = MhmImporter.deserialize_from_mhm("/home/alfredo/Documenti/makehuman/v1py3/models/1/human_1.mhm",
                                     MhmImporter.get_default_deserialization_settings())

    camera = bpy.data.objects['Camera']
    camera.location = (0, -6.5, 13.4)
    camera.rotation_euler = (1.57079, 0, 0)

    light = bpy.data.objects['Light']
    light.location = (0, -10, 5.2)

    bpy.context.view_layer.objects.active = base_mesh
    base_mesh.select_set(True)

    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.scene.render.filepath = "/home/alfredo/Documenti/result.png"
    bpy.ops.render.render(write_still=True)
