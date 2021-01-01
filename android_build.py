import getpass
import os
import shutil
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
    ('aarch64-linux-android', 'aarch64-linux-android', 'arm64-v8a', 16),
    ('arm-linux-androideabi', 'arm-linux-androideabi', 'armeabi-v7a', 16),
    ('x86_64-linux-android', 'x86_64', 'x86_64', 21),
    ('i686-linux-android', 'x86', 'x86', 21)
]

installed_rust_targets = subprocess.run(['rustup', 'target', 'list', '--installed'], capture_output=True, encoding='utf-8').stdout.splitlines()
missing_rust_targets = ''
for target in map(lambda x:x[0], target_list):
    if target not in installed_rust_targets:
        if missing_rust_targets != '':
            missing_rust_targets += ' '
        missing_rust_targets += target
        

if missing_rust_targets != '':
    print('ERROR: One or more android rust targets are missing. Please install them with `rustup target add ' + missing_rust_targets + '`')
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
    rustflags = '-C link-arg=-L' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / (target[1] + '-4.9') / 'prebuilt').glob('*')) / 'lib' / 'gcc' / target[0] / '4.9.x')
    # Prefer SDK version 16, but fall back to 21 for platforms where 16 isn't available.
    # Version 21 is only in use for x86 platforms, and the only reason we need x86 platforms is so this can work inside an emulator.
    rustflags += ' -C link-arg=-L' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / 'llvm' / 'prebuilt').glob('*')) / 'sysroot' / 'usr' / 'lib' / target[0] / '16')
    rustflags += ' -C link-arg=-L' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / 'llvm' / 'prebuilt').glob('*')) / 'sysroot' / 'usr' / 'lib' / target[0] / '21')
    rustflags += ' -C link-arg=-L' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / 'llvm' / 'prebuilt').glob('*')) / 'sysroot' / 'usr' / 'lib' / target[0])
    rustflags += ' -C linker=' + str(next((android_sdk_dir / 'ndk' / ndk_version / 'toolchains' / (target[1] + '-4.9') / 'prebuilt').glob('*')) / 'bin' / (target[0] + '-ld'))
    os.environ['RUSTFLAGS'] = rustflags
    if subprocess.run(['cargo', 'build', '--release', '--target', target[0]]).returncode != 0:
        sys.exit(1)

print('All builds successful, preparing android package now.')
try:
    package_path = Path('prefab') / 'modules' / 'hero_workshop_core'
    (package_path / 'include').mkdir(parents=True)
    (package_path / 'prefab.json').write_text('{ "schema_version": 1, "name": "hero_workshop_core, "dependencies": [] }')
    ndk_major_version = ndk_version[0:ndk_version.find('.')]
    for target in target_list:
        target_path = (package_path / 'libs' / ('android.' + target[2]))
        target_path.mkdir(parents=True)
        shutil.copy(Path('target') / target[0] / 'release' / 'libhero_workshop_core.so', target_path)
        (target_path / 'include').mkdir()
        for header_path in (Path('target') / target[0] / 'cxxbridge').glob('**/*.h'):
            dest_path = Path(str(target_path / 'include') + str(header_path)[len(str(Path('target') / target[0] / 'cxxbridge')):])
            dest_path.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(header_path, dest_path)
        (target_path / 'abi.json').write_text('{{ "abi": "{abi}", "api": {api}, "ndk": {ndk}, "stl": "c++_shared" }}'.format(abi = target[2], api = target[3], ndk = ndk_major_version))
    with zipfile.ZipFile('hero_workshop_core.aar', mode='w') as zipref:
        zipref.write('AndroidManifest.xml')
        for path in Path('prefab').glob('**/*'):
            zipref.write(path)
except Exception as e:
    print('Error making package:', e)
else:
    print('Package ready!')
finally:
    shutil.rmtree('prefab')