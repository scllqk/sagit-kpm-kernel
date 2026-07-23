#!/usr/bin/env python3
"""Fix SukiSU-Ultra code for kernel 4.4 arm64 compatibility."""
import os

KERNEL_DIR = os.path.join(os.path.dirname(__file__) or '.')
SUKI_DIR = os.path.join(KERNEL_DIR, 'SukiSU-Ultra', 'kernel')

def fix_arch_h():
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
    if old in c:
        c = c.replace(old, new)
        with open(path, 'w') as f:
            f.write(c)
        print('arch.h: OK')
    else:
        print('arch.h: already patched, skipped')

def fix_kp_hook():
    path = os.path.join(SUKI_DIR, 'kp_hook.c')
    with open(path) as f:
        c = f.read()
    # Fix NULL -> 0 for unsigned int cmd
    c = c.replace(
        'ksu_handle_sys_reboot(magic1, magic2, NULL, arg)',
        'ksu_handle_sys_reboot(magic1, magic2, 0, arg)'
    )
    # Remove PT_REAL_REGS from reboot_handler_pre (arm64 4.4 bug)
    old_reboot = (
        '\tstruct pt_regs *real_regs = PT_REAL_REGS(regs);\n'
        '\tint magic1 = (int)PT_REGS_PARM1(real_regs);\n'
        '\tint magic2 = (int)PT_REGS_PARM2(real_regs);\n'
        '\tvoid __user **arg = (void __user **)&PT_REGS_SYSCALL_PARM4(real_regs);\n'
    )
    new_reboot = (
        '\tint magic1 = (int)PT_REGS_PARM1(regs);\n'
        '\tint magic2 = (int)PT_REGS_PARM2(regs);\n'
        '\tvoid __user **arg = (void __user **)&PT_REGS_SYSCALL_PARM4(regs);\n'
    )
    if old_reboot in c:
        c = c.replace(old_reboot, new_reboot)
        print('kp_hook.c: removed PT_REAL_REGS')
    # Guard kp_handle_ksud_init when SUSFS
    c = c.replace(
        'void kp_handle_ksud_init(void)\n{\n\tint ret;',
        'void kp_handle_ksud_init(void)\n{\n#ifndef CONFIG_KSU_SUSFS\n\tint ret;'
    )
    c = c.replace(
        '\tINIT_WORK(&stop_input_hook_work, do_stop_input_hook);\n}\n\nvoid kp_handle_ksud_exit(void)',
        '\tINIT_WORK(&stop_input_hook_work, do_stop_input_hook);\n#endif\n}\n\nvoid kp_handle_ksud_exit(void)'
    )
    c = c.replace(
        'void kp_handle_ksud_exit(void)\n{\n\tunregister_kprobe(&execve_kp);',
        'void kp_handle_ksud_exit(void)\n{\n#ifndef CONFIG_KSU_SUSFS\n\tunregister_kprobe(&execve_kp);'
    )
    c = c.replace(
        '\tunregister_kprobe(&input_event_kp);\n}',
        '\tunregister_kprobe(&input_event_kp);\n#endif\n}'
    )
    c = c.replace(
        'schedule_work(&stop_init_rc_hook_work)',
        'schedule_work(&stop_vfs_read_work)'
    )
    with open(path, 'w') as f:
        f.write(c)
    print('kp_hook.c: OK')

def fix_kp_util():
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

def create_stubs():
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
    kbuild_path = os.path.join(SUKI_DIR, 'Kbuild')
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
fix_kp_hook()
fix_kp_util()
create_stubs()
fix_kbuild()
print('All fixes applied.')
