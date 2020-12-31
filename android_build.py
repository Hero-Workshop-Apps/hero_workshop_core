import getpass
import os
import sys
import subprocess
import urllib.request
import zipfile

from pathlib import Path

ndk_version = '21.3.6528147'

# Pairs, the first representing the llvm target triple, and the second being the name of the folder where Google decided to put the toolchain
# because when has being consistent ever been a good thing?
target_list = [
    ('aarch64-linux-android', 'aarch64-linux-android'),
    ('arm-linux-androideabi', 'arm-linux-androideabi'),
    ('x86_64-linux-android', 'x86_64'),
    ('i686-linux-android', 'x86')
]

installed_rust_targets = subprocess.run(['rustup', 'target', 'list', '--installed'], capture_output=True, encoding='utf-8').stdout.splitlines()
missing_rust_targets = ''
for target in map(lambda x:x[0], target_list):
    if target not in installed_rust_targets:
        if missing_rust_targets != '':
            missing_rust_targets += ' '
        missing_rust_targets += target
        

if missing_rust_targets != '':
    print('One or more android rust targets are missing. Please install them with "rustup target add ' + missing_rust_targets + '"')
    exit()

gradlew = './gradlew'
if 'ANDROID_HOME' in os.environ:
    android_sdk_dir = os.environ['ANDROID_HOME']
else:
    if sys.platform == 'win32':
        android_sdk_dir = 'C:\\Users\\' + getpass.getuser() + '\\AppData\\Local\\Android\\Sdk\\'
        gradlew = '.\gradlew.bat'
    elif sys.platform == 'darwin':
        android_sdk_dir = '/Users/' + getpass.getuser() + '/Library/Android/sdk/'
    else:
        print("I don't know where to find the Android SDK. Please set the ANDROID_HOME environment variable to the location of the SDK.")
        exit()
android_sdk_dir = Path(android_sdk_dir)
if not android_sdk_dir.exists():
    print("Android SDK doesn't exist at " + str(android_sdk_dir))
    print("You need to either set the ANDROID_HOME environment variable, or install the SDK at the aforementioned path.")
    exit()
if not (android_sdk_dir / 'ndk' / ndk_version).exists():
    print("Android NDK version " + ndk_version + "not found. You need to install " + ndk_version + " from Android Studio.")
    exit()
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
        exit()

# Everything is built and generated, let's package it for android using Google's Prefab tool.

print('All builds successful, now downloading and building Google Prefab.')

# Google's Prefab tool must use JDK 1.8. I don't make the rules.
if '1.8.0' not in subprocess.run(['javac', '-version'], capture_output=True, encoding='utf-8').stdout:
    if sys.platform == 'win32':
        os.environ['JAVA_HOME'] = str(next(Path('C:\\Program Files\\Java\\').glob('jdk1.8.0_*')))
    else:
        print("**** WARNING: JDK 1.8 required. Javac on path isn't 1.8 and searching for it in a more robust manner isn't implemented on this platform. ****")
        print("**** This might work anyways, so I won't stop you, but I don't expect it to work. ****")

prefab_path = Path('prefab') / 'prefab-1.1.2'
if not prefab_path.exists():
    os.makedirs('prefab')
    zippath = Path('prefab') / 'prefab.zip'
    urllib.request.urlretrieve('https://github.com/google/prefab/archive/v1.1.2.zip', zippath)
    with zipfile.ZipFile(zippath, 'r') as zip_ref:
        zip_ref.extractall('prefab')
    os.remove(zippath)

if subprocess.run([gradlew, 'installDist'], cwd=prefab_path, shell=True).returncode != 0:
    print('Running prefab build failed.')
    exit()
if sys.platform == 'win32':
    prefab = 'prefab.bat'
else :
    prefab = 'prefab'
subprocess.run([prefab_path / 'cli' / 'build' / 'install' / 'prefab' / 'bin' / 'prefab' / prefab], shell=True)