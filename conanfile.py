#!/usr/bin/env python
# -*- coding: utf-8 -*-
from conans import ConanFile, tools, AutoToolsBuildEnvironment, MSBuild
import os


class LZMAConan(ConanFile):
    name = "lzma"
    version = "5.2.4"
    description = "LZMA library is part of XZ Utils (a free general-purpose data compression software.)"
    url = "https://github.com/bincrafters/conan-lzma"
    homepage = "https://tukaani.org"
    license = "Public Domain"
    author = "Bincrafters <bincrafters@gmail.com>"
    exports = ["LICENSE.md"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {'shared': False, 'fPIC': True}
    description = "LZMA library is part of XZ Utils"
    _source_subfolder = 'sources'

    @property
    def _is_mingw_windows(self):
        # Linux MinGW doesn't require MSYS2 bash obviously
        return self.settings.compiler == 'gcc' and self.settings.os == 'Windows' and os.name == 'nt'

    def build_requirements(self):
        if self._is_mingw_windows:
            self.build_requires("msys2_installer/latest@bincrafters/stable")

    def _effective_msbuild_type(self):
        # treat 'RelWithDebInfo' and 'MinSizeRel' as 'Release'
        return 'Debug' if self.settings.build_type == 'Debug' else 'Release'

    def configure(self):
        del self.settings.compiler.libcxx
        if self.settings.compiler == 'Visual Studio':
            del self.options.fPIC

    def source(self):
        archive_name = "xz-%s.tar.gz" % self.version
        source_url = "https://tukaani.org/xz/%s" % archive_name
        tools.get(source_url)
        os.rename('xz-' + self.version, self._source_subfolder)

    def _build_msvc(self):
        # windows\INSTALL-MSVC.txt
        compiler_version = float(self.settings.compiler.version.value)
        msvc_version = 'vs2017' if compiler_version >= 15 else 'vs2013'
        with tools.chdir(os.path.join(self._source_subfolder, 'windows', msvc_version)):
            target = 'liblzma_dll' if self.options.shared else 'liblzma'
            msbuild = MSBuild(self)
            msbuild.build(
                'xz_win.sln',
                targets=[target],
                build_type=self._effective_msbuild_type(),
                platforms={'x86': 'Win32', 'x86_64': 'x64'},
                use_env=False)

    def _build_configure(self):
        with tools.chdir(self._source_subfolder):
            env_build = AutoToolsBuildEnvironment(self, win_bash=self._is_mingw_windows)
            args = ['--disable-xz',
                    '--disable-xzdec',
                    '--disable-lzmadec',
                    '--disable-lzmainfo',
                    '--disable-scripts',
                    '--disable-doc']
            if self.settings.os != "Windows" and self.options.fPIC:
                args.append('--with-pic')
            if self.options.shared:
                args.extend(['--disable-static', '--enable-shared'])
            else:
                args.extend(['--enable-static', '--disable-shared'])
            if self.settings.build_type == 'Debug':
                args.append('--enable-debug')
            env_build.configure(args=args, build=False)
            env_build.make()
            env_build.install()

    def build(self):
        if self.settings.compiler == 'Visual Studio':
            self._build_msvc()
        else:
            self._build_configure()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        if self.settings.compiler == "Visual Studio":
            inc_dir = os.path.join(self._source_subfolder, 'src', 'liblzma', 'api')
            self.copy(pattern="*.h", dst="include", src=inc_dir, keep_path=True)
            arch = {'x86': 'Win32', 'x86_64': 'x64'}.get(str(self.settings.arch))
            target = 'liblzma_dll' if self.options.shared else 'liblzma'
            compiler_version = float(self.settings.compiler.version.value)
            msvc_version = 'vs2017' if compiler_version >= 15 else 'vs2013'
            bin_dir = os.path.join(self._source_subfolder, 'windows', msvc_version,
                                   str(self._effective_msbuild_type()), arch, target)
            self.copy(pattern="*.lib", dst="lib", src=bin_dir, keep_path=False)
            if self.options.shared:
                self.copy(pattern="*.dll", dst="bin", src=bin_dir, keep_path=False)

    def package_info(self):
        if not self.options.shared:
            self.cpp_info.defines.append('LZMA_API_STATIC')
        self.cpp_info.libs = tools.collect_libs(self)
