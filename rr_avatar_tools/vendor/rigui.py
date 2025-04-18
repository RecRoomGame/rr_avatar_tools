# Code generated by Rig UI

import bpy
from collections import defaultdict


def find_armature_by_rig_ui_id(rig_ui_id):
    for obj in bpy.data.objects:
        if (
            obj.type == "ARMATURE"
            and "rig_ui_id" in obj.data
            and obj.data["rig_ui_id"] == rig_ui_id
        ):
            return obj
    return None


class RIG_UI_OT_armature_configure(bpy.types.Operator):
    bl_idname = "rig_ui.armature_configure"
    bl_label = ""
    bl_description = """Options for the current armature
- Bone Collection button types.
- Key modifiers"""

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        obj = bpy.data.object["Avatar_Skeleton"]
        if not obj or obj.type != "ARMATURE":
            self.layout.label(
                text="Select the armature you want to configure.", icon="INFO"
            )
            return
        armature = obj.data
        if armature:
            draw_bc_armature_config(context, self.layout, armature)
        else:
            self.layout.label(
                text="Reopen the bone collection to continue editing.", icon="INFO"
            )


def draw_bc_armature_config(context, layout, armature_data):
    props = armature_data.rig_ui_props
    box_title = layout.box()
    box_title.label(text=f"Configure {context.active_object.name}")
    operator_exists = "RIG_UI_OT_bone_collection_action" in dir(bpy.types)

    if operator_exists:
        btn_col = layout.column()
        btn_col.label(text="Bone Collection Buttons")
        btn_col.separator()
        btn_col.prop(props, "bc_button_types", text="Button Type")

    layout.separator()
    ui_col = layout.column()
    ui_col.label(text="UI Settings")
    ui_col.prop(
        props,
        "ui_button_horizontal_separation",
        text="Horizontal Separation",
        slider=True,
    )
    ui_col.prop(
        props, "ui_button_vertical_separation", text="Vertical Separation", slider=True
    )
    ui_col.prop(
        props,
        "ui_groups_vertical_separation",
        text="Groups Vertical Separation",
        slider=True,
    )


class RIG_UI_PT_Universal(bpy.types.Panel):
    """Panel for Rig UI"""

    bl_label = "Rig"
    bl_idname = "RIG_UI_PT_Universal"
    bl_parent_id = "SCENE_PT_RRAvatarToolsToolsPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        armature = bpy.data.objects["Avatar_Skeleton"]

        rig_ui_id = (
            armature.data.get("rig_ui_id", None) if armature and armature.data else None
        )

        if (
            not armature
            or not armature.data
            or not rig_ui_id
            or armature.data.get("rig_ui_id", "") != rig_ui_id
        ):
            layout.label(text="Armature not found", icon="ERROR")
            return

        props = armature.data.rig_ui_props

        grp_v_separation = props.ui_groups_vertical_separation * 3
        btn_h_separation = props.ui_button_horizontal_separation * 3
        btn_v_separation = props.ui_button_vertical_separation * 1.5

        operator_exists = "RIG_UI_OT_bone_collection_action" in dir(bpy.types)

        obj = armature
        if not obj or obj.type != "ARMATURE":
            # Armature got deleted or is invalid, bail out
            layout.label(text="No valid armature selected", icon="INFO")
            return

        is_pose_mode = obj.mode == "POSE"
        active_pose_bone = context.active_pose_bone
        selected_pose_bones = context.selected_pose_bones
        is_v41_plus = bpy.app.version >= (4, 1, 0)

        self.draw_bone_collections(
            layout,
            armature,
            grp_v_separation,
            btn_h_separation,
            btn_v_separation,
            operator_exists,
            is_pose_mode,
            active_pose_bone,
            selected_pose_bones,
            is_v41_plus,
        )

        grouped_properties = defaultdict(lambda: defaultdict(list))
        for prop in armature.data.custom_properties:
            if prop.cp_pin_state:
                group_id = prop.group_id
                row = prop.cp_row_int
                priority = prop.cp_priority_int
                grouped_properties[group_id][row].append((priority, prop))

        # Don't draw an empty box if no group properties exist
        if not grouped_properties:
            return

        cp_container = layout.box()
        cp_sub = cp_container.column(align=True)
        group_order = {
            g.unique_id: i
            for i, g in enumerate(armature.data.custom_properties_ui_groups)
        }

        for group_id in sorted(
            grouped_properties.keys(), key=lambda x: group_order.get(x, -1)
        ):
            group_item = self.get_group_by_id(
                armature, group_id, "custom_properties_ui_groups"
            )
            if group_item:
                if group_order.get(group_id, -1) > 1:
                    cp_sub.separator(factor=grp_v_separation)
                self.draw_group(
                    cp_sub,
                    group_item,
                    grouped_properties[group_id],
                    armature,
                    self.draw_custom_property,
                )

    def draw_bone_collections(
        self,
        layout,
        armature,
        grp_v_separation,
        btn_h_separation,
        btn_v_separation,
        operator_exists,
        is_pose_mode,
        active_pose_bone,
        selected_pose_bones,
        is_v41_plus,
    ):
        bc_container = layout.box()
        bc_sub = bc_container.column(align=True)
        group_index_map = {}
        colls_all = getattr(armature.data, "collections_all", armature.data.collections)

        for idx, group in enumerate(
            getattr(armature.data, "bone_collections_ui_groups", [])
        ):
            group_index_map[group.unique_id] = idx

        grouped_collections = defaultdict(lambda: defaultdict(list))
        for collection in colls_all.values():
            if collection.get("rig_ui_pin", False):
                group_id = collection.get("group_id")
                row_index = collection.get("rig_ui_row", 0)
                if group_id in group_index_map:
                    grouped_collections[group_index_map[group_id]][row_index].append(
                        collection
                    )

        groups_dict = {
            g.unique_id: g
            for g in getattr(armature.data, "bone_collections_ui_groups", [])
        }

        for group_idx in sorted(grouped_collections.keys()):
            if group_idx > 1:
                bc_sub.separator(factor=grp_v_separation)

            group_unique_id_list = [
                k for k, v in group_index_map.items() if v == group_idx
            ]
            group_unique_id = group_unique_id_list[0] if group_unique_id_list else None
            group_item = groups_dict.get(group_unique_id)

            if group_item:
                group_box = bc_sub.column()
                self.draw_group_header_main_ui(group_box, group_item)
                if group_item.toggle:
                    group_inner_box = group_box.column(align=True)
                    for row_idx in sorted(grouped_collections[group_idx].keys()):
                        group_inner_box.separator(factor=btn_v_separation)
                        row_layout = group_inner_box.row(align=True)
                        for collection in sorted(
                            grouped_collections[group_idx][row_idx],
                            key=lambda x: (x.get("rig_ui_priority", 0), x.name),
                        ):
                            if collection["rig_ui_priority"] > 1:
                                row_layout.separator(factor=btn_h_separation)
                            self.draw_collection(
                                armature,
                                row_layout,
                                collection,
                                operator_exists,
                                is_pose_mode,
                                active_pose_bone,
                                selected_pose_bones,
                                is_v41_plus,
                                btn_h_separation,
                            )
                    group_inner_box.separator(factor=btn_v_separation)

        ungrouped_pinned_collections = [
            col
            for col in colls_all.values()
            if col.get("rig_ui_pin", False)
            and col.get("group_id") not in group_index_map
        ]
        if ungrouped_pinned_collections:
            bc_sub.label(text="Ungrouped Pinned Bone Collections")
            ungrouped_container = bc_sub.box()
            ungrouped_column = ungrouped_container.column(align=True)
            ungrouped_pinned_row_collections = defaultdict(list)
            for collection in ungrouped_pinned_collections:
                row_index = collection.get("rig_ui_row", 0)
                ungrouped_pinned_row_collections[row_index].append(collection)

            for row_index, collections_in_row in sorted(
                ungrouped_pinned_row_collections.items()
            ):
                row_layout = ungrouped_column.row(align=True)
                for collection in collections_in_row:
                    if collection["rig_ui_priority"] > 1:
                        row_layout.separator(factor=btn_h_separation)
                    self.draw_collection(
                        armature,
                        row_layout,
                        collection,
                        operator_exists,
                        is_pose_mode,
                        active_pose_bone,
                        selected_pose_bones,
                        is_v41_plus,
                        btn_h_separation,
                    )

    def draw_group_header_main_ui(self, layout, group_item):
        header_container = layout.column()
        armature_data = group_item.id_data
        display_type = group_item.display_type
        label = (
            group_item.name
            if armature_data.rig_ui_props.group_headers_customProperties
            or not group_item.toggle
            else " "
        )
        if display_type == "HEADER_BOX":
            icon = "TRIA_DOWN" if group_item.toggle else "TRIA_RIGHT"
        else:
            icon = "DOWNARROW_HLT" if group_item.toggle else "RIGHTARROW"
        box = (
            header_container.box() if display_type == "HEADER_BOX" else header_container
        )
        if display_type in ["HEADER", "HEADER_BOX"]:
            box.prop(group_item, "toggle", text=label, emboss=False, icon=icon)
        elif display_type in ["LABEL", "LABEL_BOX", "BOX"]:
            box.label(text=label)
        box.scale_y = 0.5 if display_type == "HEADER_BOX" else 0.8

    def draw_group(self, layout, group_item, grouped_properties, armature, draw_func):
        display_type = group_item.display_type
        if display_type in ["HEADER", "HEADER_BOX"]:
            self.draw_group_header_main_ui(layout, group_item)
            if group_item.toggle:
                self.draw_properties_group(
                    layout.box(), group_item, grouped_properties, armature, draw_func
                )
        elif display_type in ["LABEL", "LABEL_BOX", "BOX"]:
            self.draw_group_with_label(
                layout, group_item, grouped_properties, armature, draw_func
            )
        elif display_type in ["NONE"]:
            self.draw_properties_group(
                layout, group_item, grouped_properties, armature, draw_func
            )

    def draw_properties_group(
        self, layout, group_item, grouped_properties, armature, draw_func
    ):
        armature_data = armature.data
        vertical_spacing = armature_data.rig_ui_props.ui_button_vertical_separation
        horizontal_spacing = armature_data.rig_ui_props.ui_button_horizontal_separation
        row_items = defaultdict(list)
        for row, props_list in grouped_properties.items():
            row_items[row].extend(props_list)

        vertical_wrapper = layout.column(align=True)
        for row_number in sorted(row_items.keys()):
            vertical_wrapper.separator(factor=vertical_spacing)
            row_layout = vertical_wrapper.row(align=True)
            for item in sorted(
                row_items[row_number],
                key=lambda x: (
                    x[0],
                    x[1].cp_priority_int,
                    x[1].cp_bone_name.lower(),
                    x[1].cp_prop_name.lower(),
                ),
            ):
                draw_func(armature, row_layout, item[1], horizontal_spacing)
            vertical_wrapper.separator(factor=vertical_spacing)

    def draw_group_with_label(
        self, layout, group_item, grouped_properties, armature, draw_func
    ):
        armature_data = armature.data
        container = (
            layout.box() if group_item.display_type in ["LABEL_BOX", "BOX"] else layout
        )
        if (
            armature_data.rig_ui_props.group_headers_customProperties
            and group_item.display_type
            in [
                "LABEL",
                "LABEL_BOX",
            ]
        ):
            container.row().label(text=group_item.name)
        self.draw_properties_group(
            container, group_item, grouped_properties, armature, draw_func
        )

    def get_group_by_id(self, armature, group_id, group_list_name):
        for group in getattr(armature.data, group_list_name):
            if group.unique_id == group_id:
                return group
        return None

    @staticmethod
    def draw_custom_property(armature, layout, prop_item, horizontal_separation=0.2):
        bone = armature.pose.bones.get(prop_item.cp_bone_name)
        btn_h_separation = horizontal_separation * 3
        if bone and prop_item.cp_prop_name in bone.keys():
            prop_value = bone[prop_item.cp_prop_name]
            prop_type = type(prop_value)
            prop_custom_name_display = (
                prop_item.cp_prop_custom_name
                if prop_item.cp_prop_custom_name
                else prop_item.cp_prop_name
            )
            cp_row = layout.row(align=False)
            cp_button_row = cp_row.row(align=True)
            cp_button_row.scale_x = prop_item.button_factor

            if prop_item.get("cp_priority_int", 0) > 1:
                cp_button_row.separator(factor=btn_h_separation)

            if prop_type == bool:
                if prop_item.cp_name_inside:
                    cp_button_row.prop(
                        bone,
                        f'["{prop_item.cp_prop_name}"]',
                        text=prop_custom_name_display,
                        toggle=True,
                    )
                else:
                    cp_button_row.label(text=prop_custom_name_display)
                    cp_button_row.prop(
                        bone,
                        f'["{prop_item.cp_prop_name}"]',
                        text="",
                        icon="CHECKBOX_HLT" if prop_value else "CHECKBOX_DEHLT",
                    )
            elif prop_type in (int, float):
                slider = prop_type == float
                if prop_item.cp_name_inside:
                    cp_button_row.prop(
                        bone,
                        f'["{prop_item.cp_prop_name}"]',
                        text=prop_custom_name_display,
                        slider=slider,
                    )
                else:
                    cp_button_row.label(text=prop_custom_name_display)
                    cp_button_row.prop(
                        bone, f'["{prop_item.cp_prop_name}"]', text="", slider=slider
                    )

    @staticmethod
    def draw_collection(
        armature,
        layout,
        collection,
        operator_exists,
        is_pose_mode,
        active_pose_bone,
        selected_pose_bones,
        is_v41_plus,
        horizontal_separation=0.2,
    ):
        props = armature.data.rig_ui_props
        colls_all = getattr(armature.data, "collections_all", armature.data.collections)

        bone_in_collection = False
        if is_pose_mode and active_pose_bone and selected_pose_bones:
            bone_in_collection = (
                active_pose_bone in selected_pose_bones
                and active_pose_bone.name in collection.bones
            )

        is_visible = collection.is_visible
        if is_v41_plus:
            is_solo = collection.is_solo
            isolate_on = any(c.is_solo for c in colls_all.values())
        else:
            is_solo = False
            isolate_on = False

        fade_out = is_visible
        highlight = bone_in_collection or is_solo

        button_row = layout.row(align=False)
        button_row.active = is_solo if isolate_on else fade_out

        if collection.get("display_name", False):
            button_row.scale_x = collection["button_factor"]

        icon_name = (
            "SOLO_ON"
            if is_solo
            else (
                "NONE"
                if collection.get("icon_name", "BLANK1") == "BLANK1"
                else collection.get("icon_name")
            )
        )
        display_text = collection.name if collection.get("display_name", False) else ""

        if props.bc_button_types == "SPECIAL" and operator_exists:
            button_op = button_row.operator(
                "rig_ui.bone_collection_action",
                text=display_text,
                icon=icon_name,
                emboss=True,
                depress=highlight,
            )
            button_op.collection_name = collection.name
        else:
            button_row.prop(
                collection, "is_visible", text=display_text, icon=icon_name, toggle=True
            )


class RIG_UI_PG_groups_ListItem_export(bpy.types.PropertyGroup):
    unique_id: bpy.props.StringProperty(
        name="Unique ID", default="", override={"LIBRARY_OVERRIDABLE"}
    )
    name: bpy.props.StringProperty(
        name="Name", default="Unnamed", override={"LIBRARY_OVERRIDABLE"}
    )
    toggle: bpy.props.BoolProperty(
        name="Toggle", default=True, override={"LIBRARY_OVERRIDABLE"}
    )
    display_type: bpy.props.EnumProperty(
        name="Display Type",
        items=[
            ("BOX", "Box", ""),
            ("LABEL", "Label", ""),
            ("LABEL_BOX", "Box with Label", ""),
            ("HEADER", "Toggleable header", ""),
            ("HEADER_BOX", "Toggleable header Box", ""),
            ("NONE", "No style", ""),
        ],
        default="BOX",
        override={"LIBRARY_OVERRIDABLE"},
    )


class RIG_UI_PG_CustomProperties_Item(bpy.types.PropertyGroup):
    is_moving: bpy.props.BoolProperty(default=False)
    active_section: bpy.props.StringProperty(default="")
    cp_pin_state: bpy.props.BoolProperty(
        name="Pin",
        description="Pins the bookmark to the Custom Properties UI",
        default=False,
    )
    icon_name: bpy.props.StringProperty(
        name="Icon",
        description="Icon representing the Custom Property",
        default="BLANK1",
    )
    cp_bone_name: bpy.props.StringProperty(name="Bone Name")
    cp_prop_name: bpy.props.StringProperty(name="Property Name")
    cp_prop_custom_name: bpy.props.StringProperty(
        name="Custom Name",
        description="Custom name to display for the property",
        default="",
    )
    cp_name_inside: bpy.props.BoolProperty(
        name="Property name inside",
        description="Display the property name inside the value",
        default=True,
    )
    button_factor: bpy.props.FloatProperty(
        name="Button Factor",
        default=1,
        min=1,
        max=4,
        description="Adjust the button ui size",
    )
    group_id: bpy.props.StringProperty(
        name="Group ID", description="Unique identifier of the associated group"
    )
    cp_group_int: bpy.props.IntProperty(
        name="Group",
        description="""Lower group items are drawn first in the UI
To be able to include properties in groups the groups need to exist
Add or manage groups in the Custom Properties Setup panel in Edit Mod""",
        default=0,
    )
    cp_row_int: bpy.props.IntProperty(
        name="Row",
        description="Lower row items are drawn first in the group",
        default=1,
    )
    cp_priority_int: bpy.props.IntProperty(
        name="Priority",
        description="Lower priority items are drawn first in the row",
        default=1,
    )


class RIG_UI_PG_ArmatureProperties(bpy.types.PropertyGroup):
    """Armature level property group"""

    group_headers_customProperties: bpy.props.BoolProperty(
        name="Toggle Group Headers",
        description="Hide or display the Groups Headers for the Custom Properties",
        default=True,
        override={"LIBRARY_OVERRIDABLE"},
    )
    bc_button_types: bpy.props.EnumProperty(
        name="Button Type",
        items=[
            ("SPECIAL", "Pro buttons", ""),
            ("TOGGLE", "Basic buttons", ""),
        ],
        default="SPECIAL",
        override={"LIBRARY_OVERRIDABLE"},
    )
    ui_sections_vertical_separation: bpy.props.FloatProperty(
        default=0.0,
        min=0.0,
        max=1.0,
        description="Vertical separation between sections",
    )
    ui_groups_vertical_separation: bpy.props.FloatProperty(
        default=0.0,
        min=0.0,
        max=1.0,
        description="Vertical separation between groups",
    )
    ui_button_vertical_separation: bpy.props.FloatProperty(
        default=0.0,
        min=0.0,
        max=1.0,
        description="Vertical separation between buttons",
    )
    ui_button_horizontal_separation: bpy.props.FloatProperty(
        default=0.0,
        min=0.0,
        max=1.0,
        description="Horizontal separation between buttons",
    )
    ui_section_boxes: bpy.props.BoolProperty(
        default=True,
        description="Draw section backround boxes",
    )
    ui_section_headers: bpy.props.BoolProperty(
        default=True,
        description="Draw section headers",
    )


classes = (
    RIG_UI_OT_armature_configure,
    RIG_UI_PG_groups_ListItem_export,
    RIG_UI_PG_CustomProperties_Item,
)


def register():
    try:
        bpy.utils.register_class(RIG_UI_PT_Universal)
        for cls in classes:
            bpy.utils.register_class(cls)

        try:
            bpy.utils.register_class(RIG_UI_PG_ArmatureProperties)
        except Exception as e:
            print(e)

        if not hasattr(bpy.types.Armature, "bone_collections_ui_groups"):
            bpy.types.Armature.bone_collections_ui_groups = (
                bpy.props.CollectionProperty(type=RIG_UI_PG_groups_ListItem_export)
            )
        if not hasattr(bpy.types.Armature, "visibility_bookmarks_ui_groups"):
            bpy.types.Armature.visibility_bookmarks_ui_groups = (
                bpy.props.CollectionProperty(type=RIG_UI_PG_groups_ListItem_export)
            )
        if not hasattr(bpy.types.Armature, "custom_properties_ui_groups"):
            bpy.types.Armature.custom_properties_ui_groups = (
                bpy.props.CollectionProperty(type=RIG_UI_PG_groups_ListItem_export)
            )
        if not hasattr(bpy.types.Armature, "custom_properties"):
            bpy.types.Armature.custom_properties = bpy.props.CollectionProperty(
                type=RIG_UI_PG_CustomProperties_Item
            )

        if not hasattr(bpy.types.Armature, "rig_ui_props"):
            bpy.types.Armature.rig_ui_props = bpy.props.PointerProperty(
                type=RIG_UI_PG_ArmatureProperties
            )

        for a in bpy.data.armatures:
            if not hasattr(a, "rig_ui_props"):
                a.rig_ui_props = bpy.types.RIG_UI_PG_ArmatureProperties()

    except Exception as e:
        print(e)


def unregister():
    try:
        del bpy.types.Armature.bone_collections_ui_groups
        del bpy.types.Armature.visibility_bookmarks_ui_groups
        del bpy.types.Armature.custom_properties_ui_groups
        del bpy.types.Armature.custom_properties
        del bpy.types.Armature.rig_ui_props
        for cls in classes:
            bpy.utils.unregister_class(cls)
        bpy.utils.unregister_class(RIG_UI_PT_Universal)

    except Exception as e:
        pass
