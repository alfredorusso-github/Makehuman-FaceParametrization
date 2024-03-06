import bpy, os, json
from fnmatch import fnmatch
from bpy.props import BoolProperty, StringProperty, EnumProperty, IntProperty, CollectionProperty, FloatProperty, FloatVectorProperty

from ._configurationset import ConfigurationSet

_PREFIX = "MPFB_"


class BlenderConfigSet(ConfigurationSet):

    def __init__(self, properties, bpy_type, prefix="", *, lowercase_prefix=False):

        self._properties_by_short_name = dict()
        self._properties_by_full_name = dict()
        self._prop_to_aliases = dict()
        self._alias_to_prop = dict()
        self._prefix = (_PREFIX.lower() if lowercase_prefix else _PREFIX) + prefix
        self._bpytype = bpy_type

        for prop in properties:
            # print(prop)
            self.add_property(prop)

    def get_fullname_key_from_shortname_key(self, key_name):
        return self._prefix + key_name

    @staticmethod
    def get_definitions_in_json_directory(properties_dir):

        known_properties = []
        for file_name in os.listdir(properties_dir):

            if fnmatch(file_name, "*.json"):
                json_file_name = os.path.join(properties_dir, file_name)

                try:
                    with open(json_file_name) as json_file:
                        data = json.load(json_file)

                        known_properties.append(data)
                except Exception as e:
                    raise IOError("Failed to read properties from " + str(json_file))
        return known_properties

    def check_and_transform_entity_reference(self, entity_reference):
        if entity_reference is None:
            raise ValueError('Must provide a valid entity reference in order to read a BlenderConfigSet value')
        if not isinstance(entity_reference, self._bpytype):
            raise ValueError('This entity reference is not an instance of ' + str(self._bpytype.__name__))
        return entity_reference

    def get_value(self, name, default_value=None, entity_reference=None):

        entity_reference = self.check_and_transform_entity_reference(entity_reference)
        prop = None
        if name in self._properties_by_short_name:
            prop = self._properties_by_short_name[name]
        if name in self._properties_by_full_name:
            prop = self._properties_by_full_name[name]
        if prop is None:
            if name in self._alias_to_prop:
                real_name = self._alias_to_prop[name]
                prop = self._properties_by_full_name[real_name]
        if prop is None:
            return default_value
        full_name = prop["full_name"]

        try:
            if not hasattr(entity_reference, full_name):
                return default_value
        except Exception as e:
            return default_value

        # TODO: check if defined first. If not, check if any alias is defined
        return getattr(entity_reference, full_name)

    def set_value(self, name, value, entity_reference=None):
        entity_reference = self.check_and_transform_entity_reference(entity_reference)

        prop = None
        if name in self._properties_by_short_name:
            prop = self._properties_by_short_name[name]
        if name in self._properties_by_full_name:
            prop = self._properties_by_full_name[name]
        if prop is None:
            raise ValueError('This entity has no property matching ' + name)
        full_name = prop["full_name"]

        setattr(entity_reference, full_name, value)

        if full_name in self._prop_to_aliases:
            for alias in self._prop_to_aliases[full_name]:
                setattr(entity_reference, alias, value)


    def get_keys(self):
        return self._properties_by_short_name.keys()

    def has_key(self, name):
        return name in self._properties_by_full_name or name in self._properties_by_short_name or name in self._alias_to_prop

    def has_key_with_value(self, name, entity_reference=None):
        if not self.has_key(name):
            return False
        value = self.get_value(name, entity_reference=entity_reference)
        return not value is None

    def _create_property_by_type(self, proptype, name, description, default, items=None, items_callback=None, min=None, max=None):
        entity_property = None
        if proptype == "boolean":
            entity_property = BoolProperty(name=name, description=description, default=default) # pylint: disable=E1111
        if proptype == "string":
            entity_property = StringProperty(name=name, description=description, default=default) # pylint: disable=E1111
        if proptype == "int":
            entity_property = IntProperty(name=name, description=description, default=default) # pylint: disable=E1111
        if proptype == "float":
            if min is None:
                entity_property = FloatProperty(name=name, description=description, default=default) # pylint: disable=E1111
            else:
                entity_property = FloatProperty(name=name, description=description, default=default, min=min, max=max) # pylint: disable=E1111
        if proptype == "vector_location":
            entity_property = FloatVectorProperty(name=name, description=description, default=default,
                                                  size=3, subtype='XYZ', unit='LENGTH')
        if proptype == "enum":
            enumitems = []
            if items:
                for item in items:
                    enumitems.append(tuple(item))
            if not items_callback is None:
                enumitems = items_callback
            entity_property = EnumProperty( # pylint: disable=E1111
                name=name,
                description=description,
                default=default,
                items=enumitems)

        return entity_property

    def add_property(self, prop, items_callback=None):
        copied_property = dict(prop)
        copied_property["full_name"] = self._prefix + copied_property["name"]
        self._properties_by_full_name[copied_property["full_name"]] = copied_property
        self._properties_by_short_name[copied_property["name"]] = copied_property

        if "aliases" in prop:
            self._prop_to_aliases[copied_property["full_name"]] = prop["aliases"]
            for alias in prop["aliases"]:
                self._alias_to_prop[alias] = copied_property["full_name"]

        min = None
        max = None
        if "min" in copied_property:
            min = copied_property["min"]
        if "max" in copied_property:
            max = copied_property["max"]

        items = None
        if "items" in copied_property:
            items = copied_property["items"]
        entity_property = self._create_property_by_type(copied_property["type"], copied_property["full_name"], copied_property["description"], copied_property["default"], items, items_callback, min=min, max=max)

        setattr(self._bpytype, str(copied_property["full_name"]).strip(), entity_property)

        if "aliases" in prop:
            self._prop_to_aliases[copied_property["full_name"]] = prop["aliases"]
            for alias in prop["aliases"]:
                self._alias_to_prop[alias] = copied_property["full_name"]
                alias_property = self._create_property_by_type(copied_property["type"], alias, copied_property["description"], copied_property["default"], items, items_callback)
                setattr(self._bpytype, str(alias).strip(), alias_property)

    def _find_property(self, name):
        prop = None
        if name in self._properties_by_short_name:
            prop = self._properties_by_short_name[name]
        if name in self._properties_by_full_name:
            prop = self._properties_by_full_name[name]
        return prop

    def draw_properties(self, entity_reference, component_to_draw_on, property_names, *, text=None, **kwargs):
        if entity_reference is None:
            raise ValueError('Must provide a valid blender entity reference in order to draw properties')
        if component_to_draw_on is None:
            raise ValueError('Must provide a valid blender UI component, such as a box, in order to draw properties')
        if property_names is None or len(property_names) < 1:
            return

        for name in property_names:
            prop = self._find_property(name)

            if prop is None:
                print("Tried to draw a non-existing property", name)
            else:
                label = prop.get("label", "") if text is None else text
                component_to_draw_on.prop(entity_reference, prop["full_name"], text=label, **kwargs)

    def get_property_id_for_draw(self, name):
        prop = self._find_property(name)

        if prop is None:
            print("Tried to draw a non-existing property", name)
            return None

        return prop["full_name"]
