#!/usr/bin/env python3
"""Fix SukiSU-Ultra code for kernel 4.4 arm64 compatibility."""
import os, sys

SUKI_DIR = os.path.join(os.path.dirname(__file__) or '.', 'SukiSU-Ultra', 'kernel')

# Fix 1: arch.h - use sys_ prefix for < 4.19
path = os.path.join(SUKI_DIR, 'arch.h')
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
c = c.replace(old, new)
with open(path, 'w') as f:
    f.write(c)
print('arch.h: OK')

# Fix 2: kp_hook.c - NULL -> 0 for unsigned int cmd param
path = os.path.join(SUKI_DIR, 'kp_hook.c')
with open(path) as f:
    c = f.read()
c = c.replace(
    'ksu_handle_sys_reboot(magic1, magic2, NULL, arg)',
    'ksu_handle_sys_reboot(magic1, magic2, 0, arg)'
)
with open(path, 'w') as f:
    f.write(c)
print('kp_hook.c: OK')

# Fix 3: kp_util.c - pgtable.h not available before 5.7
path = os.path.join(SUKI_DIR, 'kp_util.c')
with open(path) as f:
    c = f.read()
c = c.replace(
    '#include <linux/pgtable.h>',
    '#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 7, 0)\n#include <linux/pgtable.h>\n#endif'
)
with open(path, 'w') as f:
    f.write(c)
print('kp_util.c: OK')

print('All patches applied successfully.')
