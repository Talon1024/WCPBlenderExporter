#!/usr/bin/env python3
from . import iff


class BSPNode:

    def __init__(self, a, b, c, d, back=None, front=None, boundary=None):
        # I think VISION's BSP system is based on the plane equation
        # Ax + By + Cz + D = 0
        #
        # Here are the calculations for A, B, C, and D...
        # A = (-By - Cz - D) / x
        # B = (-Ax - Cz - D) / y
        # C = (-Ax - By - D) / z
        # D = -Ax - By - Cz

        self.a = float(a)
        self.b = float(b)
        self.c = float(c)
        self.d = float(d)

        self.back = back  # Node behind
        self.front = front  # Node in front
        self.boundary = boundary  # Vertices of boundary plane(?)

    def to_iff(self):
        data_chunk = iff.IffChunk(
            # I used 0 and -1 (0xFFFF) as the first and last members because
            # that's what I noticed when I looked at the DATA chunks in models
            # from the original game.
            "DATA", 0, self.a, self.b, self.c, self.d, -1)
        back_form = iff.IffForm("BACK", self.back)
        front_form = iff.IffForm("FRNT", self.front)
        vert_chunk = iff.IffChunk("VERT", self.boundary)

        return (data_chunk, back_form, front_form, vert_chunk)


class BSPTree:

    def __init__(self, root_node):
        self.root_node = root_node

    def to_iff(self):
        tree_form = iff.IffForm("TREE", root_node.to_iff())
        return tree_form
