import getpass
import os
import subprocess
import sys
import urllib.request
import zipfile

from pathlib import Path

ndk_version = '21.3.6528147'

# Tuples, the first representing the llvm target triple, the second being the name of the folder where Google decided to put the toolchain,
# the third being the abi identifier used in Android package archives, and the fourth being the Android API version in use for that architecture.
# because when has being consistent ever been a good thing?
target_list = [
    ('aarch64-linux-android', 'aarch64-linux-android', 'arm64-v8a', 21),
    ('arm-linux-androideabi', 'arm-linux-androideabi', 'armeabi-v7a', 16),
    ('x86_64-linux-android', 'x86_64', 'x86_64', 21),
    ('i686-linux-android', 'x86', 'x86', 16)
]

installed_rust_targets = subprocess.run(['rustup', 'target', 'list', '--installed'], capture_output=True, encoding='utf-8').stdout.splitlines()
missing_rust_targets = []
for target in map(lambda x:x[0], target_list):
    if target not in installed_rust_targets:
        missing_rust_targets.append(target)
        

if len(missing_rust_targets) > 0:
    print('ERROR: One or more android rust targets are missing. Please install them with `rustup target add ' + ' '.join(missing_rust_targets) + '`')
    sys.exit(1)

gradlew = './gradlew'
if 'ANDROID_HOME' in os.environ:
    android_sdk_dir = os.environ['ANDROID_HOME']
else:
    if sys.platform == 'win32':
        android_sdk_dir = 'C:\\Users\\' + getpass.getuser() + '\\AppData\\Local\\Android\\Sdk\\'
        gradlew = '.\\gradlew.bat'
    elif sys.platform == 'darwin':
        android_sdk_dir = '/Users/' + getpass.getuser() + '/Library/Android/sdk/'
    else:
        print("ERROR: I don't know where to find the Android SDK. Please set the ANDROID_HOME environment variable to the location of the SDK.")
        sys.exit(1)
android_sdk_dir = Path(android_sdk_dir)
if not android_sdk_dir.exists():
    print("ERROR: Android SDK doesn't exist at " + str(android_sdk_dir))
    print("You need to either set the ANDROID_HOME environment variable, or install the SDK at the aforementioned path.")
    sys.exit(1)
if not (android_sdk_dir / 'ndk' / ndk_version).exists():
    print("ERROR: Android NDK version " + ndk_version + "not found. You need to install " + ndk_version + " from Android Studio.")
    sys.exit(1)
base_flags = '-I ' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / 'llvm' / 'prebuilt').glob('*')) / 'sysroot' / 'usr' / 'include' / 'c++' / 'v1')
base_flags += ' -I ' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / 'llvm' / 'prebuilt').glob('*')) / 'sysroot' / 'usr' / 'include')
base_path = os.environ['PATH']
for target in target_list:
    print('*** Now building for ' + target[0] + ' ***')
    flags = base_flags + ' -I ' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / 'llvm' / 'prebuilt').glob('*')) / 'sysroot' / 'usr' / 'include' / target[0])
    os.environ['CFLAGS'] = flags
    os.environ['CXXFLAGS'] = flags
    os.environ['PATH'] = base_path + ';' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / (target[1] + '-4.9') / 'prebuilt').glob('*')) / 'bin')
    rustflags = ['-C link-arg=-L' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / (target[1] + '-4.9') / 'prebuilt').glob('*')) / 'lib' / 'gcc' / target[0] / '4.9.x')]
    # Prefer SDK version 16, but fall back to 21 for platforms where 16 isn't available.
    # Version 21 is only in use for 64 bit platforms, which is fine because 21 is the oldest version available on those platforms.
    rustflags.append('-C link-arg=-L' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / 'llvm' / 'prebuilt').glob('*')) / 'sysroot' / 'usr' / 'lib' / target[0] / '16'))
    rustflags.append('-C link-arg=-L' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / 'llvm' / 'prebuilt').glob('*')) / 'sysroot' / 'usr' / 'lib' / target[0] / '21'))
    rustflags.append('-C link-arg=-L' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / 'llvm' / 'prebuilt').glob('*')) / 'sysroot' / 'usr' / 'lib' / target[0]))
    rustflags.append('-C linker=' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / (target[1] + '-4.9') / 'prebuilt').glob('*')) / 'bin' / (target[0] + '-ld')))
    os.environ['RUSTFLAGS'] = ' '.join(rustflags)
    if subprocess.run(['cargo', 'build', '--release', '--target', target[0]]).returncode != 0:
        sys.exit(1)

print('All builds successful, preparing android package now.')
ndk_major_version = ndk_version[0:ndk_version.find('.')]
with zipfile.ZipFile('hero_workshop_core.aar', mode='w', strict_timestamps=False) as zipref:
    package_path = 'prefab/modules/hero_workshop_core'
    zipref.write('AndroidManifest.xml')
    zipref.writestr('prefab/prefab.json', '{ "schema_version": 1, "name": "hero_workshop_core", "dependencies": [] }')
    zipref.writestr(package_path + '/module.json', '{ "export_libraries": [], "android": {} }')
    for target in target_list:
        target_path = package_path + '/libs/android.' + target[2]
        zipref.writestr(target_path + '/abi.json', '{{ "abi": "{abi}", "api": 16, "ndk": {ndk}, "stl": "c++_static" }}'.format(abi = target[2], ndk = ndk_major_version))
        zipref.write(Path('target') / target[0] / 'release' / 'libhero_workshop_core.a', target_path + '/libhero_workshop_core.a')
        headers_path = Path('target') / target[0] / 'cxxbridge'
        for header_path in headers_path.glob('**/*.h'):
            dest_path = target_path + '/include' + str(header_path)[len(str(headers_path)):].replace('\\', '/')
            zipref.write(header_path, dest_path)
print('Package ready!')