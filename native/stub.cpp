#if defined(_WIN32) || defined(_WIN64)
#include "stub_win.cpp"
#elif defined(__linux__)
#include "stub_linux.cpp"
#else
#error "Unsupported platform"
#endif
