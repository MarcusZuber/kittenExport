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

# Import modules with all classes and functions
from . import utils
from .thruster import (
    ThrusterProperties,
    OBJECT_OT_add_thruster,
    OBJECT_PT_thruster_panel
)
from .engine import (
    EngineProperties,
    OBJECT_OT_add_engine,
    OBJECT_PT_engine_panel,
)
from .export import (
    OBJECT_OT_export_ksa_metadata,
    OBJECT_OT_export_glb_with_meta,
)
from .menu import (
    VIEW3D_MT_ksa_add,
    menu_func_add,
    menu_func_export,
)

# Addon metadata
bl_info = {
    "name": "Kitten export",
    "blender": (4, 50, 0),
    "category": ["Add Mesh", "Import-Export"],
}

# List of all classes to register
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
    """Register all addon classes and properties."""
    # Register all classes
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass

    # Register object properties
    try:
        bpy.types.Object.thruster_props = bpy.props.PointerProperty(type=ThrusterProperties)
        bpy.types.Object.engine_props = bpy.props.PointerProperty(type=EngineProperties)
    except Exception:
        pass

    # Register menu functions
    try:
        # Register the KSA menu in the main Add menu
        bpy.types.VIEW3D_MT_add.append(menu_func_add)
        # Register export in File > Export menu
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    except Exception:
        pass

    print("Kitten export addon registered")


def unregister():
    """Unregister all addon classes and properties."""
    # Remove menu functions
    try:
        bpy.types.VIEW3D_MT_add.remove(menu_func_add)
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    except Exception:
        pass

    # Remove object properties
    try:
        del bpy.types.Object.thruster_props
        del bpy.types.Object.engine_props
    except Exception:
        pass

    # Unregister all classes in reverse order
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

    print("Kitten export addon unregistered")
