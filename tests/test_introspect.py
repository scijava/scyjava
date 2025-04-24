"""
Tests for functions in _introspect submodule.
Created on Fri Mar 28 13:58:54 2025

@author: ian-coccimiglio
"""

import scyjava
from scyjava.config import Mode, mode

scyjava.config.endpoints.append("net.imagej:imagej")
scyjava.config.endpoints.append("net.imagej:imagej-legacy:MANAGED")


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
        assert len(str_Obj) == 0
        assert len(bitset_Obj) == 0
        assert bitset_Obj is not None
        assert bitset_Obj == str_Obj

    def test_find_source(self):
        if mode == Mode.JEP:
            # JEP does not support the jclass function.
            return
        str_SF = "org.scijava.search.SourceFinder"
        SF = scyjava.jimport(str_SF)
        source_strSF = scyjava.java_source(str_SF)
        source_SF = scyjava.java_source(SF)
        repo_path = "https://github.com/scijava/scijava-search/"
        assert source_strSF.startsWith(repo_path)
        assert source_SF.startsWith(repo_path)
        assert source_strSF == source_SF

    def test_imagej_legacy(self):
        if mode == Mode.JEP:
            # JEP does not support the jclass function.
            return
        str_RE = "ij.plugin.RoiEnlarger"
        table = scyjava.jreflect(str_RE, aspect="methods")
        assert len([entry for entry in table if entry["static"]]) == 3
        repo_path = "https://github.com/imagej/ImageJ/"
        assert scyjava.java_source(str_RE).startsWith(repo_path)
