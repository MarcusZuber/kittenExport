"""
    KittenExport - Export module
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
import os
import shutil
import xml.etree.ElementTree as ET
from .utils import (
    _safe_vector_to_list, sanitize_filename, _extract_material_maps,
    _indent_xml, parse_meta_string
)
from .thruster import _thruster_dict_to_xml_element
from .engine import _engine_dict_to_xml_element


class OBJECT_OT_export_ksa_metadata(bpy.types.Operator):
    """Export thrusters, engines, meshes, materials into part.xml with Meshes/ and Textures/ subfolders."""
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

        # Determine the base directory, throws an exception if invalid
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
            ET.SubElement(root, 'MeshFile', Id=obj.name + 'MeshFile', Path=f"Meshes/{mesh_file_name}",
                          Category='Vessel')

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

        # Add thruster elements directly under Part
        for thruster_data in thrusters:
            _thruster_dict_to_xml_element(part_elem, thruster_data, self.coordinate_decimal_places)

        # Add engine elements directly under Part
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

        self.report({'INFO'},
                    f"Exported {exported_mesh_count} meshes, {len(material_infos)} materials, {len(thrusters)} thrusters, {len(engines)} engines. XML: {xml_out_path}")
        return {'FINISHED'}


class OBJECT_OT_export_glb_with_meta(bpy.types.Operator):
    """Export scene to GLB excluding thruster objects and write thruster metadata JSON."""
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
        from .thruster import thrusters_list_to_xml_str

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

            # Determine the meta filepath (next to GLB) and write XML
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
