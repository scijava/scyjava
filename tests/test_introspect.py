"""
Tests for functions in _introspect submodule.
Created on Fri Mar 28 13:58:54 2025

@author: ian-coccimiglio
"""

import scyjava
from scyjava.config import Mode, mode

scyjava.config.endpoints.extend(
    ["net.imagej:imagej", "net.imagej:imagej-legacy:MANAGED"]
)


class TestIntrospection(object):
    """
    Test introspection functionality.
    """

    def test_jreflect_methods(self):
        if mode == Mode.JEP:
            # JEP does not support the jclass function.
            return
        str_String = "java.lang.String"
        String = scyjava.jimport(str_String)
        str_Obj = scyjava.jreflect(str_String, "methods")
        jimport_Obj = scyjava.jreflect(String, "methods")
        assert len(str_Obj) > 0
        assert len(jimport_Obj) > 0
        assert jimport_Obj is not None
        assert jimport_Obj == str_Obj

    def test_jreflect_fields(self):
        if mode == Mode.JEP:
            # JEP does not support the jclass function.
            return
        str_BitSet = "java.util.BitSet"
        BitSet = scyjava.jimport(str_BitSet)
        str_Obj = scyjava.jreflect(str_BitSet, "fields")
        bitset_Obj = scyjava.jreflect(BitSet, "fields")
        assert len(str_Obj) == len(bitset_Obj) == 0
        assert bitset_Obj is not None
        assert bitset_Obj == str_Obj

    def test_jreflect_ctors(self):
        if mode == Mode.JEP:
            # JEP does not support the jclass function.
            return
        str_ArrayList = "java.util.ArrayList"
        ArrayList = scyjava.jimport(str_ArrayList)
        str_Obj = scyjava.jreflect(str_ArrayList, "constructors")
        arraylist_Obj = scyjava.jreflect(ArrayList, "constructors")
        assert len(str_Obj) == len(arraylist_Obj) == 3
        arraylist_Obj.sort(
            key=lambda row: f"{row['type']}:{row['name']}:{','.join(str(row['arguments']))}"
        )
        assert arraylist_Obj == [
            {
                "arguments": ["int"],
                "mods": ["public"],
                "name": "java.util.ArrayList",
                "returns": "java.util.ArrayList",
                "type": "constructor",
            },
            {
                "arguments": ["java.util.Collection"],
                "mods": ["public"],
                "name": "java.util.ArrayList",
                "returns": "java.util.ArrayList",
                "type": "constructor",
            },
            {
                "arguments": [],
                "mods": ["public"],
                "name": "java.util.ArrayList",
                "returns": "java.util.ArrayList",
                "type": "constructor",
            },
        ]

    def test_jsource(self):
        if mode == Mode.JEP:
            # JEP does not support the jclass function.
            return
        str_SF = "org.scijava.search.SourceFinder"
        SF = scyjava.jimport(str_SF)
        source_strSF = scyjava.jsource(str_SF)
        source_SF = scyjava.jsource(SF)
        repo_path = "https://github.com/scijava/scijava-search/"
        assert source_strSF.startsWith(repo_path)
        assert source_SF.startsWith(repo_path)
        assert source_strSF == source_SF

    def test_jsource_jdk_class(self):
        if mode == Mode.JEP:
            # JEP does not support the jclass function.
            return
        jv_digits = scyjava.jvm_version()
        jv = jv_digits[1] if jv_digits[0] == 1 else jv_digits[0]
        source = scyjava.jsource("java.util.List")
        assert source.startswith("https://github.com/openjdk/jdk/blob/")
        assert source.endswith("/share/classes/java/util/List.java")
        assert str(jv) in source

    def test_imagej_legacy(self):
        if mode == Mode.JEP:
            # JEP does not support the jclass function.
            return
        str_RE = "ij.plugin.RoiEnlarger"
        table = scyjava.jreflect(str_RE, aspect="methods")
        assert sum(1 for entry in table if "static" in entry["mods"]) == 3
        repo_path = "https://github.com/imagej/ImageJ/"
        assert scyjava.jsource(str_RE).startsWith(repo_path)
