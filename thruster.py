"""
    KittenExport - Thruster module
    Copyright (C) 2025  Marcus Zuber

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
from .utils import _round_coordinate, _safe_vector_to_list, _indent_xml, prop_with_unit


def _thruster_dict_to_xml_element(parent, thruster_data, decimal_places=3):
    """Convert a single thruster dict to the KSA-format XML element."""
    # Use object name as ID
    thruster = ET.SubElement(parent, 'Thruster', Id=thruster_data.get('name', 'Unnamed'))

    # Location from absolute world position + fx_location offset
    loc = thruster_data.get('location', [0.0, 0.0, 0.0])
    fx_offset = thruster_data.get('fx_location', [0.0, 0.0, 0.0])

    # Add the fx_location offset to the world position for particle origin
    if loc and fx_offset:
        final_loc = [loc[0] + fx_offset[0], loc[1] + fx_offset[1], loc[2] + fx_offset[2]]
    else:
        final_loc = loc

    if final_loc:
        rounded_loc = [_round_coordinate(v, decimal_places) for v in final_loc]
        ET.SubElement(thruster, 'Location', X=str(rounded_loc[0]), Y=str(rounded_loc[1]), Z=str(rounded_loc[2]))

    # ExhaustDirection from the object's absolute rotation (forward = +X axis after rotation)
    # The object's local +X axis in world space represents the exhaust direction
    rotation = thruster_data.get('rotation', [0.0, 0.0, 0.0])  # euler angles (x, y, z)
    if rotation:
        # Convert Euler angles to direction vector
        # Object's local +X axis after rotation
        cos_y = math.cos(rotation[1])
        sin_y = math.sin(rotation[1])
        cos_z = math.cos(rotation[2])
        sin_z = math.sin(rotation[2])
        cos_x = math.cos(rotation[0])
        sin_x = math.sin(rotation[0])

        # Forward vector (+X in local space) transformed by rotation
        ex_dir = [
            cos_y * cos_z,
            cos_y * sin_z,
            sin_y
        ]
    else:
        ex_dir = [1.0, 0.0, 0.0]  # default forward (+X)

    rounded_ex_dir = [_round_coordinate(v, decimal_places) for v in ex_dir]
    ET.SubElement(thruster, 'ExhaustDirection', X=str(rounded_ex_dir[0]), Y=str(rounded_ex_dir[1]),
                  Z=str(rounded_ex_dir[2]))

    # ControlMap CSV
    csv_parts = []
    trans_map = thruster_data.get('control_map_translation', [])
    rot_map = thruster_data.get('control_map_rotation', [])
    trans_labels = ["TranslateForward", "TranslateBackward", "TranslateLeft", "TranslateRight", "TranslateUp",
                    "TranslateDown"]
    rot_labels = ["PitchUp", "PitchDown", "RollLeft", "RollRight", "YawLeft", "YawRight"]

    if trans_map:
        for i, enabled in enumerate(trans_map):
            if enabled and i < len(trans_labels):
                csv_parts.append(trans_labels[i])
    if rot_map:
        for i, enabled in enumerate(rot_map):
            if enabled and i < len(rot_labels):
                csv_parts.append(rot_labels[i])

    # Always add the ControlMap element (even if empty)
    csv_value = ','.join(csv_parts) if csv_parts else ''
    ET.SubElement(thruster, 'ControlMap', CSV=csv_value)

    # Thrust with N attribute
    thrust = thruster_data.get('thrust_n', 40.0)
    ET.SubElement(thruster, 'Thrust', N=str(thrust))

    # SpecificImpulse with Seconds attribute
    isp = thruster_data.get('specific_impulse_seconds', 220.0)
    ET.SubElement(thruster, 'SpecificImpulse', Seconds=str(isp))

    # MinimumPulseTime with Seconds attribute
    min_pulse = thruster_data.get('minimum_pulse_time_seconds', 0.008)
    ET.SubElement(thruster, 'MinimumPulseTime', Seconds=str(min_pulse))

    # VolumetricExhaust with Id attribute
    exhaust_id = thruster_data.get('volumetric_exhaust_id', 'ApolloRCS')
    ET.SubElement(thruster, 'VolumetricExhaust', Id=exhaust_id)

    # SoundEvent with Action and SoundId attributes
    sound_id = thruster_data.get('sound_event_on', 'DefaultRcsThruster')
    ET.SubElement(thruster, 'SoundEvent', Action='On', SoundId=sound_id)


def thrusters_list_to_xml_str(list_of_meta):
    """Export the list of thrusters to KSA-compatible XML format."""
    root = ET.Element('Thrusters')
    for meta in list_of_meta:
        _thruster_dict_to_xml_element(root, meta)
    _indent_xml(root)
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    return xml_str.replace('\n', '\r\n')  # For windows compatibility


class ThrusterProperties(bpy.types.PropertyGroup):
    """Holds editable parameters for a 'Kitten' object that will be used by the exporter."""
    
    thrust_n: bpy.props.FloatProperty(
        name="Thrust",
        description="The force provided by the thruster firing in Newtons.",
        default=100,
        min=0.00,
    )
    specific_impulse_seconds: bpy.props.FloatProperty(
        name="Specific impulse",
        description="Specific impulse (Isp): \n Engine thrust divided by propellant weight (not mass) flowrate. \n Unit: [lbf]/([lbm]/[s]) = [s]·g0 = [s] ",
        default=280.0,
        min=0.00,
    )

    minimum_pulse_time_seconds: bpy.props.FloatProperty(
        name="Minimum pulse time",
        description="Shortest thruster firing time in seconds",
        default=0.5,
        min=0.00,
    )

    volumetric_exhaust_id: bpy.props.StringProperty(
        name="VolumetricExhaust_id",
        description="Volumetric exhaust effect to be used by the thurster when firing.",
        default="ApolloRCS"
    )

    sound_event_on: bpy.props.StringProperty(
        name="Sound effect",
        description="Sound effect to be used by the thurster when firing.",
        default="DefaultRcsThruster"
    )

    control_map_translation: bpy.props.BoolVectorProperty(
        name="control_map_translation",
        description="Set if thruster should fire on translation input. Do not select both option for the same direction.",
        default=[False, False, False, False, False, False],
        size=6
    )

    control_map_rotation: bpy.props.BoolVectorProperty(
        name="control_map_rotation",
        description="Set if thruster should fire on rotation input. Do not select both option for the same direction.",
        default=[False, False, False, False, False, False],
        size=6
    )

    fx_location: bpy.props.FloatVectorProperty(
        name="FxLocation",
        description="Offset of the thruster effect.",
        default=(0.0, 0.0, 0.0),
        size=3,                          # 3D vector
        subtype='TRANSLATION',           # <-- This gives X/Y/Z, use subtype='XYZ' if you only want generic XYZ fields
        unit='LENGTH'                    # <-- Uses scene length units (m, cm, etc.)
    )

    exportable: bpy.props.BoolProperty(
        name="Export",
        description="Include this object in custom exports.",
        default=True,
    )


class OBJECT_OT_add_thruster(bpy.types.Operator):
    """Create a thruster object (Empty with metadata)."""
    bl_idname = "object.add_thruster"
    bl_label = "Add Thruster"
    bl_description = "Create a thruster object (Empty with metadata)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Create an Empty object (not a mesh) to represent the thruster
        # Empty objects don't get rendered or exported by default
        obj = bpy.data.objects.new("Thruster", None)

        # link to the active collection if available
        try:
            context.collection.objects.link(obj)
        except Exception:
            # running outside Blender or collection not available in stub
            pass

        # Configure the Empty to display as an arrow pointing along +X axis
        # This visually represents the thruster direction
        try:
            obj.empty_display_type = 'SINGLE_ARROW'
            obj.empty_display_size = 2
            # Rotate the arrow to point along +X (thruster exhaust direction)
            # Default arrow points along +Z, so rotate -90° around Y axis
            obj.rotation_euler = (0, -math.pi / 2, 0)
        except Exception:
            pass

        # Mark this as a thruster object
        try:
            obj['_is_thruster'] = True
            obj['_no_export'] = True  # Empty objects won't be exported to GLB anyway
        except Exception:
            pass

        # Initialize thruster_props (they get default values automatically)
        # The metadata will be baked when the user exports or manually clicks "Bake"

        # Select and activate
        try:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
        except Exception:
            pass

        return {'FINISHED'}


class OBJECT_PT_thruster_panel(bpy.types.Panel):
    """Display thruster properties in the properties panel."""
    bl_label = "Thruster Properties"
    bl_idname = "OBJECT_PT_thruster_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data' # more intuitive location

    @classmethod
    def poll(cls, context):
        obj = getattr(context, 'object', None)
        if obj is None:
            return False
        # Only show panel for objects that are marked as thrusters
        return obj.get('_is_thruster') is not None or obj.get('_thruster_meta') is not None or obj.name.startswith(
            'Thruster')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        # Access thruster_props
        props = obj.thruster_props

        col = layout.column()
        # Basic properties
        prop_with_unit(col, props, "thrust_n", "N")
        prop_with_unit(col, props, "specific_impulse_seconds", "s")
        prop_with_unit(col, props, "minimum_pulse_time_seconds", "s")

        col.separator()

        col.prop(props, "volumetric_exhaust_id")
        col.prop(props, "sound_event_on")


class OBJECT_PT_thruster_panel_control(bpy.types.Panel):
    bl_label = "Thruster control map"
    bl_idname = "OBJECT_PT_thruster_panel_control"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'  

    @classmethod
    def poll(cls, context):
        obj = getattr(context, 'object', None)
        if obj is None:
            return False
        # Only show panel for objects that are marked as thrusters
        return obj.get('_is_thruster') is not None or obj.get('_thruster_meta') is not None or obj.name.startswith(
            'Thruster')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        # Access thruster_props
        props = obj.thruster_props
        
        col = layout.column()

        # ------------------------------------------
        # SIDE-BY-SIDE BOXES
        # ------------------------------------------
        row = col.row(align=True)

        # --- Left Box: Translation ---
        col_left = row.column(align=True)
        box = col_left.box()
        box.label(text="Translation")
        translation_labels = ["Forward", "Backward", "Left", "Right", "Up", "Down"]
        for i, label in enumerate(translation_labels):
            box.prop(props, "control_map_translation", index=i, text=label)

        # --- Right Box: Rotation ---
        col_right = row.column(align=True)
        box = col_right.box()
        box.label(text="Rotation")
        rotation_labels = ["Pitch Up", "Pitch Down", "Roll Left", "Roll Right", "Yaw Left", "Yaw Right"]
        for i, label in enumerate(rotation_labels):
            box.prop(props, "control_map_rotation", index=i, text=label)


class OBJECT_PT_thruster_panel_offset(bpy.types.Panel):
    bl_label = "Thruster effect offset"
    bl_idname = "OBJECT_PT_thruster_panel_offset"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'  

    @classmethod
    def poll(cls, context):
        obj = getattr(context, 'object', None)
        if obj is None:
            return False
        # Only show panel for objects that are marked as thrusters
        return obj.get('_is_thruster') is not None or obj.get('_thruster_meta') is not None or obj.name.startswith(
            'Thruster')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        # Access thruster_props
        props = obj.thruster_props
        
        col = layout.column()

        col.prop(props, "fx_location")

        col.separator()
        col.prop(props, "exportable")
