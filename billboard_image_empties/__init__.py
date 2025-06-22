# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import bpy
import mathutils
from typing import cast, Any


bl_info = {
    "name": "Billboard Image Empties",
    "author": "Martinho Tavares",
    "description": "Option to view an image empty in billboard mode in the viewport.",
    "blender": (4, 4, 1),
    "version": (0, 0, 1),
    "location": "Properties &gt; Data &gt; Empty",
    "warning": "Work in progress",
    "tracker_url": "https://github.com/martinhoT/billboard-image-empties/issues",
    "category": "Object",
}


draw_handler: Any = None
prev_target: mathutils.Vector | None = None


def draw_callback_3d():
    global prev_target
    
    space = bpy.context.space_data
    if not space or not space.type == "VIEW_3D":
        return
    
    viewport = cast(bpy.types.SpaceView3D, space)
    if not viewport.region_3d:
        return
    
    target = viewport.region_3d.view_matrix.inverted().translation
    if target == prev_target:
        return
    prev_target = target
    
    up = mathutils.Vector((0.0, 0.0, 1.0))
    forward_2d = mathutils.Vector((0.0, -1.0))
    
    scene = bpy.context.scene
    if not scene:
        return

    # TODO: improve it by iterating over objects in view?
    for o in scene.objects:
        if not o.get("viewport_billboard", False):
            continue
        
        # TODO: simplify this.
        new_forward_vector = target - o.location
        new_forward_vector_flat = mathutils.Vector((new_forward_vector.x, new_forward_vector.y))
        location, _, scale = o.matrix_local.decompose()
        pitch_angle = new_forward_vector.angle(up, 0.0)
        yaw_angle = new_forward_vector_flat.angle_signed(forward_2d, 0.0)
        pitch = mathutils.Matrix.Rotation(pitch_angle, 3, "X")
        yaw = mathutils.Matrix.Rotation(yaw_angle, 3, "Z")
        o.matrix_local = mathutils.Matrix.LocRotScale(location, yaw @ pitch, scale)


def billboard_checkbox_update(self: bpy.types.bpy_struct, context: bpy.types.Context):
    if not isinstance(self, bpy.types.Object):
        return
    
    if self["viewport_billboard"]:
        self["viewport_billboard_original_rotation"] = self.matrix_local.decompose()[1]
    else:
        location, _, scale = self.matrix_local.decompose()
        original_rotation = mathutils.Quaternion(self["viewport_billboard_original_rotation"])
        self.matrix_local = mathutils.Matrix.LocRotScale(location, original_rotation, scale)


def billboard_checkbox_get(self: bpy.types.bpy_struct) -> bool:
    return self["viewport_billboard"]


def billboard_checkbox_set(self: bpy.types.bpy_struct, value: bool):
    self["viewport_billboard"] = value


def billboard_checkbox(self: bpy.types.Panel, context):
    layout = self.layout
    if not layout:
        return
    
    obj = context.object
    row = layout.row()
    row.prop(obj, "viewport_billboard")


def register():
    global draw_handler

    # TODO: not recommended to use drawing callbacks, investigate better alternative.
    #       Why: https://docs.blender.org/api/current/info_gotchas_internal_data_and_python_objects.html#no-updates-after-changing-ui-context
    #       Explore: https://docs.blender.org/api/current/bpy.app.handlers.html#module-bpy.app.handlers
    draw_handler = bpy.types.SpaceView3D.draw_handler_add(draw_callback_3d, tuple(), 'WINDOW', 'POST_VIEW')
    bpy.types.Object.viewport_billboard = bpy.props.BoolProperty( # type: ignore (new attribute)
        name="Billboard In Viewport",
        description="Have the image always face the viewport camera. Changes the object's rotation.",
        update=billboard_checkbox_update,
        get=billboard_checkbox_get,
        set=billboard_checkbox_set,
    )
    bpy.types.DATA_PT_empty.append(billboard_checkbox)


def unregister():
    # TODO: recommended to pop by index rather than remove.
    bpy.types.DATA_PT_empty.remove(billboard_checkbox)
    # The added property `viewport_billboard` is not removed because
    # I do not know how to remove it... or if it is even necessary.
    bpy.types.SpaceView3D.draw_handler_remove(draw_handler, 'WINDOW')
