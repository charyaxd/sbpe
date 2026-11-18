// x86_64 instruction-length tests for the patched subhook decoder
// build: clang -arch x86_64 -w patches/test_subhook_disasm.c -o build/test_subhook_disasm

#define SUBHOOK_STATIC
#include "../libs/subhook/subhook.c"
#include <stdio.h>
struct t { const char *name; unsigned char b[16]; int len; int reloc; };
int main(void) {
  struct t tests[] = {
    {"sub rsp, 0x168",            {0x48,0x81,0xec,0x68,0x01,0,0}, 7, 0},
    {"mov [rbp-0x178], rdx",      {0x48,0x89,0x95,0x88,0xfe,0xff,0xff}, 7, 0},
    {"movb al, [rip+x]",          {0x8a,0x05,0x0a,0xf3,0x16,0x00}, 6, 2},
    {"mov rdi, [rip+x]",          {0x48,0x8b,0x3d,1,2,3,4}, 7, 3},
    {"mov rax, imm64",            {0x48,0xb8,1,2,3,4,5,6,7,8}, 10, 0},
    {"lea r12, [rsp+8]",          {0x4c,0x8d,0x64,0x24,0x08}, 5, 0},
    {"mov rax, [rbp+r12*1+0x10]", {0x4a,0x8b,0x44,0x25,0x10}, 5, 0},
    {"mov eax, [r12*1+disp32]",   {0x42,0x8b,0x04,0x25,1,2,3,4}, 8, 0},
    {"call rel32",                {0xe8,1,2,3,4}, 5, 1},
    {"push rbp",                  {0x55}, 1, 0},
    {"push r14",                  {0x41,0x56}, 2, 0},
    {"mov rbp, rsp",              {0x48,0x89,0xe5}, 3, 0},
    {"sub rsp, 0x10",             {0x48,0x83,0xec,0x10}, 4, 0},
    {"mov dword [rax], imm32",    {0xc7,0x00,1,2,3,4}, 6, 0},
    {"mov qword [rax], imm32",    {0x48,0xc7,0x00,1,2,3,4}, 7, 0},
  };
  int fails = 0;
  for (unsigned i = 0; i < sizeof(tests)/sizeof(*tests); i++) {
    int reloc = 0;
    int len = subhook_disasm(tests[i].b, &reloc);
    int ok = len == tests[i].len && reloc == tests[i].reloc;
    fails += !ok;
    printf("%-28s len %2d (want %2d) reloc %d (want %d) %s\n", tests[i].name, len, tests[i].len, reloc, tests[i].reloc, ok ? "ok" : "FAIL");
  }
  return fails;
}
