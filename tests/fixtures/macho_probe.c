/* Minimal Mach-O probe (reviewer P1, 2026-11-20): gives native_harden a REAL
 * Mach-O object to parse, so the macOS path is exercised on real bytes rather
 * than a synthetic fixture.
 *
 * Build (Linux, clang cross-target; produces a relocatable Mach-O, which is
 * enough to test the parser -- codesigned dylibs need a macOS host):
 *   clang --target=arm64-apple-macos11 -c macho_probe.c -o macho_arm64.o
 *   clang --target=x86_64-apple-macos11 -c macho_probe.c -o macho_x86_64.o
 */
int nixon_probe_export(int x)
{
    return x + 1;
}
