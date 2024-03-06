# This is very annoying, but the maximum length of a shape key name is 61 characters
# in blender. The combinations used in MH filenames tend to be longer than that.
import gzip
import json
import os
import re

import bpy

from pathlib import Path
from ._blenderconfigset import BlenderConfigSet

_SHAPEKEY_ENCODING = [
    ["macrodetail", "$md"],
    ["female", "$fe"],
    ["male", "$ma"],
    ["caucasian", "$ca"],
    ["asian", "$as"],
    ["african", "$af"],
    ["average", "$av"],
    ["weight", "$wg"],
    ["height", "$hg"],
    ["muscle", "$mu"],
    ["proportions", "$pr"],
    ["firmness", "$fi"],
    ["ideal", "$id"],
    ["uncommon", "$un"],
    ["young", "$yn"],
    ["child", "$ch"],
]

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

_ODD_TARGET_NAMES = []

_TARGETS_DIR = "/home/alfredo/.config/blender/4.0/scripts/addons/mpfb/data/targets"
_MACRO_CONFIG = dict()
_MACRO_FILE = os.path.join(_TARGETS_DIR, "macrodetails", "macro.json")
_MACRO_PATH_PATTERN = "/mpfb/data/targets/macrodetails/"

with open(_MACRO_FILE, "r") as json_file:
    _MACRO_CONFIG = json.load(json_file)

_GENERAL_PROPERTIES_DIR = ("/home/alfredo/.config/blender/4.0/scripts/addons/mpfb/entities/objectproperties"
                           "/generalproperties/")
_GENERAL_PROPERTIES = BlenderConfigSet.get_definitions_in_json_directory(_GENERAL_PROPERTIES_DIR)
GeneralObjectProperties = BlenderConfigSet(_GENERAL_PROPERTIES, bpy.types.Object, prefix="GEN_")


class TargetService:

    def __init__(self):
        raise RuntimeError("You should not instance TargetService. Use its static methods instead.")

    @staticmethod
    def reapply_macro_details(basemesh, HumanObjectProperties, remove_zero_weight_targets=True):
        macro_info = TargetService.get_macro_info_dict_from_basemesh(basemesh, HumanObjectProperties)

        for target in TargetService.get_current_macro_targets(basemesh, decode_names=False):
            # print("Setting target to 0", target)
            basemesh.data.shape_keys.key_blocks[target].value = 0.0

        current_macro_targets = TargetService.get_current_macro_targets(basemesh, decode_names=True)
        required_macro_targets = TargetService.calculate_target_stack_from_macro_info_dict(macro_info)

        for target in required_macro_targets:
            requested = str(TargetService.macrodetail_filename_to_shapekey_name(target[0], encode_name=False)).strip()

            if requested not in current_macro_targets:
                to_load = os.path.join(_TARGETS_DIR,
                                       target[0] + ".target.gz")
                name = TargetService.macrodetail_filename_to_shapekey_name(to_load, encode_name=True)
                TargetService.load_target(basemesh, to_load, weight=0.0, name=name)

        for target in required_macro_targets:
            requested = str(TargetService.macrodetail_filename_to_shapekey_name(target[0], encode_name=True)).strip()
            TargetService.set_target_value(basemesh, requested, target[1])

        if not basemesh.data.shape_keys:
            print("Basemesh has no shape keys at this point. This is somewhat surprising.")

        if remove_zero_weight_targets and basemesh.data.shape_keys:
            # print("Checking for targets to remove")
            for shape_key in basemesh.data.shape_keys.key_blocks:
                # print("Checking shape key", (shape_key.name, shape_key.value))
                if str(shape_key.name).startswith("$md") and shape_key.value < 0.0001:
                    # print("Will remove macrodetail target", TargetService.decode_shapekey_name(shape_key.name))
                    basemesh.shape_key_remove(shape_key)

    @staticmethod
    def set_target_value(blender_object, target_name, value, delete_target_on_zero=False):
        if blender_object is None or target_name is None or not target_name:
            raise ValueError('Empty object or target')

        keys = blender_object.data.shape_keys

        if keys is None or keys.key_blocks is None or len(keys.key_blocks) < 1:
            raise ValueError('Empty object or target')

        for shape_key in keys.key_blocks:
            if shape_key.name == target_name:
                shape_key.value = value
                if value < 0.0001 and delete_target_on_zero:
                    blender_object.shape_key_remove(shape_key)

    @staticmethod
    def bulk_load_targets(blender_object, target_stack, encode_target_names=False):
        load_info = dict()
        load_info["parsed_target_stack"] = []

        for target in target_stack:
            target_full_path = TargetService.target_full_path(target["target"])
            # print(f'target full path_ {target_full_path}')

            if target_full_path:
                parsed_target = dict()
                parsed_target["full_path"] = target_full_path
                parsed_target["name"] = target["target"]
                parsed_target["value"] = target["value"]
                if str(target_full_path).endswith(".gz"):
                    with gzip.open(target_full_path, "rb") as gzip_file:
                        raw_data = gzip_file.read()
                        parsed_target["target_string"] = raw_data.decode('utf-8')
                else:
                    with open(target_full_path, "r") as target_file:
                        parsed_target["target_string"] = target_file.read()
                parsed_target["shape_key_name"] = TargetService.filename_to_shapekey_name(target_full_path)
                load_info["parsed_target_stack"].append(parsed_target)
            else:
                print("Skipping target because it could not be resolved to a path", target)

        for target_info in load_info["parsed_target_stack"]:
            shape_key = TargetService.target_string_to_shape_key(
                target_info["target_string"], target_info["shape_key_name"], blender_object)
            shape_key.value = target_info["value"]

    @staticmethod
    def target_full_path(target_name):
        targets_dir = _TARGETS_DIR

        for name in Path(targets_dir).rglob("*.target.gz"):
            bn = str(os.path.basename(name)).lower()
            if bn.startswith(str(target_name).lower()):
                return str(name)

    @staticmethod
    def load_target(blender_object, full_path, *, weight=0.0, name=None):
        if blender_object is None:
            raise ValueError("Can only load targets onto specified mesh objects")
        if full_path is None or not full_path:
            raise ValueError("Must specify a valid path - null or none was given")
        if not os.path.exists(full_path):
            raise IOError(full_path + " does not exist")
        target_string = None
        shape_key = None

        if name is None:
            name = TargetService.filename_to_shapekey_name(full_path)

        if str(full_path).endswith(".gz"):

            with gzip.open(full_path, "rb") as gzip_file:
                raw_data = gzip_file.read()
                target_string = raw_data.decode('utf-8')
        else:
            with open(full_path, "r") as target_file:
                target_string = target_file.read()

        if target_string is not None:
            shape_key = TargetService.target_string_to_shape_key(target_string, name, blender_object)
            shape_key.value = weight

        if not TargetService.shapekey_is_target(shape_key.name) and shape_key.name not in _ODD_TARGET_NAMES:
            _ODD_TARGET_NAMES.append(shape_key.name)

        return shape_key

    @staticmethod
    def shapekey_is_target(shapekey_name):
        """Guess if shape key is a target based on its name. This will catch the vast majority of all cases, but
        there are also fringe names and custom target which will not be identified correctly.
        Unfortunately, custom properties cannot be assigned to shapekeys, so there is no practical way to
        store additional metadata about a shapekey."""
        if not shapekey_name:
            return False
        if shapekey_name.lower() == "basis":
            return False
        if shapekey_name.startswith("$md"):
            return True
        for opposite in _OPPOSITES:
            if opposite in shapekey_name:
                return True
            (low, high) = opposite.split("-")
            if "-" + low in shapekey_name or "-" + high in shapekey_name:
                return True
        # Last resort since this array won't be populated if you load a blend file with previously loaded targets
        return shapekey_name in _ODD_TARGET_NAMES

    @staticmethod
    def target_string_to_shape_key(target_string, shape_key_name, blender_object, *, reuse_existing=False):
        if reuse_existing and shape_key_name in blender_object.data.shape_keys.key_blocks:
            shape_key = blender_object.data.shape_keys.key_blocks[shape_key_name]
        else:
            shape_key = TargetService.create_shape_key(blender_object, shape_key_name)

        shape_key_info = TargetService._target_string_to_shape_key_info(target_string, shape_key_name)

        TargetService._set_shape_key_coords_from_dict(blender_object, shape_key, shape_key_info)

        return shape_key

    @staticmethod
    def _set_shape_key_coords_from_dict(blender_object, shape_key, info, *, scale_factor=None):
        if scale_factor is None:
            scale_factor = GeneralObjectProperties.get_value("scale_factor", entity_reference=blender_object)
            if not scale_factor or scale_factor < 0.0001:
                scale_factor = 1.0

        basis = shape_key.relative_key

        if not basis:
            raise ValueError("Object does not have a Basis shape key")

        buffer = [0.0] * (len(shape_key.data) * 3)
        basis.data.foreach_get('co', buffer)

        for i, x, y, z in info["vertices"]:
            base = i * 3
            buffer[base] += x * scale_factor
            buffer[base + 1] += y * scale_factor
            buffer[base + 2] += z * scale_factor

        shape_key.data.foreach_set('co', buffer)

    @staticmethod
    def _target_string_to_shape_key_info(target_string, shape_key_name):
        info = dict()
        info["name"] = shape_key_name
        info["vertices"] = vertices = []

        lines = target_string.splitlines()

        for line in lines:
            target_line = str(line.strip())
            if target_line and not target_line.startswith("#") and not target_line.startswith("\""):
                parts = target_line.split(" ", 4)

                index = int(parts[0])
                x = float(parts[1])
                y = -float(parts[3])  # XZY order, -Y
                z = float(parts[2])

                vertices.append((index, x, y, z))

        return info

    @staticmethod
    def create_shape_key(blender_object, shape_key_name, also_create_basis=True, create_from_mix=False):
        assert blender_object.mode == "OBJECT"

        if also_create_basis:
            if not blender_object.data.shape_keys or "Basis" not in blender_object.data.shape_keys.key_blocks:
                blender_object.shape_key_add(name="Basis", from_mix=False)

        shape_key = blender_object.shape_key_add(name=shape_key_name, from_mix=create_from_mix)
        shape_key.value = 1.0

        shape_key_idx = blender_object.data.shape_keys.key_blocks.find(shape_key.name)
        blender_object.active_shape_key_index = shape_key_idx

        return shape_key

    @staticmethod
    def filename_to_shapekey_name(filename, *, macrodetail: bool | None = False, encode_name: bool | None = None):
        name = os.path.basename(filename)

        name = re.sub(r'\.gz$', "", name, flags=re.IGNORECASE)
        name = re.sub(r'\.p?target$', "", name, flags=re.IGNORECASE)

        if macrodetail is None:
            from pathlib import Path
            path_items = Path(os.path.abspath(filename)).parts
            macrodetail = _MACRO_PATH_PATTERN in '/'.join(path_items).lower()

        if macrodetail:
            name = "macrodetail-" + name
            if encode_name is None:
                encode_name = True

        if encode_name is None and len(name) > 60:
            encode_name = True

        if encode_name:
            name = TargetService.encode_shapekey_name(name)

        return name

    @staticmethod
    def macrodetail_filename_to_shapekey_name(filename, encode_name: bool = False):
        return TargetService.filename_to_shapekey_name(filename, macrodetail=True, encode_name=encode_name)

    @staticmethod
    def calculate_target_stack_from_macro_info_dict(macro_info, cutoff=0.01):
        if macro_info is None:
            macro_info = TargetService.get_default_macro_info_dict()

        components = dict()
        for macro_name in ["gender", "age", "muscle", "weight", "proportions", "height", "cupsize", "firmness"]:
            value = macro_info[macro_name]
            components[macro_name] = TargetService._interpolate_macro_components(macro_name, value)

        targets = []

        # Targets for race-gender-age
        for race in macro_info["race"].keys():
            # print("race", (race, macro_info["race"][race]))
            if macro_info["race"][race] > 0.0001:
                for age_component in components["age"]:
                    # print("age", age_component)
                    for gender_component in components["gender"]:
                        # print("gender", gender_component)
                        if gender_component[0] != "universal":
                            # print("components",
                            #       ([race, macro_info["race"][race]], gender_component, age_component))
                            complete_name = "macrodetails/" + race + "-" + gender_component[0] + "-" + age_component[0]
                            weight = macro_info["race"][race] * gender_component[1] * age_component[1]
                            if weight > cutoff:
                                # print("Appending race-gender-age target", [complete_name, weight])
                                targets.append([complete_name, weight])

        # Targets for (universal)-gender-age-muscle-weight
        for gender_component in components["gender"]:
            for age_component in components["age"]:
                for muscle_component in components["muscle"]:
                    for weight_component in components["weight"]:
                        complete_name = "macrodetails/universal"
                        complete_name = complete_name + "-" + gender_component[0]
                        complete_name = complete_name + "-" + age_component[0]
                        complete_name = complete_name + "-" + muscle_component[0]
                        complete_name = complete_name + "-" + weight_component[0]
                        weight = 1.0
                        weight = weight * gender_component[1]
                        weight = weight * age_component[1]
                        weight = weight * muscle_component[1]
                        weight = weight * weight_component[1]
                        if weight > cutoff:
                            # print("Appending universal-gender-age-muscle-weight target", [complete_name, weight])
                            targets.append([complete_name, weight])
                        else:
                            print("Not appending universal-gender-age-muscle-weight target",
                                  [complete_name, weight])

        # Targets for gender-age-muscle-weight-height
        for gender_component in components["gender"]:
            for age_component in components["age"]:
                for muscle_component in components["muscle"]:
                    for weight_component in components["weight"]:
                        for height_component in components["height"]:
                            complete_name = "macrodetails/height/"
                            complete_name = complete_name + gender_component[0]
                            complete_name = complete_name + "-" + age_component[0]
                            complete_name = complete_name + "-" + muscle_component[0]
                            complete_name = complete_name + "-" + weight_component[0]
                            complete_name = complete_name + "-" + height_component[0]
                            weight = 1.0
                            weight = weight * gender_component[1]
                            weight = weight * age_component[1]
                            weight = weight * muscle_component[1]
                            weight = weight * weight_component[1]
                            weight = weight * height_component[1]
                            if weight > cutoff:
                                # print("Appending gender-age-muscle-weight-height target", [complete_name, weight])
                                targets.append([complete_name, weight])
                            else:
                                print("Not appending gender-age-muscle-weight-height target",
                                      [complete_name, weight])

        # Targets for gender-age-muscle-weight-cupsize-firmness
        for gender_component in components["gender"]:
            if gender_component[0] == "female":
                for age_component in components["age"]:
                    for muscle_component in components["muscle"]:
                        for weight_component in components["weight"]:
                            for cup_component in components["cupsize"]:
                                for firmness_component in components["firmness"]:
                                    complete_name = "breast/"
                                    complete_name = complete_name + gender_component[0]
                                    complete_name = complete_name + "-" + age_component[0]
                                    complete_name = complete_name + "-" + muscle_component[0]
                                    complete_name = complete_name + "-" + weight_component[0]
                                    complete_name = complete_name + "-" + cup_component[0]
                                    complete_name = complete_name + "-" + firmness_component[0]
                                    weight = 1.0
                                    # weight = weight * gender_component[1]    <-- there are no male complementary targets
                                    weight = weight * age_component[1]
                                    weight = weight * muscle_component[1]
                                    weight = weight * weight_component[1]
                                    weight = weight * cup_component[1]
                                    weight = weight * firmness_component[1]
                                    # print("Breast target", complete_name)
                                    if weight > cutoff:
                                        if "averagecup-averagefirmness" in complete_name or "_baby_" in complete_name or "-baby-" in complete_name:
                                            print("Excluding forbidden breast modifier combination",
                                                  complete_name)
                                            print("Excluding forbidden breast modifier combination", complete_name)
                                        else:
                                            print("Appending gender-age-muscle-weight-cupsize-firmness target",
                                                  [complete_name, weight])
                                            print("Appending gender-age-muscle-weight-cupsize-firmness target",
                                                  [complete_name, weight])
                                            targets.append([complete_name, weight])
                                    # else:
                                    #     print("Not appending gender-age-muscle-weight-cupsize-firmness target",
                                    #           [complete_name, weight])

        # Targets for gender-age-muscle-weight-proportions
        for gender_component in components["gender"]:
            for age_component in components["age"]:
                for muscle_component in components["muscle"]:
                    for weight_component in components["weight"]:
                        for proportions_component in components["proportions"]:
                            complete_name = "macrodetails/proportions/"
                            complete_name = complete_name + gender_component[0]
                            complete_name = complete_name + "-" + age_component[0]
                            complete_name = complete_name + "-" + muscle_component[0]
                            complete_name = complete_name + "-" + weight_component[0]
                            complete_name = complete_name + "-" + proportions_component[0]
                            weight = 1.0
                            weight = weight * gender_component[1]
                            weight = weight * age_component[1]
                            weight = weight * muscle_component[1]
                            weight = weight * weight_component[1]
                            weight = weight * proportions_component[1]
                            if weight > cutoff:
                                print("Appending gender-age-muscle-weight-proportions target",
                                      [complete_name, weight])
                                targets.append([complete_name, weight])
                            else:
                                print("Not appending gender-age-muscle-weight-proportions target",
                                      [complete_name, weight])

        return targets

    @staticmethod
    def _interpolate_macro_components(macro_name, value):

        macrotarget = _MACRO_CONFIG["macrotargets"][macro_name]
        components = []

        for parts in macrotarget["parts"]:

            highest = parts["highest"]
            lowest = parts["lowest"]
            low = parts["low"]
            high = parts["high"]
            hlrange = highest - lowest

            if lowest < value < highest:
                position = value - lowest
                position_pct = position / hlrange
                lowweight = round(1 - position_pct, 4)
                highweight = round(position_pct, 4)

                if low:
                    components.append([low, round(lowweight, 4)])
                if high:
                    components.append([high, round(highweight, 4)])

        return components

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

    @staticmethod
    def get_macro_info_dict_from_basemesh(basemesh, HumanObjectProperties):
        return {
            "gender": HumanObjectProperties.get_value("gender", entity_reference=basemesh),
            "age": HumanObjectProperties.get_value("age", entity_reference=basemesh),
            "muscle": HumanObjectProperties.get_value("muscle", entity_reference=basemesh),
            "weight": HumanObjectProperties.get_value("weight", entity_reference=basemesh),
            "proportions": HumanObjectProperties.get_value("proportions", entity_reference=basemesh),
            "height": HumanObjectProperties.get_value("height", entity_reference=basemesh),
            "cupsize": HumanObjectProperties.get_value("cupsize", entity_reference=basemesh),
            "firmness": HumanObjectProperties.get_value("firmness", entity_reference=basemesh),
            "race": {
                "asian": HumanObjectProperties.get_value("asian", entity_reference=basemesh),
                "caucasian": HumanObjectProperties.get_value("caucasian", entity_reference=basemesh),
                "african": HumanObjectProperties.get_value("african", entity_reference=basemesh)
            }
        }

    @staticmethod
    def decode_shapekey_name(encoded_name):
        name = str(encoded_name)
        for code in _SHAPEKEY_ENCODING:
            name = name.replace(code[1], code[0])
        return name

    @staticmethod
    def encode_shapekey_name(original_name):
        name = str(original_name)
        for code in _SHAPEKEY_ENCODING:
            name = name.replace(code[0], code[1])
        return name

    @staticmethod
    def get_current_macro_targets(basemesh, decode_names=True):
        macro_targets = []
        if basemesh and basemesh.data.shape_keys and basemesh.data.shape_keys.key_blocks:
            for shape_key in basemesh.data.shape_keys.key_blocks:
                name = shape_key.name
                if decode_names:
                    name = TargetService.decode_shapekey_name(name)
                if str(shape_key.name).startswith("$md"):
                    macro_targets.append(name)

        return macro_targets
