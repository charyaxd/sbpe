// macOS-only helpers implemented in cdefs/remote.c
intptr_t sbpe_exe_slide(void);
uint64_t sbpe_find_symbol(const char *prefix, int *nmatches);
void sbpe_install_crash_handler(int fd);

// WorldView methods that create effect graphics (x86_64: `this` is the
// first argument). Hooked on macOS so plugin_noise can tell whose effect
// it is (see remote.py: effect hooks).
typedef void (*pWorldView_handleDamage)(void *view, void *obj, int damage,
    bool b1, bool b2, unsigned int srcWorldId, int x, int y, const char *vid);
typedef void (*pWorldView_handleObjectRemoved)(void *view, void *obj, int reason);
typedef void (*pWorldView_handleTrail)(void *view, void *obj, const char *vid);
