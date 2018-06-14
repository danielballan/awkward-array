#!/usr/bin/env python

# Copyright (c) 2018, DIANA-HEP
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest

import numpy

from awkward import *

class TestChunked(unittest.TestCase):
    def runTest(self):
        pass

    def test_chunked_iteration(self):
        a = ChunkedArray([[], [0, 1, 2, 3, 4], [5, 6], [], [7, 8, 9], []])
        self.assertEqual(a.tolist(), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

        a = ChunkedArray([[0, 1, 2, 3, 4], [5, 6], [], [7, 8, 9], []])
        self.assertEqual(a.tolist(), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

        a = ChunkedArray([[], [0, 1, 2, 3, 4], [5, 6], [], [7, 8, 9]])
        self.assertEqual(a.tolist(), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

        a = ChunkedArray([[]])
        self.assertEqual(a.tolist(), [])

        a = ChunkedArray([])
        self.assertEqual(a.tolist(), [])

    def test_chunked_dtype(self):
        a = ChunkedArray([[], [0, 1, 2, 3, 4], [5, 6], [], [7, 8, 9], []])
        self.assertEqual(a.dtype, numpy.dtype(float))

        a = ChunkedArray([[0, 1, 2, 3, 4], [5, 6], [], [7, 8, 9], []])
        self.assertEqual(a.dtype, numpy.dtype(int))

        a = ChunkedArray([])
        self.assertRaises(ValueError, lambda: a.dtype)

    def test_chunked_get_index(self):
        a = ChunkedArray([[], [0, 1, 2, 3, 4], [5, 6], [], [7, 8, 9], []])
        self.assertEqual([a[i] for i in range(10)], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        print [a[i : i + 1] for i in range(10)]



