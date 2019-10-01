# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack import *


class PySymengine(PythonPackage):
    """Python wrappers for SymEngine, a symbolic manipulation library."""

    homepage = "https://github.com/symengine/symengine.py"
    url      = "https://github.com/symengine/symengine.py/archive/v0.2.0.tar.gz"
    git      = "https://github.com/symengine/symengine.py.git"

    version('develop',   branch='master')
    version('0.3.0',     sha256='0ecccfe5a09b25b6640afca12de62062bdb60ed2712d6c16cc47fc1ba1e851ac')

    # Build dependencies
    depends_on('python@2.7:2.8,3.3:')
    depends_on('py-setuptools',     type='build')
    depends_on('py-cython@0.19.1:', type='build')
    depends_on('cmake@2.8.7:',      type='build')
    depends_on('symengine@0.3.0:')

    def build_args(self, spec, prefix):
        return ['build_ext', '--symengine-dir={0}'.format(spec['symengine'].prefix)]
