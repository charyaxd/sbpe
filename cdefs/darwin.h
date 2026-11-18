// macOS-only helpers implemented in cdefs/remote.c
intptr_t sbpe_exe_slide(void);
uint64_t sbpe_find_symbol(const char *prefix, int *nmatches);
void sbpe_install_crash_handler(int fd);
