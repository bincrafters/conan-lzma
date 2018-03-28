#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, AutoToolsBuildEnvironment
import os


class LZMAConan(ConanFile):
    name = "lzma"
    version = "5.2.3"
    description = "LZMA library is part of XZ Utils (a free general-purpose data compression software.)"
    url = "https://github.com/bincrafters/conan-lzma"
    license = "Public Domain"
    exports = ["LICENSE.md"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = "shared=False", "fPIC=True"
    url = "https://github.com/bincrafters/conan-lzma"
    description = "LZMA library is part of XZ Utils. """ \
                  "XZ Utils is free general-purpose data compression software with a high compression ratio"
    license = "https://git.tukaani.org/?p=xz.git;a=blob;f=COPYING;hb=HEAD"
    root = "xz-" + version

    @property
    def is_mingw(self):
        return self.settings.compiler == 'gcc' and self.settings.os == 'Windows'

    def build_requirements(self):
        if self.is_mingw:
            self.build_requires('msys2_installer/latest@bincrafters/stable')
            self.build_requires('mingw_installer/1.0@conan/stable')

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
        with tools.chdir(os.path.join(self.root, 'windows')):
            target = 'liblzma_dll' if self.options.shared else 'liblzma'
            if str(self.settings.compiler.runtime).startswith('MT'):
                tools.replace_in_file('%s.vcxproj' % target,
                                      '<RuntimeLibrary>MultiThreadedDebugDLL</RuntimeLibrary>',
                                      '<RuntimeLibrary>MultiThreadedDebug</RuntimeLibrary>')
                tools.replace_in_file('%s.vcxproj' % target,
                                      '<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>',
                                      '<RuntimeLibrary>MultiThreaded</RuntimeLibrary>')
            command = tools.msvc_build_command(self.settings, 'xz_win.sln', targets=[target], upgrade_project=False)
            if self.settings.arch == 'x86':
                command = command.replace('/p:Platform="x86"', '/p:Platform="Win32"')
            self.run(command)

    def build_configure(self):
        prefix = os.path.abspath(self.package_folder)
        if self.is_mingw:
            prefix = tools.unix_path(prefix, tools.MSYS2)
        with tools.chdir(self.root):
            env_build = AutoToolsBuildEnvironment(self, win_bash=self.is_mingw)
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
        elif self.is_mingw:
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

    def package_info(self):
        if not self.options.shared:
            self.cpp_info.defines.append('LZMA_API_STATIC')
        self.cpp_info.libs = tools.collect_libs(self)
