from typing import List

import bpy

import rr_avatar_tools
import rr_avatar_tools.data


class CollectionState:
    collection: bpy.types.Collection
    hide_render: bool
    hide_select: bool
    hide_viewport: bool

    def __init__(self, collection: bpy.types.Collection):
        self.collection = collection
        self.hide_render = collection.hide_render
        self.hide_select = collection.hide_select
        self.hide_viewport = collection.hide_viewport

    def show(self):
        self.collection.hide_render = False
        self.collection.hide_select = False
        self.collection.hide_viewport = False

    def restore(self):
        if not self.collection:
            return

        if self.collection not in rr_avatar_tools.data.collections:
            return

        self.collection.hide_render = self.hide_render
        self.collection.hide_select = self.hide_select
        self.collection.hide_viewport = self.hide_viewport


class LayerCollectionState:
    layer_collection: bpy.types.LayerCollection
    hide_viewport: bool

    def __init__(self, layer_collection: bpy.types.LayerCollection):
        self.layer_collection = layer_collection
        self.hide_viewport = layer_collection.hide_viewport

    def show(self):
        self.layer_collection.hide_viewport = False

    def restore(self):
        if not self.layer_collection:
            return

        if self.layer_collection not in rr_avatar_tools.data.layer_collections:
            return

        self.layer_collection.hide_viewport = self.hide_viewport


class ObjectState:
    object: bpy.types.Object
    hide: bool
    hide_render: bool
    hide_select: bool
    hide_viewport: bool
    select: bool

    def __init__(self, object_):
        self.object = object_
        self.hide = object_.hide_get()
        self.hide_render = object_.hide_render
        self.hide_select = object_.hide_select
        self.hide_viewport = object_.hide_viewport
        self.select = object_.select_get()

    def show(self):
        self.object.hide_set(False)
        self.object.hide_render = False
        self.object.hide_select = False
        self.object.hide_viewport = False

    def restore(self):
        if not self.object:
            return

        if self.object not in rr_avatar_tools.data.objects:
            return

        self.object.hide_set(self.hide)
        self.object.hide_render = self.hide_render
        self.object.hide_select = self.hide_select
        self.object.hide_viewport = self.hide_viewport
        self.object.select_set(self.select)


def put_file_in_known_good_state(func):
    """Put file in a known good state and restore state after function call."""

    def wrapper(*args, **kwargs):
        # Ensure object mode
        mode = bpy.context.object.mode if bpy.context.active_object else None
        if mode and mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Checks and Remove all animation data from Object
        obj = bpy.context.active_object if bpy.context.active_object else None
        if obj and obj.animation_data and any([obj.animation_data.action, obj.animation_data.drivers, obj.animation_data.nla_tracks]):
            obj.animation_data_clear()
        

        # Cache current state
        active = bpy.context.active_object
        collections = [CollectionState(c) for c in rr_avatar_tools.data.collections]
        layer_collections = [
            LayerCollectionState(l) for l in rr_avatar_tools.data.layer_collections
        ]
        objects = [ObjectState(o) for o in bpy.data.objects]

        # Put in known good state
        for c in collections:
            c.show()

        for l in layer_collections:
            l.show()

        for o in objects:
            o.show()

        frame = bpy.context.scene.frame_current
        bpy.context.scene.frame_set(0)

        # Call wrapped function
        result = func(*args, **kwargs)

        bpy.context.scene.frame_set(frame)

        # Restore previous state
        try:
            bpy.context.view_layer.objects.active = active
        except ReferenceError:
            # Ignore if the active object has been removed
            pass

        for c in collections:
            c.restore()

        for l in layer_collections:
            l.restore()

        for o in objects:
            o.restore()

        # Restore previous mode
        if mode and mode != "OBJECT":
            bpy.ops.object.mode_set(mode=mode)

        return result

    return wrapper


def layer_collections_recursive() -> List[bpy.types.LayerCollection]:
    """Returns a flattened sequence of LayerCollection objects"""

    def walk_view_layers(collection):
        return sum(
            [walk_view_layers(c) for c in collection.children], start=[collection]
        )

    return walk_view_layers(bpy.context.view_layer.layer_collection)
