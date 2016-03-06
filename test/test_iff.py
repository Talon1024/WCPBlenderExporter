#!/usr/bin/env python3
# -*- coding: utf8 -*-

from os import getcwd
import os.path
import sys
import unittest

sys.path.append(os.path.abspath(getcwd() + "/.."))


class TestIFF(unittest.TestCase):

    def setUp(self):
        import iff
        self.ifff = iff.IffForm("FONG")
        self.iffc_ponf = iff.IffChunk("PONF")
        self.iffc_ponf.add_member(12.345)
        self.iffc_ponf.add_member("I am poncho man!")
        self.iffc_ponf.add_member(12345)
        self.ifff.add_member(self.iffc_ponf)
        self.iffc_gone = iff.IffChunk("GONE")
        self.iffc_gone.add_member(42)
        self.ifff.add_member(self.iffc_gone)

    def test_iff_form(self):
        import iff
        self.assertIsNotNone(iff.IffForm("BABY"), 'Cannot create Form BABY!')
        self.assertEqual("IffForm 'BOOK'", str(iff.IffForm("BOOK")),
                         "IffForm isn't converting to a string properly!")

        # Exception testing.
        # Invalid Chunk ID
        self.assertRaises(ValueError, iff.IffForm, ("\x02Aéâ"))
        # Invalid member types
        self.assertRaises(TypeError, iff.IffForm, "DETA", [192, 2.25, "abc"])

    def test_iff_chunk(self):
        import iff
        self.assertIsNotNone(iff.IffChunk("DOCK"), 'Cannot create chunk DOCK!')
        self.assertEqual("IffChunk 'SOCK'", str(iff.IffChunk("SOCK")),
                         "IffChunk isn't converting to a string properly!")

        # Exception testing.
        # Invalid Chunk ID
        self.assertRaises(ValueError, iff.IffChunk, ("\x02Aéâ"))
        # Invalid member types
        self.assertRaises(TypeError, iff.IffChunk, "META",
                          [iff.IffChunk("SETA"), iff.IffForm("ZETA")])

    def test_chunk(self):
        """Check chunk length and content"""
        self.assertEqual(25, self.iffc_ponf.get_length(),
                         'Chunk PONF is wrong length!')
        self.assertEqual(4, self.iffc_gone.get_length(),
                         'Chunk GONE is wrong length!')
        self.assertEqual(
            b'GONE\x00\x00\x00\x04*\x00\x00\x00', self.iffc_gone.to_bytes(),
            'chunk GONE is outputting incorrectly')
        self.assertEqual(
            b'PONF\x00\x00\x00\x19\x1F\x85EAI am poncho man!\x0090\x00\x00'
            b'\x00',
            self.iffc_ponf.to_bytes(), 'chunk PONF is outputting incorrectly')

    def test_form(self):
        """Check root form length and content"""
        self.assertEqual(50, self.ifff._length, 'Form FONG is wrong length!')
        self.assertEqual(
            b'FORM\x00\x00\x002FONGPONF\x00\x00\x00\x19\x1f\x85EAI am poncho '
            b'man!\x0090\x00\x00\x00GONE\x00\x00\x00\x04*\x00\x00\x00',
            self.ifff.to_bytes(), 'Form FONG is outputting incorrectly!')


if __name__ == '__main__':
    unittest.main()
