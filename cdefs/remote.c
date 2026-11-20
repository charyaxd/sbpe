// paths are relative to the build dir

#ifdef __APPLE__
#include "../cdefs/internals_libcxx.h"
#include "../cdefs/generated_darwin.h" // needed to define enum values
#else
#include "../cdefs/internals.h"
#include "../cdefs/generated.h" // needed to define enum values
#endif
#include "../cdefs/XDL.h"

// defined later by cffi (embedding_api)
uint32_t kickstart();

#include "../libs/subhook/subhook.h"
#include "../libs/plthook/plthook.h"

#if defined(MS_WIN32)
	#include "../libs/SDL/include/SDL.h"
#elif defined(__APPLE__)
	// SDL is resolved at load time from the game's own libSDL2
	// (linked with -undefined dynamic_lookup), so only declare what we use.
	#include "../cdefs/SDL.h"
#else
	#include <SDL2/SDL.h>
#endif

#if defined(__APPLE__)

#include <string.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <mach-o/nlist.h>

// ---------------------------------------------------------------------------
// symbol lookup in the main executable's in-memory symbol table.
// The game binary is not stripped, so local (static) symbols are available.

static const struct mach_header_64 *exe_header = NULL;
static intptr_t exe_slide = 0;

static void find_executable(void) {
	uint32_t i, n = _dyld_image_count();
	for (i = 0; i < n; i++) {
		const struct mach_header *h = _dyld_get_image_header(i);
		if (h && h->filetype == MH_EXECUTE && h->magic == MH_MAGIC_64) {
			exe_header = (const struct mach_header_64 *)h;
			exe_slide = _dyld_get_image_vmaddr_slide(i);
			return;
		}
	}
}

intptr_t sbpe_exe_slide(void) {
	if (!exe_header) find_executable();
	return exe_slide;
}

// Find a defined symbol whose name (without the leading underscore) starts
// with `prefix`. Returns its runtime address (slide applied) or 0. The
// number of distinct addresses that matched is stored in *nmatches.
uint64_t sbpe_find_symbol(const char *prefix, int *nmatches) {
	const struct load_command *lc;
	const struct symtab_command *symtab = NULL;
	const struct segment_command_64 *linkedit = NULL;
	uint32_t i;
	uint64_t found = 0;
	int count = 0;
	size_t plen = strlen(prefix);

	if (!exe_header) find_executable();
	*nmatches = 0;
	if (!exe_header) return 0;

	lc = (const struct load_command *)(exe_header + 1);
	for (i = 0; i < exe_header->ncmds; i++) {
		if (lc->cmd == LC_SYMTAB) {
			symtab = (const struct symtab_command *)lc;
		} else if (lc->cmd == LC_SEGMENT_64) {
			const struct segment_command_64 *seg = (const void *)lc;
			if (strcmp(seg->segname, SEG_LINKEDIT) == 0) linkedit = seg;
		}
		lc = (const void *)((const char *)lc + lc->cmdsize);
	}
	if (!symtab || !linkedit) return 0;

	{
		const char *base = (const char *)(exe_slide + linkedit->vmaddr - linkedit->fileoff);
		const struct nlist_64 *syms = (const void *)(base + symtab->symoff);
		const char *strs = base + symtab->stroff;

		for (i = 0; i < symtab->nsyms; i++) {
			const struct nlist_64 *s = &syms[i];
			const char *name;
			uint64_t addr;
			if (s->n_type & N_STAB) continue;
			if ((s->n_type & N_TYPE) != N_SECT) continue;
			if (s->n_un.n_strx == 0) continue;
			name = strs + s->n_un.n_strx;
			if (name[0] == '_') name++;
			if (strncmp(name, prefix, plen) != 0) continue;
			addr = s->n_value + exe_slide;
			if (count == 0 || addr != found) {
				if (count == 0) found = addr;
				count++;
			}
		}
	}
	*nmatches = count;
	return found;
}

// ---------------------------------------------------------------------------
// native backtrace on fatal signals, chained before python's faulthandler

#include <execinfo.h>
#include <signal.h>
#include <unistd.h>

static int crash_fd = -1;
static struct sigaction prev_segv, prev_bus, prev_ill;

static void crash_handler(int sig, siginfo_t *info, void *ctx) {
	void *frames[64];
	int n = backtrace(frames, 64);
	char buf[64];
	int len;
	struct sigaction *prev = sig == SIGSEGV ? &prev_segv : sig == SIGBUS ? &prev_bus : &prev_ill;

	len = snprintf(buf, sizeof(buf), "native signal %d at %p, slide %p\n",
		sig, info ? info->si_addr : NULL, (void *)exe_slide);
	write(crash_fd, buf, len);
	backtrace_symbols_fd(frames, n, crash_fd);
	write(crash_fd, "\n", 1);

	if (prev->sa_flags & SA_SIGINFO) {
		if (prev->sa_sigaction) { prev->sa_sigaction(sig, info, ctx); return; }
	} else if (prev->sa_handler != SIG_DFL && prev->sa_handler != SIG_IGN) {
		prev->sa_handler(sig); return;
	}
	signal(sig, SIG_DFL);
	raise(sig);
}

void sbpe_install_crash_handler(int fd) {
	struct sigaction sa;
	crash_fd = fd;
	memset(&sa, 0, sizeof(sa));
	sa.sa_sigaction = crash_handler;
	sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
	sigemptyset(&sa.sa_mask);
	sigaction(SIGSEGV, &sa, &prev_segv);
	sigaction(SIGBUS, &sa, &prev_bus);
	sigaction(SIGILL, &sa, &prev_ill);
}

// ---------------------------------------------------------------------------
// entry point: interpose SDL_Init (dyld __interpose works with the default
// two-level namespace, no DYLD_FORCE_FLAT_NAMESPACE needed)

static int sbpe_started = 0;

static int sbpe_SDL_Init(uint32_t flags) {
	if (!sbpe_started) {
		sbpe_started = 1;
		kickstart();
	}
	return SDL_Init(flags);
}

__attribute__((used)) static struct { const void *replacement; const void *original; }
_sbpe_interpose[] __attribute__((section("__DATA,__interpose"))) = {
	{ (const void *)(unsigned long)&sbpe_SDL_Init, (const void *)(unsigned long)&SDL_Init },
};

#elif !defined(MS_WIN32)

#include <dlfcn.h>

CFFI_DLLEXPORT int SDL_Init(uint32_t flags) {
	kickstart();
	return ((int(*)(uint32_t))dlsym(RTLD_NEXT, "SDL_Init"))(flags);
}

#endif
