"""
    KittenExport - Menu module
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


class VIEW3D_MT_ksa_add(bpy.types.Menu):
    """Menu for adding KSA objects."""
    bl_label = "KSA"
    bl_idname = "VIEW3D_MT_ksa_add"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.add_thruster", text="Thruster", icon='EMPTY_SINGLE_ARROW')
        layout.operator("object.add_engine", text="Engine", icon='CONE')


def menu_func_add(self, context):
    """Add a 'KSA menu' to the main Add menu."""
    self.layout.menu(VIEW3D_MT_ksa_add.bl_idname)


def menu_func_export(self, context):
    """Add KSA export to File > Export menu."""
    self.layout.operator("export_scene.ksa_metadata", text="KSA Part")
