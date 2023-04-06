# Python built-in modules
from bisect import bisect_left      # search sorted keyframe lists

# External, non built-in modules
import OpenGL.GL as GL              # standard Python OpenGL wrapper
import glfw                         # lean window system wrapper for OpenGL
import numpy as np                  # all matrix manipulations & OpenGL args

from core import Node
from transform import (lerp, quaternion_slerp, quaternion_matrix, translate,
                       scale, identity)


# -------------- Keyframing Utilities TP6 ------------------------------------
class KeyFrames:
    """ Stores keyframe pairs for any value type with interpolation_function"""

    def __init__(self, time_value_pairs, interpolation_function=lerp):
        if isinstance(time_value_pairs, dict):  # convert to list of pairs
            time_value_pairs = time_value_pairs.items()
        keyframes = sorted(((key[0], key[1]) for key in time_value_pairs))
        self.times, self.values = zip(*keyframes)  # pairs list -> 2 lists
        self.interpolate = interpolation_function

    def value(self, time):
        """ Computes interpolated value from keyframes, for a given time """

        time = max(min(time, self.times[-1]), self.times[0])

        index = bisect_left(self.times, time)

        return self.interpolate(self.values[index - 1], self.values[index], (time - self.times[index - 1]) / (self.times[index] - self.times[index - 1]))


class TransformKeyFrames:
    """ KeyFrames-like object dedicated to 3D transforms """

    def __init__(self, translate_keys, rotate_keys, scale_keys):
        """ stores 3 keyframe sets for translation, rotation, scale """
        self.translate_keys = KeyFrames(translate_keys)
        self.rot_keys = KeyFrames(rotate_keys, quaternion_slerp)
        self.scale_keys = KeyFrames(scale_keys)

    def value(self, time):
        """ Compute each component's interpolation and compose TRS matrix """
        T = translate(self.translate_keys.value(time))
        R = quaternion_matrix(self.rot_keys.value(time))
        S = scale(self.scale_keys.value(time))
        return T @ R @ S


class KeyFrameControlNode(Node):
    """ Place node with transform keys above a controlled subtree """

    def __init__(self, trans_keys, rot_keys, scale_keys, transform=identity(), duration=None):
        super().__init__(transform=transform)
        self.keyframes = TransformKeyFrames(trans_keys, rot_keys, scale_keys)
        self.duration = duration

    def draw(self, primitives=GL.GL_TRIANGLES, **uniforms):
        """ When redraw requested, interpolate our node transform from keys """
        time = glfw.get_time()
        if self.duration is not None:
            time %= self.duration
        self.transform = self.keyframes.value(time)
        super().draw(primitives=primitives, **uniforms)


# -------------- Linear Blend Skinning : TP7 ---------------------------------
class Skinned:
    """ Skinned mesh decorator, passes bone world transforms to shader """

    def __init__(self, mesh, bone_nodes, bone_offsets):
        self.mesh = mesh

        # store skinning data
        self.bone_nodes = bone_nodes
        self.bone_offsets = np.array(bone_offsets, np.float32)

    def draw(self, **uniforms):
        world_transforms = [node.world_transform for node in self.bone_nodes]
        uniforms['bone_matrix'] = world_transforms @ self.bone_offsets
        self.mesh.draw(**uniforms)
