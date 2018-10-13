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

import fnmatch
import importlib
import json
import numbers
import zlib

import numpy

import awkward.util
import awkward.version

compression = [
    [8192, [numpy.bool_, numpy.bool, numpy.integer], "*", (zlib.compress, ("zlib", "decompress"))],
    ]

whitelist = [["numpy", "frombuffer"], ["zlib", "decompress"], ["awkward", "*"], ["awkward.persist", "*"]]

def dtype2json(obj):
    if obj.subdtype is not None:
        dt, sh = obj.subdtype
        return (dtype2json(dt), sh)
    elif obj.names is not None:
        return [(n, dtype2json(obj[n])) for n in obj.names]
    else:
        return str(obj)

def json2dtype(obj):
    def recurse(obj):
        if isinstance(obj, (list, tuple)) and len(obj) > 0 and (isinstance(obj[-1], numbers.Integral) or isinstance(obj[0], str) or (isinstance(obj[-1], (list, tuple)) and all(isinstance(x, numbers.Integral) for x in obj[-1]))):
            return tuple(recurse(x) for x in obj)
        elif isinstance(obj, (list, tuple)):
            return [recurse(x) for x in obj]
        else:
            return obj
    return numpy.dtype(recurse(obj))

def serialize(obj, sink, name="", compression=compression):
    import awkward.array.base

    if isinstance(compression, tuple) and len(compression) == 2 and callable(compression[0]):
        compression = [(0, (object,), "*", (zlib.compress, ("zlib", "decompress")))]

    seen = {}
    def fill(obj, context):
        if id(obj) in seen:
            return {"ref": seen[id(obj)]}

        ident = len(seen)
        seen[id(obj)] = ident

        if type(obj) is numpy.ndarray and len(obj.shape) != 0:
            if len(obj.shape) > 1:
                dtype = dtype2json(numpy.dtype((obj.dtype, obj.shape[1:])))
            else:
                dtype = dtype2json(obj.dtype)

            for minsize, types, contexts, pair in compression:
                if obj.nbytes >= minsize and issubclass(obj.dtype.type, tuple(types)) and any(fnmatch.fnmatchcase(context, p) for p in contexts):
                    compress, decompress = pair
                    sink[name + str(ident)] = compress(obj)

                    return {"id": ident,
                            "gen": ["numpy", "frombuffer"],
                            "args": [{"gen": decompress, "args": [{"read": str(ident)}]},
                                     {"gen": ["awkward.persist", "json2dtype"], "args": [dtype]},
                                     len(obj)]}

            else:
                sink[name + str(ident)] = obj.tostring()
                return {"id": ident,
                        "gen": ["numpy", "frombuffer"],
                        "args": [{"read": str(ident)},
                                 {"gen": ["awkward.persist", "json2dtype"], "args": [dtype]},
                                 len(obj)]}

        elif hasattr(obj, "__awkward_persist__"):
            return obj.__awkward_persist__(ident, fill, sink)

        else:
            raise TypeError("cannot serialize {0} instance (has no __awkward_persist__ method)".format(type(obj)))

    schema = {"awkward": awkward.version.__version__,
              "prefix": name,
              "schema": fill(obj, "")}

    sink[name] = json.dumps(schema).encode("ascii")

def deserialize(source, name="", whitelist=whitelist):
    schema = json.loads(source[name])
    prefix = schema["prefix"]
    seen = {}

    def unfill(schema):
        if isinstance(schema, dict):
            if "gen" in schema and isinstance(schema["gen"], list) and len(schema["gen"]) > 0:
                for white in whitelist:
                    for n, p in zip(schema["gen"], white):
                        if not fnmatch.fnmatchcase(n, p):
                            break
                    else:
                        gen, genname = importlib.import_module(schema["gen"][0]), schema["gen"][1:]
                        while len(genname) > 0:
                            gen, genname = getattr(gen, genname[0]), genname[1:]
                        break
                else:
                    raise RuntimeError("callable {0} not in whitelist: {1}".format(schema["gen"], whitelist))

                args = [unfill(x) for x in schema.get("args", [])]

                out = gen(*args)
                if "id" in schema:
                    seen[schema["id"]] = out
                return out
                
            elif "read" in schema:
                if schema.get("absolute", False):
                    return source[schema["read"]]
                else:
                    return source[prefix + schema["read"]]
                
            elif "ref" in schema:
                return seen[schema["ref"]]

            else:
                return schema

        else:
            return schema

    return unfill(schema["schema"])
