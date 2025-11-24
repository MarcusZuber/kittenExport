"""
    KittenExport - Utilities module
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

import json
import xml.etree.ElementTree as ET
import re


def _round_coordinate(value, decimal_places):
    """Round a coordinate value based on the number of decimal places.

    Args:
        value: The coordinate value to round
        decimal_places: Number of decimal places (e.g., 3 for 0.001 precision)

    Returns:
        Rounded value as float
    """
    return round(float(value), decimal_places)


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
    if not name:
        return "unnamed"
    # Replace path separators and any char not in the whitelist with '_'
    cleaned = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    # Avoid leading dots (hidden files on some OS)
    cleaned = cleaned.lstrip('.')
    if not cleaned:
        cleaned = 'unnamed'
    # Trim very long names to a reasonable length
    if len(cleaned) > 128:
        cleaned = cleaned[:128]
    return cleaned


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
    """Convert an XML element to a dictionary recursively."""
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
    """Parse a metadata string (XML or JSON format)."""
    if not s:
        return None
    s = s.strip()
    # try XML first
    if s.startswith('<'):
        try:
            root = ET.fromstring(s)
            if root.tag == 'thruster':
                return _element_to_dict(root)
            # if it's a list wrapper, return a list
            if root.tag == 'thrusters':
                return [_element_to_dict(child) for child in root]
        except Exception:
            pass
    # fallback: try JSON
    try:
        return json.loads(s)
    except Exception:
        return None


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
            if any(key in lower for key in
                   ['diffuse', 'albedo', 'basecolor', 'base_color']) and 'diffuse' not in result:
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
        # Trim the last child's tail to a single indent
        if elem[-1].tail:
            elem[-1].tail = indent
    else:
        if not elem.text or not elem.text.strip():
            elem.text = ''


def prop_with_unit(layout, props, prop_name, unit, factor_edit=0.92): # layout for units after the numbers

    prop_rna = props.bl_rna.properties[prop_name]
    label = prop_rna.name
    
    split = layout.split(factor=factor_edit, align=True)
    col_left = split.column(align=True)
    col_right = split.column(align=True)

    col_left.prop(props, prop_name, text=label)
    col_right.label(text=unit)
