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

import numbers

import numpy

import awkward.base

class ChunkedArray(awkward.base.AwkwardArray):
    def __init__(self, chunks, writeable=True, appendable=True, appendsize=1024):
        self._appendable = appendable
        self.chunks = chunks
        self.writeable = writeable
        self.appendsize = appendsize

    @property
    def chunks(self):
        return self._chunks

    @chunks.setter
    def chunks(self, value):
        try:
            iter(value)
        except TypeError:
            raise TypeError("chunks must be iterable")

        if self._appendable and not (hasattr(value, "append") and callable(value.append)):
            raise TypeError("because appendable=True, chunks must have an append method")

        self._chunks = value

    @property
    def writeable(self):
        return self._writeable

    @writeable.setter
    def writeable(self, value):
        self._writeable = bool(value)

    @property
    def appendable(self):
        return self._appendable

    @appendable.setter
    def appendable(self, value):
        if value and not (hasattr(value, "append") and callable(value.append)):
            raise TypeError("chunks must have an append method for appendable=True")
        self._appendable = bool(value)

    @property
    def appendsize(self):
        return self._appendsize

    @appendsize.setter
    def appendsize(self, value):
        if not isinstance(value, (numbers.Integral, numpy.integer)) or value <= 0:
            raise TypeError("appendsize must be a positive integer")
        self._appendsize = value

    @property
    def dtype(self):
        chunk = None
        for chunk in self._chunks:
            break
        if chunk is None:
            raise ValueError("chunks is empty; cannot determine dtype")
        else:
            if not isinstance(chunk, awkward.base.AwkwardArray):
                chunk = numpy.array(chunk, copy=False)
            return numpy.dtype((chunk.dtype, getattr(chunk, "shape", (0,))[1:]))

    @property
    def dimension(self):
        try:
            return self.dtype.shape
        except ValueError:
            raise ValueError("chunks is empty; cannot determine dimension")

    def __iter__(self):
        for chunk in self._chunks:
            for x in chunk:
                yield x

    def __str__(self):
        values = []
        for x in self:
            if len(values) == 7:
                return "[{0} ...]".format(" ".join(str(x) for x in values))
            values.append(x)
        return "[{0}]".format(" ".join(str(x) for x in values))

    def _chunkiterator(self):
        sofar = 0
        for chunk in self._chunks:
            yield sofar, chunk
            sofar += len(chunk)

    def _slicedchunks(self, start, stop, step):
        if step == 0:
            raise ValueError("slice step cannot be zero")
        elif step is None:
            step = 1

        slicedchunks = []
        localstep = 1 if step > 0 else -1
        for sofar, chunk in self._chunkiterator():
            if step > 0:
                if start is None:
                    localstart = None
                elif start < sofar:
                    localstart = None
                elif sofar <= start < sofar + len(chunk):
                    localstart = start - sofar
                else:
                    continue

                if stop is None:
                    localstop = None
                elif stop <= sofar:
                    break
                elif sofar < stop < sofar + len(chunk):
                    localstop = stop - sofar
                else:
                    localstop = None

            else:
                if start is None:
                    localstart = None
                elif start < sofar:
                    break
                elif sofar <= start < sofar + len(chunk):
                    localstart = start - sofar
                else:
                    localstart = None

                if stop is None:
                    localstop = None
                elif stop < sofar:
                    localstop = None
                elif sofar <= stop < sofar + len(chunk):
                    localstop = stop - sofar
                else:
                    continue

            slicedchunk = chunk[localstart:localstop:localstep]   # don't apply step here
            if len(slicedchunk) != 0:                             # avoid mixing empty list dtype
                slicedchunks.append(slicedchunk)

        if step > 0:
            return slicedchunks
        else:
            return list(reversed(slicedchunks))

    def _zerolen(self):
        try:
            dtype = self.dtype
        except ValueError:
            return numpy.empty(0)
        else:
            return numpy.empty(0, dtype)

    def __getitem__(self, where):
        if not isinstance(where, tuple):
            where = (where,)
        head, rest = where[0], where[1:]

        if isinstance(head, (numbers.Integral, numpy.integer)):
            if head < 0:
                raise IndexError("negative indexes are not allowed in ChunkedArray")
            for sofar, chunk in self._chunkiterator():
                if sofar <= head < sofar + len(chunk):
                    chunk = numpy.array(chunk, copy=False)
                    return chunk[(head - sofar,) + rest]
            raise IndexError("index {0} out of bounds for length {1}".format(head, sofar + len(chunk)))

        elif isinstance(head, slice):
            start, stop, step = head.start, head.stop, head.step
            if (start is not None and start < 0) or (stop is not None and stop < 0):
                raise IndexError("negative indexes are not allowed in ChunkedArray")

            slicedchunks = self._slicedchunks(start, stop, step)

            if len(slicedchunks) == 0:
                return self._zerolen()

            if len(slicedchunks) == 1:
                out = numpy.array(slicedchunks[0], copy=False)
            else:
                out = numpy.concatenate(slicedchunks)

            if step is None or step == 1:
                return out
            else:
                return out[::abs(step)]

        else:
            head = numpy.array(head, copy=False)
            if len(head.shape) == 1 and issubclass(head.dtype.type, numpy.integer):
                if len(head) == 0:
                    return self._zerolen()

                if (head < 0).any():
                    raise IndexError("negative indexes are not allowed in ChunkedArray")
                maxindex = head.max()

                out = numpy.empty(len(head), dtype=self.dtype)
                for sofar, chunk in self._chunkiterator():
                    chunk = numpy.array(chunk, copy=False)

                    indexes = head - sofar
                    mask = (indexes >= 0)
                    numpy.bitwise_and(mask, (indexes < len(chunk)), mask)

                    masked = indexes[mask]
                    if len(masked) != 0:
                        out[mask] = chunk[masked]

                    if sofar + len(chunk) > maxindex:
                        break

                if maxindex >= sofar + len(chunk):
                    raise IndexError("index {0} out of bounds for length {1}".format(maxindex, sofar + len(chunk)))

                return out

            elif len(head.shape) == 1 and issubclass(head.dtype.type, (numpy.bool, numpy.bool_)):
                numtrue = numpy.count_nonzero(head)

                if len(self._chunks) == len(head) == 0 or numtrue == 0:
                    return self._zerolen()

                this = next = 0
                out = numpy.empty(numtrue, dtype=self.dtype)
                for sofar, chunk in self._chunkiterator():
                    chunk = numpy.array(chunk, copy=False)
                    submask = head[sofar : sofar + len(chunk)]

                    next += numpy.count_nonzero(submask)
                    out[this:next] = chunk[submask]
                    this = next

                if len(head) != sofar + len(chunk):
                    raise IndexError("boolean index did not match indexed array along dimension 0; dimension is {0} but corresponding boolean dimension is {1}".format(sofar + len(chunk), len(head)))

                return out

            else:
                raise TypeError("cannot interpret shape {0}, dtype {1} as a fancy index or mask".format(head.shape, head.dtype))

class PartitionedArray(ChunkedArray):
    pass
