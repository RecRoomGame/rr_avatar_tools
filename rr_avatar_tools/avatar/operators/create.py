import uuid

import bpy

from bpy.props import (
    BoolProperty,
    EnumProperty,
    StringProperty,
)

from rr_avatar_tools.avatar.operators.base import (
    RecRoomAvatarOperator,
    RecRoomAvatarMeshOperator,
)

from rr_avatar_tools.utils import put_file_in_known_good_state
from rr_avatar_tools import handlers

class RR_OT_CreateAvatarItem(RecRoomAvatarMeshOperator):
    """Set up selected meshes as a new item. Select all LODs for a single item before running this command"""

    bl_idname = "rr.create_avatar_item"
    bl_label = "Create Avatar Item"
    bl_options = {"REGISTER", "UNDO"}
    rr_required_mode = "OBJECT"

    item_name: StringProperty(name="Item Name", description="")

    item_type: bpy.props.EnumProperty(
        name="Item Type",
        items=[
            ("BELT", "Belt", ""),
            ("EAR", "Ear", ""),
            ("EYE", "Eye", ""),
            ("HAIR", "Hair", ""),
            ("HAT", "Hat", ""),
            ("MOUTH", "Mouth", ""),
            ("NECK", "Neck", ""),
            ("WRIST", "Wrist", ""),
            ("SHIRT", "Shirt", ""),
            ("SHOULDER", "Shoulder", ""),
            ("LEG", "Leg", ""),
            ("SHOE", "Shoe", ""),
        ],
        default="SHIRT",
    )

    body_type: EnumProperty(
        name="Body Type",
        description="Select which body type item is for.",
        items=[
            ("FULL_BODY", "Full Body", ""),
            ("MODERN_BEAN_BODY", "Modern Bean Body", ""),
        ],
        default="FULL_BODY",
    )

    transfer_weights: BoolProperty(
        name="Transfer Weights",
        description="Copy weights based on item type",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def setup(self):
        first = self.selected_meshes()[0]
        self.item_name = first.name

        if first.name.startswith("MB_"):
            self.body_type = "MODERN_BEAN_BODY"
        else:
            self.body_type = "FULL_BODY"

        try:
            parts = first.name.split("_")
            last = parts[-1]
            if last.upper().startswith("LOD"):
                last = parts[-2]
            self.item_type = last.upper()
        except:
            self.item_type = "SHIRT"

        self.ensure_name()

        # Don't default to transferring weights if meshes already have weights
        names = [
            vertex_group.name
            for mesh in self.selected_meshes()
            for vertex_group in mesh.vertex_groups
        ]
        self.transfer_weights = not any(map(lambda x: x.startswith("Jnt."), names))

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)

        # Initial values
        self.setup()

        self._execute(context)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        return {"FINISHED"}

    def execute(self, context):
        return self._execute(context)

    def _execute(self, context):
        if self.item_name == "":
            self.setup()

        self.ensure_name()

        if self.body_type == "FULL_BODY":
            bpy.ops.rr.create_full_body_avatar_item(
                item_name=self.item_name, transfer_weights=self.transfer_weights
            )

        elif self.body_type == "MODERN_BEAN_BODY":
            bpy.ops.rr.create_modern_bean_body_avatar_item(
                item_name=self.item_name,
                item_type=self.item_type,
                transfer_weights=self.transfer_weights,
            )

        return {"FINISHED"}

    def ensure_name(self):
        parts = []

        for part in self.item_name.rstrip(".R").rstrip(".L").split("_"):
            if part.upper() in ("LOD0", "LOD1", "LOD2"):
                continue

            parts.append(part)

        if parts[0].upper() not in ("FB", "MB"):
            parts.insert(0, "FB")
        else:
            parts[0] = {
                "FULL_BODY": "FB",
                "MODERN_BEAN_BODY": "MB",
            }.get(self.body_type) or "FB"

        last = parts[-1].capitalize()

        if last in (
            "Belt",
            "Ear",
            "Eye",
            "Hair",
            "Hat",
            "Mouth",
            "Neck",
            "Wrist",
            "Shirt",
            "Shoulder",
            "Leg",
            "Shoe",
        ):
            parts[-1] = self.item_type.title()
        else:
            parts.append(self.item_type.title())

        self.item_name = "_".join(parts)

        for mesh in self.selected_meshes():
            prefix = {
                "FULL_BODY": "FB",
                "MODERN_BEAN_BODY": "MB",
            }.get(self.body_type) or "FB"

            if not mesh.name.startswith(prefix):
                i = 0
                if mesh.name[2] == "_":
                    i = 3

                mesh.name = f"{prefix}_{mesh.name[i:]}"

            # Ensure we have LOD part
            if not mesh.name.split("_")[-1].startswith("LOD"):
                mesh.name = f"{mesh.name}_LOD0"


class RR_OT_CreateFullBodyAvatarItem(RecRoomAvatarMeshOperator):
    """Setup file for avatar work"""

    bl_idname = "rr.create_full_body_avatar_item"
    bl_label = "Create Full Body Avatar Item"
    bl_options = {"REGISTER", "UNDO"}

    item_name: StringProperty(name="Item Name", description="")

    transfer_weights: BoolProperty(
        name="Transfer Weights",
        description="Copy weights based on item type",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return bool(bpy.data.collections.get("Full_Body"))

    def execute(self, context):
        # Ensure avatar item collection
        dest = bpy.data.collections.get(self.item_name)
        if not dest:
            dest = bpy.data.collections.new(self.item_name)
            bpy.data.collections["Full_Body"].children.link(dest)

        dest.color_tag = "COLOR_02"

        # Mark collection as an avatar item
        if not dest.get("rec_room_uuid"):
            dest["rec_room_uuid"] = str(uuid.uuid4())

        # Link in armature
        rig = bpy.data.objects.get("Avatar_Skeleton")
        if not rig:
            self.report({"ERROR"}, "Missing Avatar_Skeleton armature")
            return {"CANCELLED"}

        if dest not in rig.users_collection:
            dest.objects.link(rig)

        for mesh in self.selected_meshes():
            # Remove mesh from all collections
            for collection in mesh.users_collection:
                collection.objects.unlink(mesh)

            dest.objects.link(mesh)

            modifers = [m for m in mesh.modifiers if m.type == "ARMATURE"]
            if len(modifers) > 1:
                for m in modifers:
                    mesh.modifiers.remove(m)
                modifers = []

            if len(modifers) == 0:
                m = mesh.modifiers.new(name="Armature", type="ARMATURE")
                modifers = [m]

            modifer = modifers[0]
            modifer.object = rig
            modifer.show_on_cage = True
            modifer.show_in_editmode = True

            if self.transfer_weights:
                # Set body mesh to active selection
                body_mesh = bpy.data.objects.get("BodyMesh_LOD0")
                body_mesh.select_set(True)
                old_active = bpy.context.view_layer.objects.active
                bpy.context.view_layer.objects.active = body_mesh
                
                # Cache and make Culling Groups visible.
                mask_selection = [m.select for m in bpy.context.scene.mask_list]
                for i in range(len(bpy.context.scene.mask_list)):
                    bpy.context.scene.mask_list[i].select = True
                handlers.update_mask_modifiers(bpy.context.scene)


                # Transfer weights
                bpy.ops.rr.weights_transfer_weights_from_active_mesh()

                # Restore disabled Culling Groups 
                for i, select in enumerate(mask_selection):
                    bpy.context.scene.mask_list[i].select = select
                handlers.update_mask_modifiers(bpy.context.scene)

                # Clear body mesh active and selection
                bpy.context.view_layer.objects.active = old_active
                body_mesh.select_set(False)

        return {"FINISHED"}


class RR_OT_CreateModernBeanBodyAvatarItem(RecRoomAvatarMeshOperator):
    """Setup file for avatar work"""

    bl_idname = "rr.create_modern_bean_body_avatar_item"
    bl_label = "Create Modern Bean Body Avatar Item"
    bl_options = {"REGISTER", "UNDO"}

    item_name: StringProperty(name="Item Name", description="")

    item_type: bpy.props.EnumProperty(
        name="Item Type",
        items=[
            ("BELT", "Belt", ""),
            ("EAR", "Ear", ""),
            ("EYE", "Eye", ""),
            ("HAIR", "Hair", ""),
            ("HAT", "Hat", ""),
            ("MOUTH", "Mouth", ""),
            ("NECK", "Neck", ""),
            ("WRIST", "Wrist", ""),
            ("SHIRT", "Shirt", ""),
            ("SHOULDER", "Shoulder", ""),
            ("LEG", "Leg", ""),
            ("SHOE", "Shoe", ""),
        ],
        default="SHIRT",
    )

    transfer_weights: BoolProperty(
        name="Transfer Weights",
        description="Copy weights based on item type",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return bool(bpy.data.collections.get("Modern_Bean_Body"))

    def execute(self, context):
        # Ensure avatar item collection
        dest = bpy.data.collections.get(self.item_name)
        if not dest:
            dest = bpy.data.collections.new(self.item_name)
            bpy.data.collections["Modern_Bean_Body"].children.link(dest)

        dest.color_tag = "COLOR_05"

        # Mark collection as an avatar item
        if not dest.get("rec_room_uuid"):
            dest["rec_room_uuid"] = str(uuid.uuid4())

        # Link in armature
        rig = bpy.data.objects.get("Avatar_Skeleton")
        if not rig:
            self.report({"ERROR"}, "Missing Avatar_Skeleton armature")
            return {"CANCELLED"}

        if dest not in rig.users_collection:
            dest.objects.link(rig)

        # Cache selection
        active = bpy.context.view_layer.objects.active
        selected_meshes = self.selected_meshes()

        bpy.ops.object.select_all(action="DESELECT")

        for mesh in selected_meshes:
            mesh.select_set(True)
            bpy.context.view_layer.objects.active = mesh

            # Apply visual transformations
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

            # Remove mesh from all collections
            for collection in mesh.users_collection:
                collection.objects.unlink(mesh)

            dest.objects.link(mesh)

            # Remove all existing shape keys
            if mesh.data.shape_keys and len(mesh.data.shape_keys.key_blocks) > 0:
                mesh.active_shape_key_index = 0
                if bpy.ops.object.shape_key_remove.poll():
                    bpy.ops.object.shape_key_remove(all=True)

            modifers = [m for m in mesh.modifiers if m.type == "ARMATURE"]
            if len(modifers) > 1:
                for m in modifers:
                    mesh.modifiers.remove(m)
                modifers = []

            if len(modifers) == 0:
                m = mesh.modifiers.new(name="Armature", type="ARMATURE")
                modifers = [m]

            modifer = modifers[0]
            modifer.object = rig
            modifer.show_on_cage = True
            modifer.show_in_editmode = True
            modifer.vertex_group = ""

            # Apply weights
            weight_transferrable_item_types = (
                "BELT",
                "NECK",
                "SHIRT",
                "SHOULDER",
                "WRIST",
            )

            if (
                self.transfer_weights
                and self.item_type in weight_transferrable_item_types
            ):
                if self.item_type == "WRIST":
                    if bpy.ops.rr.weights_apply_modern_bean_hand_weights.poll():
                        bpy.ops.rr.weights_apply_modern_bean_hand_weights()

                else:
                    if bpy.ops.rr.weights_apply_modern_bean_torso_weights.poll():
                        bpy.ops.rr.weights_apply_modern_bean_torso_weights()

            bpy.context.view_layer.objects.active = None
            mesh.select_set(False)

        # Restore selection
        bpy.context.view_layer.objects.active = active
        for mesh in selected_meshes:
            mesh.select_set(True)

        return {"FINISHED"}


class RR_OT_CreateLeftSideAvatarItem(RecRoomAvatarMeshOperator):
    """Duplicate and mirror an item across the z-axis"""

    bl_idname = "rr.create_left_side_avatar_item"
    bl_label = "Create Left Side Item"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(cls.target_meshes())

    @classmethod
    def target_meshes(cls):
        def is_ear_or_wrist_item(object_):
            parts = object_.name.split("_")

            if "Wrist" in parts:
                return True

            return "Ear" in parts

        selection = [m for m in cls.selected_meshes() if is_ear_or_wrist_item(m)]

        return selection

    def execute(self, context):
        # Cache selection
        active = bpy.context.view_layer.objects.active
        selection = self.target_meshes()

        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = None

        duplicated_selection = []

        for selected in selection:
            name = selected.name.rstrip(".R")
            selected.name = f"{name}.R"

            selected.select_set(True)

            bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

            # Duplicate selection
            duplicate = selected.copy()
            duplicate.data = selected.data.copy()
            bpy.context.collection.objects.link(duplicate)
            selected.select_set(False)

            # Remove duplicate from all collections
            for collection in duplicate.users_collection[:]:
                collection.objects.unlink(duplicate)

            # Put duplicate into the same collections as selected mesh
            for collection in selected.users_collection:
                collection.objects.link(duplicate)

            selected = duplicate
            selected.name = f"{name}.L"
            selected.select_set(True)
            bpy.context.view_layer.objects.active = selected

            # Add modifier
            modifier: bpy.types.MirrorModifier = selected.modifiers.new(
                "Mirror", "MIRROR"
            )

            # Configure modifier
            modifier.use_axis[0] = True

            # Apply modifier
            bpy.ops.object.modifier_apply(modifier="Mirror")

            bpy.ops.object.mode_set(mode="EDIT")

            # Select all geo
            bpy.ops.mesh.select_all(action="SELECT")

            # Delete right-side geo
            bpy.ops.mesh.bisect(
                plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=True, flip=False
            )
            bpy.ops.object.mode_set(mode="OBJECT")

            bpy.context.view_layer.objects.active = None
            selected.select_set(False)

            duplicated_selection.append(selected)

        # Restore selection
        bpy.context.view_layer.objects.active = None
        bpy.ops.object.select_all(action="DESELECT")
        for selected in duplicated_selection:
            selected.select_set(True)

        return {"FINISHED"}


class RR_OT_CreateModerBeanFromFullBodyItem(RecRoomAvatarOperator):
    """Create Modern Bean Avatar Item from Full Body"""

    bl_idname = "rr.create_modern_bean_from_full_body"
    bl_label = "Create Modern Bean Avatar Item from Full Body"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        selected_collection = bpy.context.collection

        if not selected_collection:
            return False

        if selected_collection.name[:3] != "FB_":
            return False

        if selected_collection.name == "FB_Resources":
            return False

        return super().poll(context)

    def execute(self, context):
        return self._execute(context)

    @put_file_in_known_good_state
    def _execute(self, context):
        selected_collection = bpy.context.collection

        bpy.ops.object.select_all(action="DESELECT")

        duplicates = []

        mesh: bpy.types.Object
        for mesh in [o for o in selected_collection.objects if o.type == "MESH"]:
            mesh.select_set(True)
            bpy.context.view_layer.objects.active = mesh

            # Duplicate selection
            bpy.ops.object.duplicate_move()
            duplicate = bpy.context.view_layer.objects.active
            bpy.context.view_layer.objects.active = duplicate
            duplicate.select_set(True)
            duplicate.select_set(False)

            # Rename duplicate
            if duplicate.name.startswith("FB_"):
                duplicate.name = f"MB_{duplicate.name[3:]}"

            if duplicate.name[-4] == ".":
                duplicate.name = duplicate.name[:-4]

            duplicates.append(duplicate)

            duplicate.select_set(False)

        for duplicate in duplicates:
            duplicate.select_set(True)

        bpy.ops.rr.create_avatar_item(transfer_weights=False)

        for duplicate in duplicates:
            duplicate.select_set(False)

        return {"FINISHED"}


classes = (
    RR_OT_CreateAvatarItem,
    RR_OT_CreateFullBodyAvatarItem,
    RR_OT_CreateLeftSideAvatarItem,
    RR_OT_CreateModernBeanBodyAvatarItem,
    RR_OT_CreateModerBeanFromFullBodyItem,
)

panel = (
    RR_OT_CreateAvatarItem,
    RR_OT_CreateLeftSideAvatarItem,
    RR_OT_CreateModerBeanFromFullBodyItem,
)


def register():
    for class_ in classes:
        bpy.utils.register_class(class_)


def unregister():
    for class_ in classes:
        bpy.utils.unregister_class(class_)
