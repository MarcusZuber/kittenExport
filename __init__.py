"""
    KittenExport plugin for blender
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
import json
import xml.etree.ElementTree as ET


def _round_coordinate(value, decimal_places):
    """Round a coordinate value based on the number of decimal places.

    Args:
        value: The coordinate value to round
        decimal_places: Number of decimal places (e.g., 3 for 0.001 precision)

    Returns:
        Rounded value as float
    """
    return round(float(value), decimal_places)


def _thruster_dict_to_xml_element(parent, thruster_data, decimal_places=3):
    """Convert a single thruster dict to KSA-format XML element."""
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

    # ExhaustDirection from object's absolute rotation (forward = +X axis after rotation)
    # The object's local +X axis in world space represents the exhaust direction
    import math
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
    ET.SubElement(thruster, 'ExhaustDirection', X=str(rounded_ex_dir[0]), Y=str(rounded_ex_dir[1]), Z=str(rounded_ex_dir[2]))

    # ControlMap CSV
    csv_parts = []
    trans_map = thruster_data.get('control_map_translation', [])
    rot_map = thruster_data.get('control_map_rotation', [])
    trans_labels = ["TranslateForward", "TranslateBackward", "TranslateLeft", "TranslateRight", "TranslateUp", "TranslateDown"]
    rot_labels = ["PitchUp", "PitchDown", "RollLeft", "RollRight", "YawLeft", "YawRight"]

    if trans_map:
        for i, enabled in enumerate(trans_map):
            if enabled and i < len(trans_labels):
                csv_parts.append(trans_labels[i])
    if rot_map:
        for i, enabled in enumerate(rot_map):
            if enabled and i < len(rot_labels):
                csv_parts.append(rot_labels[i])

    # Always add ControlMap element (even if empty)
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
    import math
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
    ET.SubElement(engine, 'ExhaustDirection', X=str(rounded_ex_dir[0]), Y=str(rounded_ex_dir[1]), Z=str(rounded_ex_dir[2]))

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


def thrusters_list_to_xml_str(list_of_meta):
    """Export list of thrusters to KSA-compatible XML format."""
    root = ET.Element('Thrusters')
    for meta in list_of_meta:
        _thruster_dict_to_xml_element(root, meta)
    _indent_xml(root)
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    return xml_str.replace('\n', '\r\n')


def engines_list_to_xml_str(list_of_meta):
    """Export list of engines to KSA-compatible XML format."""
    root = ET.Element('Engines')
    for meta in list_of_meta:
        _engine_dict_to_xml_element(root, meta)
    _indent_xml(root)
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    return xml_str.replace('\n', '\r\n')


def meta_dict_to_xml_str(meta_dict):
    """Legacy function for backward compatibility - stores raw metadata."""
    root = ET.Element('metadata')
    for k, v in meta_dict.items():
        if isinstance(v, (list, tuple)):
            sub = ET.SubElement(root, k)
            for item in v:
                ET.SubElement(sub, 'item').text = str(item)
        else:
            ET.SubElement(root, k).text = str(v)
    return ET.tostring(root, encoding='utf-8').decode('utf-8')


def _element_to_dict(elem):
    d = {}
    for child in elem:
        if len(child):
            # has subelements
            tags = [c.tag for c in child]
            texts = [c.text for c in child]
            if set(tags) <= {'r', 'g', 'b'}:
                d[child.tag] = [float(t) for t in texts]
            elif set(tags) <= {'x', 'y', 'z'}:
                d[child.tag] = [float(t) for t in texts]
            else:
                # generic list
                vals = []
                for t in texts:
                    if t is None:
                        vals.append(None)
                    else:
                        try:
                            if '.' in t:
                                vals.append(float(t))
                            else:
                                vals.append(int(t))
                        except Exception:
                            if t.lower() in ('true', 'false'):
                                vals.append(t.lower() == 'true')
                            else:
                                vals.append(t)
                d[child.tag] = vals
        else:
            t = child.text
            if t is None:
                d[child.tag] = None
            else:
                if t.lower() in ('true', 'false'):
                    d[child.tag] = t.lower() == 'true'
                else:
                    try:
                        if '.' in t:
                            d[child.tag] = float(t)
                        else:
                            d[child.tag] = int(t)
                    except Exception:
                        d[child.tag] = t
    return d


def parse_meta_string(s):
    if not s:
        return None
    s = s.strip()
    # try XML first
    if s.startswith('<'):
        try:
            root = ET.fromstring(s)
            if root.tag == 'thruster':
                return _element_to_dict(root)
            # if it's a list wrapper, return list
            if root.tag == 'thrusters':
                return [_element_to_dict(child) for child in root]
        except Exception:
            pass
    # fallback: try JSON
    try:
        return json.loads(s)
    except Exception:
        return None


def _safe_vector_to_list(vec_prop):
    """Safely convert a Blender vector property to a Python list."""
    try:
        # Try direct conversion first
        return list(vec_prop)
    except TypeError:
        # If that fails, try accessing as an array-like object
        try:
            return [vec_prop[i] for i in range(len(vec_prop))]
        except Exception:
            # Last resort: try iteration
            try:
                return [x for x in vec_prop]
            except Exception:
                return None


def sanitize_filename(name: str) -> str:
    """Sanitize object or image names for safe filesystem usage.
    Replaces disallowed characters with underscore and trims length. Guarantees non-empty.
    """
    import re
    if not name:
        return "unnamed"
    # Replace path separators and any char not in whitelist with '_'
    cleaned = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    # Avoid leading dots (hidden files on some OS)
    cleaned = cleaned.lstrip('.')
    if not cleaned:
        cleaned = 'unnamed'
    # Trim very long names to a reasonable length
    if len(cleaned) > 128:
        cleaned = cleaned[:128]
    return cleaned


bl_info = {
    "name": "Kitten export",
    "blender": (4, 50, 0),
    "category": ["Add Mesh", "Import-Export"],
}


class ThrusterProperties(bpy.types.PropertyGroup):
    """Holds editable parameters for a 'Kitten' object that will be used by the exporter."""
    fx_location: bpy.props.FloatVectorProperty(
        name="FxLocation",
        description="Origin of the thruster effect",
        default=(0.0, 0.0, 0.0),
    )
    thrust_n: bpy.props.FloatProperty(
        name="Thrust N",
        description="?",
        default=40,
        min=0.00,
    )
    specific_impulse_seconds: bpy.props.FloatProperty(
        name="Specific impulse seconds",
        description="?",
        default=0.0,
        min=0.00,
    )

    minimum_pulse_time_seconds: bpy.props.FloatProperty(
        name="Minimum pulse time seconds",
        description="?",
        default=0.0,
        min=0.00,
    )

    volumetric_exhaust_id: bpy.props.StringProperty(
        name="VolumetricExhaust_id",
        description="",
        default="ApolloRCS"
    )

    sound_event_on: bpy.props.StringProperty(
        name="Sound event on",
        description="",
        default="DefaultRcsThruster"
    )

    control_map_translation: bpy.props.BoolVectorProperty(
        name="control_map_translation",
        description="Set if thruster should fire on translation input. [TranslateForward, TranslateBackward, TranslateLeft, TranslateRight, TranslateUp, TranslateDown]",
        default=[False, False, False, False, False, False],
        size=6
    )

    control_map_rotation: bpy.props.BoolVectorProperty(
        name="control_map_rotation",
        description="Set if thruster should fire on rotation input. [PitchUp, PitchDown, RollLeft, RollRight, YawLeft, YawRight]",
        default=[False, False, False, False, False, False],
        size=6
    )

    exportable: bpy.props.BoolProperty(
        name="Export",
        description="Include this object in custom exports",
        default=True,
    )


class EngineProperties(bpy.types.PropertyGroup):
    """Holds editable parameters for an 'Engine' object that will be used by the exporter."""
    thrust_kn: bpy.props.FloatProperty(
        name="Thrust kN",
        description="Engine thrust in kilonewtons",
        default=650.0,
        min=0.00,
    )

    specific_impulse_seconds: bpy.props.FloatProperty(
        name="Specific Impulse Seconds",
        description="Specific impulse in seconds",
        default=10000.0,
        min=0.00,
    )

    minimum_throttle: bpy.props.FloatProperty(
        name="Minimum Throttle",
        description="Minimum throttle value (0-1)",
        default=0.05,
        min=0.00,
        max=1.00,
    )

    volumetric_exhaust_id: bpy.props.StringProperty(
        name="VolumetricExhaust_id",
        description="",
        default="ApolloCSM"
    )

    sound_event_action_on: bpy.props.StringProperty(
        name="SoundEventAction_On",
        description="",
        default="DefaultEngineSoundBehavior"
    )

    exportable: bpy.props.BoolProperty(
        name="Export",
        description="Include this object in custom exports",
        default=True,
    )


class OBJECT_OT_export_ksa_metadata(bpy.types.Operator):
    bl_idname = "export_scene.ksa_metadata"
    bl_label = "Export KSA Part"
    bl_description = "Export thrusters, engines, meshes, materials into part.xml with Meshes/ and Textures/ subfolders"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(
        name="Directory",
        description="Target directory. part.xml plus Meshes/ and Textures/ will be created inside it.",
        default="",
        subtype='DIR_PATH',
    )

    filter_glob: bpy.props.StringProperty(
        default="*",
        options={'HIDDEN'},
    )
    part_id: bpy.props.StringProperty(
        name="Part ID",
        description="Identifier used for the <Part Id=...> element in the XML",
        default="MyRocket",
    )

    coordinate_decimal_places: bpy.props.IntProperty(
        name="Coordinate Decimal Places",
        description="Number of decimal places for coordinates in the XML export (e.g., 3 for 0.001 precision)",
        default=3,
        min=0,
        max=10,
    )

    def invoke(self, context, event):
        try:
            # Suggest current working directory; user picks folder
            self.filepath = bpy.path.abspath('//') if hasattr(bpy.path, 'abspath') else ""
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        except Exception:
            return self.execute(context)

    def draw(self, context):
        """Draw custom properties in the file selector dialog."""
        layout = self.layout
        layout.prop(self, "part_id")
        layout.prop(self, "coordinate_decimal_places")

    def execute(self, context):
        scene = getattr(context, 'scene', None)
        if scene is None:
            self.report({'ERROR'}, "No scene found")
            return {'CANCELLED'}

        # Collect thrusters
        thrusters = []
        for obj in scene.objects:
            if obj.get('_is_thruster') is None and not obj.name.startswith('Thruster'):
                continue
            tp = getattr(obj, 'thruster_props', None)
            if tp is None or not getattr(tp, 'exportable', False):
                continue
            entry = {
                'name': obj.name,
                'location': list(obj.location) if obj.location is not None else None,
                'rotation': list(obj.rotation_euler) if obj.rotation_euler is not None else None,
                'fx_location': _safe_vector_to_list(tp.fx_location),
                'thrust_n': tp.thrust_n,
                'specific_impulse_seconds': tp.specific_impulse_seconds,
                'minimum_pulse_time_seconds': tp.minimum_pulse_time_seconds,
                'volumetric_exhaust_id': tp.volumetric_exhaust_id,
                'sound_event_on': tp.sound_event_on,
                'control_map_translation': _safe_vector_to_list(tp.control_map_translation),
                'control_map_rotation': _safe_vector_to_list(tp.control_map_rotation),
                'exportable': tp.exportable,
            }
            thrusters.append(entry)

        # Collect engines
        engines = []
        for obj in scene.objects:
            if obj.get('_is_engine') is None and not obj.name.startswith('Engine'):
                continue
            ep = getattr(obj, 'engine_props', None)
            if ep is None or not getattr(ep, 'exportable', False):
                continue
            entry = {
                'name': obj.name,
                'location': list(obj.location) if obj.location is not None else None,
                'rotation': list(obj.rotation_euler) if obj.rotation_euler is not None else None,
                'thrust_kn': ep.thrust_kn,
                'specific_impulse_seconds': ep.specific_impulse_seconds,
                'minimum_throttle': ep.minimum_throttle,
                'volumetric_exhaust_id': ep.volumetric_exhaust_id,
                'sound_event_action_on': ep.sound_event_action_on,
                'exportable': ep.exportable,
            }
            engines.append(entry)

        # Determine base directory, throws an exception if invalid
        import os
        base_dir = self.filepath if os.path.isdir(self.filepath) else (os.path.dirname(self.filepath))

        meshes_dir = os.path.join(base_dir, 'Meshes')
        textures_dir = os.path.join(base_dir, 'Textures')
        try:
            os.makedirs(meshes_dir, exist_ok=True)
        except Exception:
            meshes_dir = base_dir
        try:
            os.makedirs(textures_dir, exist_ok=True)
        except Exception:
            textures_dir = None

        # Collect mesh objects (exclude thrusters/engines/_no_export)
        mesh_objects = []
        for obj in scene.objects:
            if getattr(obj, 'type', '') != 'MESH':
                continue
            if obj.get('_no_export') or obj.get('_is_thruster') or obj.get('_is_engine'):
                continue
            mesh_objects.append(obj)

        # Unique filenames for meshes
        used_names = set()
        mesh_export_info = []  # (obj, glb_path, mesh_id)
        for obj in mesh_objects:
            safe_name = sanitize_filename(obj.name) or 'mesh'
            candidate = safe_name
            idx = 1
            while candidate.lower() in used_names:
                candidate = f"{safe_name}_{idx}"
                idx += 1
            used_names.add(candidate.lower())
            mesh_file_name = f"{candidate}.glb"
            glb_path = os.path.join(meshes_dir, mesh_file_name)
            mesh_id = f"{candidate}MeshFile"  # append MeshFile suffix for ID uniqueness
            mesh_export_info.append((obj, glb_path, mesh_file_name, mesh_id))

        # Preserve selection
        prev_selected = [o for o in getattr(context, 'selected_objects', [])]
        prev_active = getattr(context.view_layer.objects, 'active', None)

        exported_mesh_count = 0
        for obj, path, _, _ in mesh_export_info:
            try:
                bpy.ops.object.select_all(action='DESELECT')
            except Exception:
                pass
            try:
                obj.select_set(True)
                context.view_layer.objects.active = obj
            except Exception:
                continue
            try:
                bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True)
                exported_mesh_count += 1
            except Exception:
                continue

        # Restore selection
        try:
            bpy.ops.object.select_all(action='DESELECT')
        except Exception:
            pass
        for o in prev_selected:
            try:
                o.select_set(True)
            except Exception:
                pass
        try:
            if prev_active is not None:
                context.view_layer.objects.active = prev_active
        except Exception:
            pass

        # Collect materials used by mesh objects
        materials = set()
        for obj in mesh_objects:
            for slot in getattr(obj, 'material_slots', []) or []:
                mat = getattr(slot, 'material', None)
                if mat is not None:
                    materials.add(mat)

        # Build material maps and export texture files (PNG) with suffixes
        material_infos = []  # (mat, maps_dict, material_id)
        exported_texture_count = 0
        for mat in materials:
            maps = _extract_material_maps(mat)
            if not maps:
                # still include material without textures
                material_id = f"{sanitize_filename(mat.name)}TextureFile" if mat.name else 'MaterialTextureFile'
                material_infos.append((mat, maps, material_id))
                continue
            material_id = f"{sanitize_filename(mat.name)}TextureFile" if mat.name else 'MaterialTextureFile'
            # Export each identified map under standardized filenames
            for key, img in maps.items():
                if textures_dir is None or img is None:
                    continue
                suffix = 'Diffuse' if key == 'diffuse' else ('Normal' if key == 'normal' else 'RoughMetaAo')
                file_name = f"{sanitize_filename(mat.name)}_{suffix}.png" if mat.name else f"material_{suffix}.png"
                out_path = os.path.join(textures_dir, file_name)
                if not os.path.exists(out_path):
                    saved = False
                    try:
                        if hasattr(img, 'save_render'):
                            img.save_render(out_path)
                            saved = True
                        elif hasattr(img, 'save'):  # try original or direct save
                            if hasattr(img, 'filepath_raw') and img.filepath_raw and os.path.exists(img.filepath_raw):
                                import shutil
                                shutil.copy2(img.filepath_raw, out_path)
                                saved = True
                            if not saved:
                                img.save(out_path)
                                saved = True
                    except Exception:
                        saved = False
                    if not saved:
                        try:
                            src_fallback = getattr(img, 'filepath', '') or getattr(img, 'filepath_raw', '')
                            if src_fallback and os.path.exists(src_fallback):
                                import shutil
                                shutil.copy2(src_fallback, out_path)
                                saved = True
                        except Exception:
                            pass
                    if saved:
                        exported_texture_count += 1
            material_infos.append((mat, maps, material_id))

        # Construct new XML structure
        root = ET.Element('Assets')  # top-level container

        # MeshFile entries
        for obj, _, mesh_file_name, mesh_id in mesh_export_info:
            ET.SubElement(root, 'MeshFile', Id=obj.name + 'MeshFile', Path=f"Meshes/{mesh_file_name}", Category='Vessel')

        # PbrMaterial entries
        for mat, maps, material_id in material_infos:
            mat_elem = ET.SubElement(root, 'PbrMaterial', Id=material_id)
            # Diffuse
            if 'diffuse' in maps and textures_dir:
                diffuse_file = f"{sanitize_filename(mat.name)}_Diffuse.png"
                ET.SubElement(mat_elem, 'Diffuse', Path=f"Textures/{diffuse_file}", Category='Vessel')
            # Normal
            if 'normal' in maps and textures_dir:
                normal_file = f"{sanitize_filename(mat.name)}_Normal.png"
                ET.SubElement(mat_elem, 'Normal', Path=f"Textures/{normal_file}", Category='Vessel')
            # RoughMetaAo
            if 'roughmetaao' in maps and textures_dir:
                rma_file = f"{sanitize_filename(mat.name)}_RoughMetaAo.png"
                ET.SubElement(mat_elem, 'RoughMetaAo', Path=f"Textures/{rma_file}", Category='Vessel')

        # Part block (single vessel part). Use user-specified part_id or fallback
        part_id = sanitize_filename(self.part_id) or 'Vessel'
        part_elem = ET.SubElement(root, 'Part', Id=part_id)

        # Add mesh subparts
        for obj, _, mesh_file_name, mesh_id in mesh_export_info:
            sub_part = ET.SubElement(part_elem, 'SubPart', Id=obj.name)
            sp_model = ET.SubElement(sub_part, 'SubPartModel', Id=f"{sanitize_filename(obj.name)}Model")
            # Mesh reference
            ET.SubElement(sp_model, 'Mesh', Id=obj.name + 'MeshFile')
            # Choose first material slot's material id if exists
            first_mat = None
            for slot in getattr(obj, 'material_slots', []) or []:
                m = getattr(slot, 'material', None)
                if m is not None:
                    first_mat = m
                    break
            if first_mat is not None:
                mat_id = f"{sanitize_filename(first_mat.name)}TextureFile"
                ET.SubElement(sp_model, 'Material', Id=mat_id)

        # Add thruster subparts
        for thruster_data in thrusters:
            # Previously each thruster was wrapped in a SubPart; now we place it directly under Part.
            _thruster_dict_to_xml_element(part_elem, thruster_data, self.coordinate_decimal_places)
        # Add engines directly under Part (no SubPart wrapper)
        for engine_data in engines:
            _engine_dict_to_xml_element(part_elem, engine_data, self.coordinate_decimal_places)

        # Serialize XML (pretty + CRLF)
        _indent_xml(root)
        xml_text = ET.tostring(root, encoding='utf-8').decode('utf-8').replace('\n', '\r\n')
        xml_out_path = os.path.join(base_dir, 'part.xml')
        try:
            with open(xml_out_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\r\n')
                f.write(xml_text)
        except Exception as e:
            self.report({'ERROR'}, f"XML write failed: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Exported {exported_mesh_count} meshes, {len(material_infos)} materials, {len(thrusters)} thrusters, {len(engines)} engines. XML: {xml_out_path}")
        return {'FINISHED'}


class OBJECT_OT_add_thruster(bpy.types.Operator):
    bl_idname = "object.add_thruster"
    bl_label = "Add Thruster"
    bl_description = "Create a thruster object (Empty with metadata)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Create an Empty object (not a mesh) to represent the thruster
        # Empty objects don't get rendered or exported by default
        obj = bpy.data.objects.new("Thruster", None)

        # link to active collection if available
        try:
            context.collection.objects.link(obj)
        except Exception:
            # running outside Blender or collection not available in stub
            pass

        # Configure the Empty to display as an arrow pointing along +X axis
        # This visually represents the thruster direction
        try:
            obj.empty_display_type = 'SINGLE_ARROW'
            obj.empty_display_size = 0.3
            # Rotate the arrow to point along +X (thruster exhaust direction)
            # Default arrow points along +Z, so rotate -90° around Y axis
            import math
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


class OBJECT_OT_add_engine(bpy.types.Operator):
    bl_idname = "object.add_engine"
    bl_label = "Add Engine"
    bl_description = "Create an engine object (Empty with metadata)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Create an Empty object to represent the engine
        obj = bpy.data.objects.new("Engine", None)

        # link to active collection if available
        try:
            context.collection.objects.link(obj)
        except Exception:
            pass

        # Configure the Empty to display as a cone pointing along +X axis
        # This visually represents the engine exhaust direction
        try:
            obj.empty_display_type = 'CONE'
            obj.empty_display_size = 0.5
            # Rotate the cone to point along +X (engine exhaust direction)
            import math
            obj.rotation_euler = (0, -math.pi / 2, 0)
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


class OBJECT_PT_thruster_panel(bpy.types.Panel):
    bl_label = "Thruster Properties"
    bl_idname = "OBJECT_PT_thruster_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

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
        col.prop(props, "fx_location")
        col.prop(props, "thrust_n")
        col.prop(props, "specific_impulse_seconds")
        col.prop(props, "minimum_pulse_time_seconds")
        col.prop(props, "volumetric_exhaust_id")
        col.prop(props, "sound_event_on")

        # Translation control mapping with labels
        col.separator()
        box = col.box()
        box.label(text="Translation Control Map:")
        translation_labels = ["Forward", "Backward", "Left", "Right", "Up", "Down"]
        for i, label in enumerate(translation_labels):
            box.prop(props, "control_map_translation", index=i, text=label)

        # Rotation control mapping with labels
        col.separator()
        box = col.box()
        box.label(text="Rotation Control Map:")
        rotation_labels = ["Pitch Up", "Pitch Down", "Roll Left", "Roll Right", "Yaw Left", "Yaw Right"]
        for i, label in enumerate(rotation_labels):
            box.prop(props, "control_map_rotation", index=i, text=label)

        col.separator()
        col.prop(props, "exportable")



class OBJECT_PT_engine_panel(bpy.types.Panel):
    bl_label = "Engine Properties"
    bl_idname = "OBJECT_PT_engine_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

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
        col.prop(props, "thrust_kn")
        col.prop(props, "specific_impulse_seconds")
        col.prop(props, "minimum_throttle")
        col.prop(props, "volumetric_exhaust_id")
        col.prop(props, "sound_event_action_on")
        col.prop(props, "exportable")


# Old operator classes below are not registered and should be removed eventually
class OBJECT_OT_export_thrusters_OLD(bpy.types.Operator):
    bl_label = "Export Selected Thrusters"
    bl_description = "Collect Thruster parameters from selected objects and export them as JSON"

    filepath = bpy.props.StringProperty(
        name="Filepath",
        description="Where to write the JSON export. If empty, print to console.",
        default="",
    )

    def invoke(self, context, event):
        # Open Blender file selector so user can pick a filepath (works in Blender)
        try:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        except Exception:
            # not running in Blender - fallback to execute
            return self.execute(context)

    def execute(self, context):
        data = []
        for obj in getattr(context, 'selected_objects', []):
            kp = getattr(obj, 'thruster_props', None)
            if kp is None:
                continue
            # skip objects marked non-exportable
            if not getattr(kp, 'exportable', False):
                continue
            entry = {
                'name': getattr(obj, 'name', ''),
                'location': list(obj.location) if obj.location is not None else None,
                'rotation': list(obj.rotation_euler) if obj.rotation_euler is not None else None,
                'fx_location': _safe_vector_to_list(kp.fx_location),
                'thrust_n': kp.thrust_n,
                'specific_impulse_seconds': kp.specific_impulse_seconds,
                'minimum_pulse_time_seconds': kp.minimum_pulse_time_seconds,
                'volumetric_exhaust_id': kp.volumetric_exhaust_id,
                'sound_event_on': kp.sound_event_on,
                'control_map_translation': _safe_vector_to_list(kp.control_map_translation),
                'control_map_rotation': _safe_vector_to_list(kp.control_map_rotation),
                'exportable': kp.exportable,
            }
            data.append(entry)

        # write XML instead of JSON
        xml_text = thrusters_list_to_xml_str(data)

        if getattr(self, 'filepath', ''):
            try:
                # if filepath ends with .json replace with .xml
                path = self.filepath
                if path.lower().endswith('.json'):
                    path = path[:-5] + '.xml'
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(xml_text)
                self.report({'INFO'}, f"Exported {len(data)} items to {path}")
            except Exception as e:
                try:
                    self.report({'ERROR'}, str(e))
                except Exception:
                    pass
                return {'CANCELLED'}
        else:
            try:
                print("Thruster export (XML):\n", xml_text)
                self.report({'INFO'}, f"Prepared export for {len(data)} objects (printed to console)")
            except Exception:
                pass

        return {'FINISHED'}


class OBJECT_OT_bake_thruster_meta(bpy.types.Operator):
    bl_idname = "object.bake_thruster_meta"
    bl_label = "Bake Thruster Metadata"
    bl_description = "Write thruster properties into the object's custom property for external exporters"

    def execute(self, context):
        count = 0
        for obj in getattr(context, 'selected_objects', []):
            kp = getattr(obj, 'thruster_props', None)
            if kp is None:
                continue
            try:
                meta = {
                    'name': obj.name,
                    'thrust_n': kp.thrust_n,
                    'specific_impulse_seconds': kp.specific_impulse_seconds,
                    'minimum_pulse_time_seconds': kp.minimum_pulse_time_seconds,
                    'volumetric_exhaust_id': kp.volumetric_exhaust_id,
                    'sound_event_on': kp.sound_event_on,
                    'control_map_translation': _safe_vector_to_list(kp.control_map_translation),
                    'control_map_rotation': _safe_vector_to_list(kp.control_map_rotation),
                    'exportable': kp.exportable,
                    'location': list(obj.location) if obj.location is not None else None,
                }
                obj['_thruster_meta'] = meta_dict_to_xml_str(meta)
                obj['_no_export'] = True
                count += 1
            except Exception:
                pass
        self.report({'INFO'}, f"Baked metadata for {count} objects")
        return {'FINISHED'}


class OBJECT_OT_export_engines(bpy.types.Operator):
    bl_idname = "object.export_engines"
    bl_label = "Export Selected Engines"
    bl_description = "Collect Engine parameters from selected objects and export them as XML"

    filepath: bpy.props.StringProperty(
        name="Filepath",
        description="Where to write the XML export. If empty, print to console.",
        default="",
    )

    def invoke(self, context, event):
        try:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        except Exception:
            return self.execute(context)

    def execute(self, context):
        data = []
        for obj in getattr(context, 'selected_objects', []):
            ep = getattr(obj, 'engine_props', None)
            if ep is None:
                continue
            # skip objects marked non-exportable
            if not getattr(ep, 'exportable', False):
                continue
            entry = {
                'name': getattr(obj, 'name', ''),
                'location': list(obj.location) if obj.location is not None else None,
                'rotation': list(obj.rotation_euler) if obj.rotation_euler is not None else None,
                'thrust_kn': ep.thrust_kn,
                'specific_impulse_seconds': ep.specific_impulse_seconds,
                'minimum_throttle': ep.minimum_throttle,
                'volumetric_exhaust_id': ep.volumetric_exhaust_id,
                'sound_event_action_on': ep.sound_event_action_on,
                'exportable': ep.exportable,
            }
            data.append(entry)

        # write XML
        xml_text = engines_list_to_xml_str(data)  # use engine-specific function

        if getattr(self, 'filepath', ''):
            try:
                path = self.filepath
                if path.lower().endswith('.json'):
                    path = path[:-5] + '.xml'
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(xml_text)
                self.report({'INFO'}, f"Exported {len(data)} engine items to {path}")
            except Exception as e:
                try:
                    self.report({'ERROR'}, str(e))
                except Exception:
                    pass
                return {'CANCELLED'}
        else:
            try:
                print("Engine export (XML):\n", xml_text)
                self.report({'INFO'}, f"Prepared export for {len(data)} engine objects (printed to console)")
            except Exception:
                pass

        return {'FINISHED'}


class OBJECT_OT_bake_engine_meta(bpy.types.Operator):
    bl_idname = "object.bake_engine_meta"
    bl_label = "Bake Engine Metadata"
    bl_description = "Write engine properties into the object's custom property for external exporters"

    def execute(self, context):
        count = 0
        for obj in getattr(context, 'selected_objects', []):
            ep = getattr(obj, 'engine_props', None)
            if ep is None:
                continue
            try:
                meta = {
                    'name': obj.name,
                    'thrust_kn': ep.thrust_kn,
                    'specific_impulse_seconds': ep.specific_impulse_seconds,
                    'minimum_throttle': ep.minimum_throttle,
                    'volumetric_exhaust_id': ep.volumetric_exhaust_id,
                    'sound_event_action_on': ep.sound_event_action_on,
                    'exportable': ep.exportable,
                    'location': list(obj.location) if obj.location is not None else None,
                }
                obj['_engine_meta'] = meta_dict_to_xml_str(meta)
                obj['_no_export'] = True
                count += 1
            except Exception:
                pass
        self.report({'INFO'}, f"Baked engine metadata for {count} objects")
        return {'FINISHED'}


class OBJECT_OT_export_glb_with_meta(bpy.types.Operator):
    bl_idname = "export.glb_with_meta"
    bl_label = "Export GLB + Thruster Metadata"
    bl_description = "Export scene to GLB excluding thruster objects and write thruster metadata JSON"

    filepath = bpy.props.StringProperty(
        name="Filepath",
        description="GLB output path",
        subtype='FILE_PATH',
        default="",
    )

    def invoke(self, context, event):
        try:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        except Exception:
            return self.execute(context)

    def execute(self, context):
        scene = getattr(context, 'scene', None)
        if scene is None:
            self.report({'ERROR'}, "No scene found")
            return {'CANCELLED'}

        # Collect thruster objects (those with baked meta or thruster_props)
        thrusters = [o for o in scene.objects if
                     (o.get('_thruster_meta') is not None) or (getattr(o, 'thruster_props', None) is not None)]
        non_thrusters = [o for o in scene.objects if o not in thrusters]

        # Save current selection and active
        prev_selected = [o for o in context.selected_objects]
        prev_active = getattr(context.view_layer, 'objects', None) and context.view_layer.objects.active

        try:
            # Select only non-thruster objects for export
            try:
                bpy.ops.object.select_all(action='DESELECT')
            except Exception:
                pass
            for o in non_thrusters:
                try:
                    o.select_set(True)
                except Exception:
                    pass
            if non_thrusters:
                try:
                    context.view_layer.objects.active = non_thrusters[0]
                except Exception:
                    pass

            # Export GLB (using Blender glTF exporter)
            try:
                bpy.ops.export_scene.gltf(filepath=self.filepath, export_format='GLB', use_selection=True)
            except Exception as e:
                self.report({'ERROR'}, f"GLB export failed: {e}")
                return {'CANCELLED'}

            # Build metadata list for thrusters
            meta_list = []
            for o in thrusters:
                jm = o.get('_thruster_meta')
                if jm:
                    parsed = parse_meta_string(jm)
                    if isinstance(parsed, dict):
                        meta_list.append(parsed)
                        continue
                    elif isinstance(parsed, list):
                        meta_list.extend(parsed)
                        continue
                kp = getattr(o, 'thruster_props', None)
                if kp is not None:
                    entry = {
                        'name': o.name,
                        'thrust_n': kp.thrust_n,
                        'specific_impulse_seconds': kp.specific_impulse_seconds,
                        'minimum_pulse_time_seconds': kp.minimum_pulse_time_seconds,
                        'volumetric_exhaust_id': kp.volumetric_exhaust_id,
                        'sound_event_on': kp.sound_event_on,
                        'control_map_translation': _safe_vector_to_list(kp.control_map_translation),
                        'control_map_rotation': _safe_vector_to_list(kp.control_map_rotation),
                        'exportable': kp.exportable,
                        'location': list(o.location) if o.location is not None else None,
                    }
                    meta_list.append(entry)

            # Determine meta filepath (next to GLB) and write XML
            import os
            base = os.path.splitext(self.filepath)[0]
            meta_path = base + '_meta.xml'
            try:
                xml_text = thrusters_list_to_xml_str(meta_list)
                with open(meta_path, 'w', encoding='utf-8') as f:
                    f.write(xml_text)
            except Exception as e:
                self.report({'WARNING'}, f"GLB exported but failed to write meta file: {e}")
                return {'FINISHED'}

            self.report({'INFO'}, f"Exported GLB and wrote {len(meta_list)} metadata entries to {meta_path}")
            return {'FINISHED'}

        finally:
            # Restore selection and active object
            try:
                bpy.ops.object.select_all(action='DESELECT')
            except Exception:
                pass
            for o in prev_selected:
                try:
                    o.select_set(True)
                except Exception:
                    pass
            try:
                if prev_active is not None:
                    context.view_layer.objects.active = prev_active
            except Exception:
                pass


class VIEW3D_MT_ksa_add(bpy.types.Menu):
    bl_label = "KSA"
    bl_idname = "VIEW3D_MT_ksa_add"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.add_thruster", text="Thruster", icon='EMPTY_SINGLE_ARROW')
        layout.operator("object.add_engine", text="Engine", icon='CONE')


def menu_func(self, context):
    # Add KSA menu directly in the Add menu (not under Mesh)
    self.layout.menu(VIEW3D_MT_ksa_add.bl_idname)


def export_menu_func(self, context):
    # Add to File > Export menu
    self.layout.operator("export_scene.ksa_metadata", text="KSA Part")


def _extract_material_maps(mat):
    """Extract diffuse, normal, and combined rough/metal/ao images from a material.
    Returns a dict with optional keys: 'diffuse', 'normal', 'roughmetaao'.
    Heuristics:
    - Diffuse: image node whose name contains diffuse|albedo|basecolor or linked to Principled Base Color.
    - Normal: image node whose name contains normal or feeding into a Normal Map node.
    - RoughMetaAo: first image whose name contains rough|metal|ao|orm|rma.
    Safe against missing node trees; always returns dict (possibly empty)."""
    result = {}
    try:
        if not getattr(mat, 'use_nodes', False):
            return result
        nt = getattr(mat, 'node_tree', None)
        if nt is None:
            return result
        nodes = list(getattr(nt, 'nodes', []) or [])
        links = list(getattr(nt, 'links', []) or [])
        principled = [n for n in nodes if getattr(n, 'type', '') == 'BSDF_PRINCIPLED']
        normal_maps = [n for n in nodes if getattr(n, 'type', '') == 'NORMAL_MAP']
        for node in nodes:
            if getattr(node, 'type', '') != 'TEX_IMAGE':
                continue
            img = getattr(node, 'image', None)
            if img is None:
                continue
            lower = (getattr(img, 'name', '') or '').lower()
            # Diffuse by name
            if any(key in lower for key in ['diffuse', 'albedo', 'basecolor', 'base_color']) and 'diffuse' not in result:
                result['diffuse'] = img
            # Diffuse by link into Principled Base Color
            if 'diffuse' not in result:
                try:
                    for pnode in principled:
                        for inp in getattr(pnode, 'inputs', []) or []:
                            if getattr(inp, 'name', '').lower() in ['base color', 'basecolor']:
                                for link in links:
                                    if link.to_socket == inp and link.from_node == node:
                                        result['diffuse'] = img
                                        break
                        if 'diffuse' in result:
                            break
                except Exception:
                    pass
            # Normal by name
            if 'normal' not in result and 'normal' in lower:
                result['normal'] = img
            # Normal via Normal Map node link
            if 'normal' not in result:
                try:
                    for nmap in normal_maps:
                        for inp in getattr(nmap, 'inputs', []) or []:
                            if getattr(inp, 'name', '').lower() in ['color', 'image']:
                                for link in links:
                                    if link.to_socket == inp and link.from_node == node:
                                        result['normal'] = img
                                        break
                        if 'normal' in result:
                            break
                except Exception:
                    pass
            # Rough/Metal/AO packed
            if 'roughmetaao' not in result and any(key in lower for key in ['rough', 'metal', 'ao', 'orm', 'rma']):
                result['roughmetaao'] = img
        return result
    except Exception:
        return result


def _indent_xml(elem, level=0):
    """In-place pretty formatter for an ElementTree element.
    Adds indentation and newlines so the XML is human-readable.
    """
    indent = "\n" + ("  " * level)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        for child in elem:
            _indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent + "  "
        # Trim last child's tail to single indent
        if elem[-1].tail:
            elem[-1].tail = indent
    else:
        if not elem.text or not elem.text.strip():
            elem.text = ''


classes = (
    ThrusterProperties,
    EngineProperties,
    OBJECT_OT_add_thruster,
    OBJECT_OT_add_engine,
    OBJECT_PT_thruster_panel,
    OBJECT_PT_engine_panel,
    OBJECT_OT_export_ksa_metadata,
    OBJECT_OT_export_glb_with_meta,
    VIEW3D_MT_ksa_add,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass
    try:
        bpy.types.Object.thruster_props = bpy.props.PointerProperty(type=ThrusterProperties)
        bpy.types.Object.engine_props = bpy.props.PointerProperty(type=EngineProperties)
    except Exception:
        pass
    try:
        # Register KSA menu in the main Add menu (VIEW3D_MT_add), not in Mesh submenu
        bpy.types.VIEW3D_MT_add.append(menu_func)
        # Register export in File > Export menu
        bpy.types.TOPBAR_MT_file_export.append(export_menu_func)
    except Exception:
        pass
    print("Kitten export addon registered")


def unregister():
    try:
        bpy.types.VIEW3D_MT_add.remove(menu_func)
        bpy.types.TOPBAR_MT_file_export.remove(export_menu_func)
    except Exception:
        pass
    try:
        del bpy.types.Object.thruster_props
        del bpy.types.Object.engine_props
    except Exception:
        pass
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    print("Kitten export addon unregistered")

