#!/usr/bin/env python3
"""Fix SukiSU-Ultra v4.1.0 code for kernel 4.4 arm64 compatibility.
   Files that exist in v4.1.0 (kp_hook.c/kp_util.c don't exist here)."""
import os

# Repo root (where this script lives)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# SukiSU kernel sources are at kernel/SukiSU-Ultra/kernel/
SUKI_DIR = os.path.join(BASE_DIR, 'kernel', 'SukiSU-Ultra', 'kernel')
# Symlink target for drivers/kernelsu
KSU_DIR = os.path.join(BASE_DIR, 'kernel', 'drivers', 'kernelsu')

print(f"BASE_DIR: {BASE_DIR}")
print(f"SUKI_DIR: {SUKI_DIR}")


def fix_arch_h():
    """Fix syscall symbol names for kernel 4.4 (no __arm64_ prefix)."""
    path = os.path.join(SUKI_DIR, 'arch.h')
    if not os.path.exists(path):
        print('arch.h: NOT FOUND, skipped')
        return
    with open(path) as f:
        c = f.read()
    old = '#define REBOOT_SYMBOL "__arm64_sys_reboot"'
    new = (
        '#if LINUX_VERSION_CODE >= KERNEL_VERSION(4, 19, 0)\n'
        '#define REBOOT_SYMBOL "__arm64_sys_reboot"\n'
        '#define SYS_READ_SYMBOL "__arm64_sys_read"\n'
        '#define SYS_EXECVE_SYMBOL "__arm64_sys_execve"\n'
        '#define SYS_FSTAT_SYMBOL "__arm64_sys_newfstat"\n'
        '#else\n'
        '#define REBOOT_SYMBOL "sys_reboot"\n'
        '#define SYS_READ_SYMBOL "sys_read"\n'
        '#define SYS_EXECVE_SYMBOL "sys_execve"\n'
        '#define SYS_FSTAT_SYMBOL "sys_newfstat"\n'
        '#endif\n'
    )
    if old in c:
        c = c.replace(old, new)
        with open(path, 'w') as f:
            f.write(c)
        print('arch.h: OK')
    else:
        print('arch.h: already patched, skipped')


def create_stubs():
    """Create stubs for symbols only needed when SUSFS is disabled."""
    stub_path = os.path.join(SUKI_DIR, 'ksu_stubs_44.c')
    stub_content = (
        '/* Kernel 4.4 stubs - provides symbols excluded when CONFIG_KSU_SUSFS=y */\n'
        '#include <linux/types.h>\n'
        '#include <linux/cred.h>\n'
        '#include <linux/dcache.h>\n\n'
        '#ifndef CONFIG_KSU_SUSFS\n'
        '/* Already defined in other files */\n'
        '#else\n'
        'int ksu_handle_execve_sucompat(int *fd, const char __user **filename_user,\n'
        '                               void *a, void *b, int *c) { return 0; }\n'
        'int ksu_handle_setuid_common(uid_t nu, uid_t ou, uid_t ne) { return 0; }\n'
        '#endif\n'
    )
    with open(stub_path, 'w') as f:
        f.write(stub_content)
    print('ksu_stubs_44.c: created')


def fix_kbuild():
    """Add ksu_stubs_44.o to build."""
    kbuild_path = os.path.join(SUKI_DIR, 'Kbuild')
    if not os.path.exists(kbuild_path):
        print('Kbuild: NOT FOUND, skipped')
        return
    with open(kbuild_path) as f:
        c = f.read()
    if 'ksu_stubs_44' not in c:
        c = c.replace(
            'kernelsu-objs := $(ksu_obj-y)',
            'ksu_obj-y += ksu_stubs_44.o\nkernelsu-objs := $(ksu_obj-y)'
        )
        with open(kbuild_path, 'w') as f:
            f.write(c)
        print('Kbuild: added ksu_stubs_44.o')
    else:
        print('Kbuild: already has ksu_stubs_44.o')


fix_arch_h()
create_stubs()
fix_kbuild()
print('All fixes applied.')
