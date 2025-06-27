import bpy

from rr_avatar_tools.operators.base import RecRoomAvatarMeshOperator
from rr_avatar_tools.utils import put_file_in_known_good_state
from rr_avatar_tools.budgets import budgets
from rr_avatar_tools.bones import bones
from rr_avatar_tools.bounds import bounding_boxes


class Icons:
    WARNING = "ERROR"
    ERROR = "CANCEL"


class RecRoomDiagnosticOperator(RecRoomAvatarMeshOperator):
    rr_required_mode = "OBJECT"

    label = {"text": "", "icon": Icons.WARNING}

    target: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return cls.can_fix(context)

    @classmethod
    def can_fix(cls, context):
        return True

    @classmethod
    def diagnose(cls, mesh):
        """Returns True if diagnostic applies to given mesh"""
        return True


class RR_OT_DiagnosticsFixUnappliedTransforms(RecRoomDiagnosticOperator):
    """"""

    bl_idname = "rr.diagnostics_fix_unapplied_transforms"
    bl_label = "Unapplied Transforms"
    bl_options = {"REGISTER", "UNDO"}

    label = {"text": "Unapplied Transforms", "icon": Icons.WARNING}

    @classmethod
    def diagnose(cls, mesh):
        sx, sy, sz = mesh.scale
        unapplied_scale = not (sx == sy == sz == 1.0)

        rx, ry, rz = mesh.rotation_euler[:]
        unapplied_rotation = not (rx == ry == rz == 0.0)

        lx, ly, lz = mesh.location
        unapplied_location = not (lx == ly == lz == 0.0)

        return unapplied_scale or unapplied_rotation or unapplied_location

    @classmethod
    def can_fix(cls, context):
        return True

    def execute(self, context):
        return self.execute_(context)

    @put_file_in_known_good_state
    def execute_(self, context):
        # Cache selection
        active = bpy.context.active_object
        selected_meshes = [
            o for o in bpy.data.objects if o.select_get() and o.type == "MESH"
        ]

        # Clear selection
        bpy.ops.object.select_all(action="DESELECT")

        mesh = bpy.data.objects.get(self.target)
        if mesh:
            mesh.select_set(True)
            bpy.context.view_layer.objects.active = mesh
            state = mesh.hide_get()
            mesh.hide_set(False)

            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

            mesh.hide_set(state)

        # Restore selection
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = active
        for selected in selected_meshes:
            selected.select_set(True)

        return {"FINISHED"}


class RR_OT_DiagnosticsFixMissingArmatureModifier(RecRoomDiagnosticOperator):
    """"""

    bl_idname = "rr.diagnostics_fix_missing_armature_modifier"
    bl_label = "Missing Armature Modifier"
    bl_options = {"REGISTER", "UNDO"}

    label = {"text": bl_label, "icon": Icons.ERROR}

    @classmethod
    def get_body_type(cls, mesh):
        def check_prefix(obj, prefix):
            return obj.name.startswith(prefix)

        if check_prefix(mesh, "MB_"):
            return "MODERNBEAN"

        if check_prefix(mesh, "FB_"):
            return "FULLBODY"

        collections = mesh.users_collection

        if any(map(lambda x: check_prefix(x, "MB_"), collections)):
            return "MODERNBEAN"

        if any(map(lambda x: check_prefix(x, "FB_"), collections)):
            return "FULLBODY"

        return "UNKNOWN"

    @classmethod
    def get_rig(cls, mesh):
        body_type = cls.get_body_type(mesh)

        if body_type in ("MODERNBEAN", "FULLBODY"):
            return bpy.data.objects.get("Avatar_Skeleton")

        return None

    @classmethod
    def diagnose(cls, mesh):
        modifiers = [m for m in mesh.modifiers if m.type == "ARMATURE"]

        if len(modifiers) != 1:
            return True

        modifier: bpy.types.ArmatureModifier = modifiers[0]

        # Get the correct rig for this item
        rig = cls.get_rig(mesh)
        if not rig:
            return True

        uses_vertex_groups = (
            bpy.data.objects.get("Torso.Rig"),
            bpy.data.objects.get("Head.Rig"),
        )

        # Ensure Torso and Head items have vertex group set
        if rig in uses_vertex_groups and not modifier.vertex_group:
            return True

        # Verify the rig is set as the modifier's object
        return modifier.object != rig

    @classmethod
    def can_fix(cls, context):
        def can_fix_(o):
            return cls.get_body_type(o) in ("FULLBODY", "MODERNBEAN")

        selected_meshes = [
            o for o in bpy.data.objects if o.select_get() and o.type == "MESH"
        ]

        return any(map(lambda x: can_fix_(x), selected_meshes))

    def get_or_create_armature_modifier(self, mesh) -> bpy.types.ArmatureModifier:
        modifiers = [m for m in mesh.modifiers if m.type == "ARMATURE"]

        # If we have too many, just remove them all
        if len(modifiers) > 1:
            for modifier in modifiers:
                mesh.modifiers.remove(modifier)

            modifiers = [m for m in mesh.modifiers if m.type == "ARMATURE"]

        if len(modifiers) == 0:
            m = mesh.modifiers.new(name="Armature", type="ARMATURE")
            modifiers = [m]

        return modifiers[0]

    def fix_full_body(self, mesh):
        modifier = self.get_or_create_armature_modifier(mesh)
        modifier.object = self.get_rig(mesh)

    def execute(self, context):
        return self.execute_(context)

    @put_file_in_known_good_state
    def execute_(self, context):
        # Cache selection
        active = bpy.context.active_object
        selected_meshes = [
            o for o in bpy.data.objects if o.select_get() and o.type == "MESH"
        ]

        # Clear selection
        bpy.ops.object.select_all(action="DESELECT")

        mesh = bpy.data.objects.get(self.target)

        state = mesh.hide_get()
        mesh.hide_set(False)

        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh

        # Perform fix for corresponding body type
        body_type = self.get_body_type(mesh)
        if body_type in ("FULLBODY", "MODERNBEAN"):
            self.fix_full_body(mesh)

        mesh.hide_set(state)

        # Restore selection
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = active
        for selected in selected_meshes:
            selected.select_set(True)

        return {"FINISHED"}


class RR_OT_DiagnosticsFixCullingMaskVertexGroups(RecRoomDiagnosticOperator):
    """Remove culling mask vertex group"""

    bl_idname = "rr.diagnostics_fix_culling_mask_vertex_groups"
    bl_label = "Culling Mask Vertex Groups"
    bl_options = {"REGISTER", "UNDO"}

    label = {"text": "Culling Mask Vertex Groups", "icon": Icons.WARNING}

    @classmethod
    def diagnose(cls, mesh):
        mask_groups = [g for g in mesh.vertex_groups if g.name.startswith("Msk.")]

        return mask_groups

    @classmethod
    def can_fix(cls, context):
        return True

    def execute(self, context):
        return self.execute_(context)

    @put_file_in_known_good_state
    def execute_(self, context):
        # Cache selection
        active = bpy.context.active_object
        selected_meshes = self.selected_meshes()

        # Clear selection
        bpy.ops.object.select_all(action="DESELECT")

        mesh = bpy.data.objects.get(self.target)
        if mesh:
            mesh.select_set(True)
            bpy.context.view_layer.objects.active = mesh
            state = mesh.hide_get()
            mesh.hide_set(False)

            mask_groups = [g for g in mesh.vertex_groups if g.name.startswith("Msk.")]
            for mask in mask_groups:
                mesh.vertex_groups.remove(mask)

            mesh.hide_set(state)

        # Restore selection
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = active
        for selected in selected_meshes:
            selected.select_set(True)

        return {"FINISHED"}


class RR_OT_DiagnosticsLimitBonesPerVertex(RecRoomDiagnosticOperator):
    """Fix bone groups"""

    bl_idname = "rr.diagnostics_limit_bones_per_vertex"
    bl_label = "Limit Bones per Vertex"
    bl_options = {"REGISTER", "UNDO"}

    label = {"text": "Limit Bones per Vertex", "icon": Icons.WARNING}

    @classmethod
    def diagnose(cls, mesh):
        bone_groups = set(
            g.index for g in mesh.vertex_groups if g.name.startswith("Jnt.")
        )

        return any(
            map(
                lambda x: len(x) > 4,
                [
                    {g.group for g in v.groups if g.group in bone_groups}
                    for v in mesh.data.vertices
                ],
            )
        )

    @classmethod
    def can_fix(cls, context):
        return True

    def execute(self, context):
        return self.execute_(context)

    @put_file_in_known_good_state
    def execute_(self, context):
        # Cache selection
        active = bpy.context.active_object
        selected_meshes = self.selected_meshes()

        # Clear selection
        bpy.ops.object.select_all(action="DESELECT")

        mesh: bpy.types.Object = bpy.data.objects.get(self.target)
        if mesh:
            bpy.context.view_layer.objects.active = mesh
            mesh.select_set(True)
            state = mesh.hide_get()
            mesh.hide_set(False)

            # Enter weight paint mode
            bpy.ops.paint.weight_paint_toggle()

            # Cache state of use vertex paint
            state = bpy.context.object.data.use_paint_mask_vertex
            bpy.context.object.data.use_paint_mask_vertex = True

            # Limit influences
            bpy.ops.paint.vert_select_all(action="SELECT")
            bpy.ops.object.vertex_group_limit_total(limit=4)

            # Restore use vertex paint state
            bpy.context.object.data.use_paint_mask_vertex = state

            # Exit weight paint mode
            bpy.ops.paint.weight_paint_toggle()

            mesh.hide_set(state)
            mesh.select_set(False)

        # Restore selection
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = active
        for selected in selected_meshes:
            selected.select_set(True)

        return {"FINISHED"}


class RR_OT_DiagnosticsFixNgons(RecRoomDiagnosticOperator):
    """"""

    bl_idname = "rr.diagnostics_fix_ngons"
    bl_label = "Fix Ngons"
    bl_options = {"REGISTER", "UNDO"}

    label = {"text": "Ngon faces", "icon": Icons.WARNING}

    @classmethod
    def diagnose(cls, mesh):
        return any(p for p in mesh.data.polygons if len(p.vertices) > 4)

    @classmethod
    def can_fix(cls, context):
        return True

    def execute(self, context):
        return self.execute_(context)

    @put_file_in_known_good_state
    def execute_(self, context):
        # Cache selection
        active = bpy.context.active_object
        selected_meshes = [
            o for o in bpy.data.objects if o.select_get() and o.type == "MESH"
        ]

        # Clear selection
        bpy.ops.object.select_all(action="DESELECT")

        mesh = bpy.data.objects.get(self.target)
        if mesh:
            mesh.select_set(True)
            bpy.context.view_layer.objects.active = mesh
            state = mesh.hide_get()
            mesh.hide_set(False)

            bpy.ops.object.mode_set(mode="EDIT")
            # Reveal any potentially hiding faces
            bpy.ops.mesh.reveal()
            # Select ngons and fix
            bpy.ops.mesh.select_all(action="DESELECT")
            bpy.ops.mesh.select_face_by_sides(type="GREATER")
            bpy.ops.mesh.quads_convert_to_tris()
            bpy.ops.mesh.tris_convert_to_quads(uvs=True, sharp=True)

            bpy.ops.object.mode_set(mode="OBJECT")

            mesh.hide_set(state)

        # Restore selection
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = active
        for selected in selected_meshes:
            selected.select_set(True)

        return {"FINISHED"}


class RR_OT_DiagnosticsCheckTriangleCount(RecRoomDiagnosticOperator):
    """"""

    bl_idname = "rr.diagnostics_check_triangle_count"
    bl_label = "Check Triangle Count"
    bl_options = {"REGISTER", "UNDO"}

    label = {"text": "Over Triangle Count", "icon": Icons.WARNING}

    @classmethod
    def diagnose(cls, mesh):
        parts = mesh.name.upper().split("_")
        item_type = parts[0].upper()
        lod_level = parts[-1].upper()
        outfit_type = parts[-2].upper()

        body_budget = budgets.get(item_type)

        if not body_budget:
            return False

        outfit_budget = body_budget.get(outfit_type)

        if not outfit_budget:
            return False

        triangle_budget = outfit_budget.get(lod_level)

        if not triangle_budget:
            return False

        triangle_count = sum([len(p.vertices) - 2 for p in mesh.data.polygons])

        cls.label["text"] = "Exceeded Triangle Count"

        return triangle_count > triangle_budget

    @classmethod
    def can_fix(cls, context):
        return False

    def execute(self, context):
        return {"FINISHED"}


class RR_OT_DiagnosticsCheckItemType(RecRoomDiagnosticOperator):
    """"""

    bl_idname = "rr.diagnostics_check_item_type"
    bl_label = "Check Item Type"
    bl_options = {"REGISTER", "UNDO"}

    label = {"text": "Incorrect Item Type for Body Type", "icon": Icons.WARNING}

    @classmethod
    def diagnose(cls, mesh):
        name = mesh.name
        parts = name.split("_")
        prefix = parts[0]
        item_type = parts[-2].upper()

        cls.label["text"] = "Incorrect Item Type for Body Type"

        body_types = {"MB": "Modern Bean", "FB": "Full Body"}

        if prefix == "MB":
            if item_type in ("LEG", "SHOE"):
                cls.label["text"] = (
                    f"Item type {item_type.capitalize()} not valid for {body_types[prefix]}"
                )
                return True

        return False

    @classmethod
    def can_fix(cls, context):
        return False

    def execute(self, context):
        return {"FINISHED"}


class RR_OT_DiagnosticsCheckBoneWeighting(RecRoomDiagnosticOperator):
    """"""

    bl_idname = "rr.diagnostics_check_bone_weighting"
    bl_label = "Check Bone Weighting"
    bl_options = {"REGISTER", "UNDO"}

    label = {"text": "Invalid Bone Found", "icon": Icons.WARNING}

    @classmethod
    def diagnose(cls, mesh):
        parts = mesh.name.upper().split("_")
        item_type = parts[0].upper()
        outfit_type = parts[-2].upper()

        body_bones = bones.get(item_type)

        if not body_bones:
            return False

        expected_bone_names = body_bones.get(outfit_type)

        if not expected_bone_names:
            return False

        # Find vertex groups that have at least one vertex with non-zero weight
        indices = {
            g.group for v in mesh.data.vertices for g in v.groups if g.weight > 0
        }
        actual_bone_names = {
            mesh.vertex_groups[i].name
            for i in indices
            if mesh.vertex_groups[i].name.startswith("Jnt.")
        }

        unexpected_bones = list(actual_bone_names.difference(expected_bone_names))

        if unexpected_bones:
            cls.label["text"] = f'Invalid Bone(s) Found: {", ".join(unexpected_bones)}'

        return not actual_bone_names.issubset(expected_bone_names)

    @classmethod
    def can_fix(cls, context):
        return False

    def execute(self, context):
        return {"FINISHED"}


class RR_OT_DiagnosticsCheckBounds(RecRoomDiagnosticOperator):
    """"""

    bl_idname = "rr.diagnostics_check_bounds"
    bl_label = "Check Bounds"
    bl_options = {"REGISTER", "UNDO"}

    label = {"text": "Outside bounds", "icon": Icons.WARNING}

    def in_bounds(self, bound, location):
        m = bound.matrix_world.inverted()

        v = m @ location

        if abs(v.x) > 1:
            return False

        if abs(v.y) > 1:
            return False

        if abs(v.z) > 1:
            return False

        return True

    @classmethod
    def diagnose(cls, mesh):
        parts = mesh.name.upper().split("_")
        item_type = parts[0].upper()
        outfit_type = parts[-2].upper()

        target = outfit_type

        if target == "SHIRT":
            if item_type == "FB":
                target = "FB_SHIRT"
            elif item_type == "MB":
                target = "MB_SHIRT"

        if target == "WRIST":
            if mesh.name.endswith(".L"):
                target = "WRIST.L"
            elif mesh.name.endswith(".R"):
                target = "WRIST.R"

        bounds = bounding_boxes.get(target, None)

        if not bounds:
            return False

        local_to_world = mesh.matrix_world
        world_to_bounds = bounds.inverted()
        local_to_bounds = world_to_bounds @ local_to_world

        for vertex in mesh.data.vertices:
            # Convert vertex local > world > bounds space
            v = local_to_bounds @ vertex.co

            if any(map(lambda component: abs(component) > 1, v)):
                return True

        return False

    @classmethod
    def can_fix(cls, context):
        return False

    def execute(self, context):
        return {"FINISHED"}


classes = (
    RR_OT_DiagnosticsFixUnappliedTransforms,
    RR_OT_DiagnosticsFixMissingArmatureModifier,
    RR_OT_DiagnosticsFixCullingMaskVertexGroups,
    RR_OT_DiagnosticsLimitBonesPerVertex,
    RR_OT_DiagnosticsFixNgons,
    RR_OT_DiagnosticsCheckTriangleCount,
    RR_OT_DiagnosticsCheckItemType,
    RR_OT_DiagnosticsCheckBoneWeighting,
    RR_OT_DiagnosticsCheckBounds,
)

panel = (
    RR_OT_DiagnosticsFixUnappliedTransforms,
    RR_OT_DiagnosticsFixMissingArmatureModifier,
    RR_OT_DiagnosticsFixCullingMaskVertexGroups,
    RR_OT_DiagnosticsLimitBonesPerVertex,
    RR_OT_DiagnosticsFixNgons,
    RR_OT_DiagnosticsCheckTriangleCount,
    RR_OT_DiagnosticsCheckItemType,
    RR_OT_DiagnosticsCheckBoneWeighting,
    RR_OT_DiagnosticsCheckBounds,
)


def register():
    for class_ in classes:
        bpy.utils.register_class(class_)


def unregister():
    for class_ in classes:
        bpy.utils.unregister_class(class_)
