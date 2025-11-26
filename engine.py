"""
    KittenExport - Engine module
    Copyright (C) 2025  Marcus Zuber and contributors (https://github.com/MarcusZuber/kittenExport/graphs/contributors)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import bpy
import xml.etree.ElementTree as ET
import math
from .utils import _round_coordinate, _indent_xml, prop_with_unit


def _engine_dict_to_xml_element(parent, engine_data, decimal_places=3):
    """Convert a single engine dict to KSA-format XML element."""
    # Use object name as ID
    engine = ET.SubElement(parent, 'Engine', Id=engine_data.get('name', 'Unnamed'))

    # Location from absolute world position
    loc = engine_data.get('location', [0.0, 0.0, 0.0])
    if loc:
        rounded_loc = [_round_coordinate(v, decimal_places) for v in loc]
        ET.SubElement(engine, 'Location', X=str(rounded_loc[0]), Y=str(rounded_loc[1]), Z=str(rounded_loc[2]))

    # ExhaustDirection from object's absolute rotation (forward = +X axis after rotation)
    rotation = engine_data.get('rotation', [0.0, 0.0, 0.0])  # euler angles (x, y, z)
    if rotation:
        # Convert Euler angles to direction vector
        # Object's local +X axis after rotation
        cos_y = math.cos(rotation[1])
        sin_y = math.sin(rotation[1])
        cos_z = math.cos(rotation[2])
        sin_z = math.sin(rotation[2])

        # Forward vector (+X in local space) transformed by rotation
        ex_dir = [
            cos_y * cos_z,
            cos_y * sin_z,
            sin_y
        ]
    else:
        ex_dir = [1.0, 0.0, 0.0]  # default forward (+X)

    rounded_ex_dir = [_round_coordinate(v, decimal_places) for v in ex_dir]
    ET.SubElement(engine, 'ExhaustDirection', X=str(rounded_ex_dir[0]), Y=str(rounded_ex_dir[1]),
                  Z=str(rounded_ex_dir[2]))

    # Thrust with N attribute (convert kN to N by multiplying with 1000)
    thrust_kn = engine_data.get('thrust_kn', 650.0)
    thrust_n = thrust_kn * 1000.0
    ET.SubElement(engine, 'Thrust', N=str(thrust_n))

    # SpecificImpulse with Seconds attribute
    isp = engine_data.get('specific_impulse_seconds', 452.0)
    ET.SubElement(engine, 'SpecificImpulse', Seconds=str(isp))

    # MinimumThrottle with Value attribute
    min_throttle = engine_data.get('minimum_throttle', 0.05)
    ET.SubElement(engine, 'MinimumThrottle', Value=str(min_throttle))

    # VolumetricExhaust with Id attribute
    exhaust_id = engine_data.get('volumetric_exhaust_id', 'ApolloCSM')
    ET.SubElement(engine, 'VolumetricExhaust', Id=exhaust_id)

    # SoundEvent with Action and SoundId attributes
    sound_id = engine_data.get('sound_event_action_on', 'DefaultEngineSoundBehavior')
    ET.SubElement(engine, 'SoundEvent', Action='On', SoundId=sound_id)


def engines_list_to_xml_str(list_of_meta):
    """Export list of engines to KSA-compatible XML format."""
    root = ET.Element('Engines')
    for meta in list_of_meta:
        _engine_dict_to_xml_element(root, meta)
    _indent_xml(root)
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    return xml_str.replace('\n', '\r\n')


class EngineProperties(bpy.types.PropertyGroup):
    """Holds editable parameters for an 'Engine' object that will be used by the exporter."""
    thrust_kn: bpy.props.FloatProperty(
        name="Thrust",
        description="The force provided by the thruster firing in Kilonewtons.",
        default=850.0,
        min=0.00,
    )

    specific_impulse_seconds: bpy.props.FloatProperty(
        name="Specific Impulse",
        description="Specific impulse (Isp): \n Engine thrust divided by propellant weight (not mass) flowrate. \n Unit: [lbf]/([lbm]/[s]) = [s]·g0 = [s]",
        default=350.0,
        min=0.00,
    )

    minimum_throttle: bpy.props.FloatProperty(
        name="Minimum Throttle",
        description="Minimum throttle value (0-1)",
        default=0.10,
        min=0.00,
        max=1.00,
    )

    volumetric_exhaust_id: bpy.props.StringProperty(
        name="Volumetric exhaust",
        description="Volumetric exhaust effect to be used by the thurster when firing.",
        default="ApolloCSM"
    )

    sound_event_action_on: bpy.props.StringProperty(
        name="Sound",
        description="Sound effect to be used by the thurster when firing.",
        default="DefaultEngineSoundBehavior"
    )

    exportable: bpy.props.BoolProperty(
        name="Export",
        description="Include this object in custom exports.",
        default=True,
    )


class OBJECT_OT_add_engine(bpy.types.Operator):
    """Create an engine object (Empty with metadata)."""
    bl_idname = "object.add_engine"
    bl_label = "Add Engine"
    bl_description = "Create an engine object (Empty with metadata)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Create an Empty object to represent the engine
        obj = bpy.data.objects.new("Engine", None)

        # link to the active collection if available
        try:
            context.collection.objects.link(obj)
        except Exception:
            pass

        # Configure the Empty to display as a cone pointing along +X axis
        # This visually represents the engine exhaust direction
        try:
            obj.empty_display_type = 'CONE'
            obj.empty_display_size = 4                  # makes scale more appropriate

            # Rotate the cone to point along +X (engine exhaust direction)
            obj.rotation_euler = (0, 0, math.pi / 2)    # align engine thrust with -X direction
            obj.scale = (0.5, 2, 0.5)                   # better proportions
        except Exception:
            pass

        # Mark this as an engine object
        try:
            obj['_is_engine'] = True
            obj['_no_export'] = True
        except Exception:
            pass

        # Initialize engine_props (they get default values automatically)

        # Select and activate
        try:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
        except Exception:
            pass

        return {'FINISHED'}


class OBJECT_PT_engine_panel(bpy.types.Panel):
    """Display engine properties in the properties panel."""
    bl_label = "Engine Properties"
    bl_idname = "OBJECT_PT_engine_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data' # more intuitive location

    @classmethod
    def poll(cls, context):
        obj = getattr(context, 'object', None)
        if obj is None:
            return False
        # Only show panel for objects that are marked as engines
        return obj.get('_is_engine') is not None or obj.get('_engine_meta') is not None or obj.name.startswith('Engine')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        # Access engine_props
        props = obj.engine_props

        col = layout.column()
        prop_with_unit(col, props, "thrust_kn", "kN")
        prop_with_unit(col, props, "specific_impulse_seconds", "s")
        prop_with_unit(col, props, "minimum_throttle", "%")
        col.prop(props, "volumetric_exhaust_id")
        col.prop(props, "sound_event_action_on")
        col.prop(props, "exportable")
