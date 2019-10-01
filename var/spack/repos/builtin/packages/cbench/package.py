# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack import *


class Cbench(MakefilePackage):
    """Cbench is intended as a relatively straightforward toolbox of tests,
    benchmarks, applications, utilities, and framework to hold them together
    with the goal to facilitate scalable testing, benchmarking, and analysis
    of a Linux parallel compute cluster."""

    homepage = "https://sourceforge.net/projects/cbench/"
    url      = "https://sourceforge.net/projects/cbench/files/cbench/1.3.0/cbench_release_1.3.0.tar.gz/download"
    list_url = "https://sourceforge.net/projects/cbench/files/cbench/"
    list_depth = 1

    version('1.3.0', '2fb112876fdc96165d14e019b4a26f2e')

    depends_on('mpi')
    depends_on('blas')
    depends_on('lapack')
    depends_on('fftw')

    # The following compilers are not supported by Cbench:
    conflicts('%cce')
    conflicts('%clang')
    conflicts('%nag')
    conflicts('%xl')
    conflicts('%xl_r')

    def setup_environment(self, build_env, run_env):
        # The location of the Cbench source tree
        build_env.set('CBENCHOME', self.stage.source_path)

        # The location that will contain all of your tests and their results
        build_env.set('CBENCHTEST', self.prefix)

        # The location of the system MPI tree
        build_env.set('MPIHOME', self.spec['mpi'].prefix)

        # Pick the compiler collection/chain you want to compile with.
        # Examples include: intel, gcc, pgi.
        build_env.set('COMPILERCOLLECTION', self.compiler.name)

        # Linking flags for BLAS/LAPACK and FFTW
        build_env.set('BLASLIB', self.spec['blas'].libs.ld_flags)
        build_env.set('LAPACKLIB', self.spec['lapack'].libs.ld_flags)
        build_env.set('FFTWLIB', self.spec['fftw'].libs.ld_flags)

        # The number of make jobs (commands) to run simultaneously
        build_env.set('JOBS', str(make_jobs))

    @run_before('build')
    @on_package_attributes(run_tests=True)
    def test_blas_linkage(self):
        """Quick test to ensure that BLAS linkage is working correctly."""

        make('-C', 'opensource/maketests', 'clean')
        make('-C', 'opensource/maketests', 'dummy_blas')
        make('-C', 'opensource/maketests', 'linkstatus')

    def install(self, spec, prefix):
        # Install binaries in $CBENCHOME/bin
        make('install')

        # This creates a testing tree (if one doesn't already exist) and
        # copies the binaries from `$CBENCHOME/bin` to `$CBENCHTEST/bin`.
        # This allows you to use the testing tree independently of the
        # source tree in the future.
        make('installtests')
