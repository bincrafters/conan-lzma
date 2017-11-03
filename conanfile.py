#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools
import os


class LZMAConan(ConanFile):
    name = "lzma"
    version = "5.2.3"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = "shared=False"
    url = "https://github.com/SSE4/conan-lzma"
    description = "XZ Utils is free general-purpose data compression software with a high compression ratio"
    license = "https://git.tukaani.org/?p=xz.git;a=blob;f=COPYING;hb=HEAD"
    root = "xz-" + version
    #use static org/channel for libs in conan-center
    #use dynamic org/channel for libs in bincrafters
    #requires = "OpenSSL/1.0.2l@conan/stable", \
    #    "zlib/1.2.11@conan/stable", \
    #    "websocketpp/0.7.0@%s/%s" % (self.user, self.channel)

    def configure(self):
        del self.settings.compiler.libcxx

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
            command = tools.msvc_build_command(self.settings, 'xz_win.sln', targets=[target], upgrade_project=True)
            if self.settings.arch == 'x86':
                command = command.replace('/p:Platform="x86"', '/p:Platform="Win32"')
            self.run(command)

    def build_configure(self):
        with tools.chdir(self.root):
            raise Exception("not implemented")

    def build(self):
        if self.settings.compiler == 'Visual Studio':
            self.build_msvc()
        else:
            self.build_configure()

    def package(self):
        inc_dir = os.path.join(self.root, 'src', 'liblzma', 'api')
        self.copy(pattern="*.h", dst="include", src=inc_dir, keep_path=True)
        if self.settings.os == "Windows":
            arch = {'x86': 'Win32', 'x86_64': 'x64'}.get(str(self.settings.arch))
            target = 'liblzma_dll' if self.options.shared else 'liblzma'
            bin_dir = os.path.join(self.root, 'windows', str(self.settings.build_type), arch, target)
            self.copy(pattern="*.lib", dst="lib", src=bin_dir, keep_path=False)
            if self.options.shared:
                self.copy(pattern="*.dll", dst="bin", src=bin_dir, keep_path=False)
        #self.copy(pattern="*.dll", dst="bin", src="bin", keep_path=False)
        #self.copy(pattern="*.lib", dst="lib", src="lib", keep_path=False)
        #self.copy(pattern="*.a", dst="lib", src="lib", keep_path=False)
        #self.copy(pattern="*.so*", dst="lib", src="lib", keep_path=False)
        #self.copy(pattern="*.dylib", dst="lib", src="lib", keep_path=False)

    def package_info(self):
        if not self.options.shared:
            self.cpp_info.defines.append('LZMA_API_STATIC')
        self.cpp_info.libs = tools.collect_libs(self)
