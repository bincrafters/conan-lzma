#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, AutoToolsBuildEnvironment, MSBuild
import os
import shutil


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
    default_options = "shared=False", "fPIC=True"
    description = "LZMA library is part of XZ Utils"
    root = "xz-" + version

    @property
    def is_mingw_windows(self):
        # Linux MinGW doesn't require MSYS2 bash obviously
        return self.settings.compiler == 'gcc' and self.settings.os == 'Windows' and os.name == 'nt'

    def configure(self):
        del self.settings.compiler.libcxx
        if self.settings.compiler == 'Visual Studio':
            del self.options.fPIC

    def source(self):
        archive_name = "xz-%s.tar.gz" % self.version
        source_url = "https://tukaani.org/xz/%s" % archive_name
        tools.download(source_url, archive_name, verify=True)
        tools.untargz(archive_name)
        os.unlink(archive_name)

    def build_msvc(self):
        # windows\INSTALL-MSVC.txt
        version_dir = 'vs2017' if self.settings.compiler.version >= 15 else 'vs2013'
        with tools.chdir(os.path.join(self.root, 'windows', version_dir)):
            target = 'liblzma_dll' if self.options.shared else 'liblzma'

            msbuild = MSBuild(self)
            msbuild.build(
                'xz_win.sln',
                targets=[target],
                platforms={"x86":"Win32"},
                upgrade_project=False)

    def build_configure(self):
        prefix = os.path.abspath(self.package_folder)
        if self.is_mingw_windows:
            prefix = tools.unix_path(prefix, tools.MSYS2)
        with tools.chdir(self.root):
            env_build = AutoToolsBuildEnvironment(self, win_bash=self.is_mingw_windows)
            args = ['--disable-xz',
                    '--disable-xzdec',
                    '--disable-lzmadec',
                    '--disable-lzmainfo',
                    '--disable-scripts',
                    '--disable-doc',
                    '--prefix=%s' % prefix]
            if self.options.fPIC:
                args.append('--with-pic')
            if self.options.shared:
                args.extend(['--disable-static', '--enable-shared'])
            else:
                args.extend(['--enable-static', '--disable-shared'])
            if self.settings.build_type == 'Debug':
                args.append('--enable-debug')
            env_build.configure(args=args, build=False)
            env_build.make()
            env_build.make(args=['install'])

    def build(self):
        if self.settings.compiler == 'Visual Studio':
            self.build_msvc()
        elif self.is_mingw_windows:
            msys_bin = self.deps_env_info['msys2_installer'].MSYS_BIN
            with tools.environment_append({'PATH': [msys_bin],
                                           'CONAN_BASH_PATH': os.path.join(msys_bin, 'bash.exe')}):
                self.build_configure()
        else:
            self.build_configure()

    def package(self):
        self.copy(pattern="COPYING", dst="license", src=self.root)
        if self.settings.compiler == "Visual Studio":
            inc_dir = os.path.join(self.root, 'src', 'liblzma', 'api')
            self.copy(pattern="*.h", dst="include", src=inc_dir, keep_path=True)
            arch = {'x86': 'Win32', 'x86_64': 'x64'}.get(str(self.settings.arch))
            target = 'liblzma_dll' if self.options.shared else 'liblzma'
            bin_dir = os.path.join(self.root, 'windows', str(self.settings.build_type), arch, target)
            self.copy(pattern="*.lib", dst="lib", src=bin_dir, keep_path=False)
            if self.options.shared:
                self.copy(pattern="*.dll", dst="bin", src=bin_dir, keep_path=False)
            shutil.move(os.path.join(self.package_folder, 'lib', 'liblzma.lib'),
                        os.path.join(self.package_folder, 'lib', 'lzma.lib'))

    def package_info(self):
        if not self.options.shared:
            self.cpp_info.defines.append('LZMA_API_STATIC')
        self.cpp_info.libs = tools.collect_libs(self)
