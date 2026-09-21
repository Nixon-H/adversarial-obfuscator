# Nyami changelogs v1.1 – 9.0 (pasted from Discord announcements, 2026-09-20)

> Pasted verbatim from Discord `#announcements` (user `JustManiak` posts).
> Formatting/emojis preserved where readable. These changelogs describe the
> *commercial nyami.cc obfuscator* (third-party reference), NOT our pipeline.
> Saved here because the `obf-test.py` sample in this folder is one of its outputs.

Note repeated in most versions: "I do not own the code in test.py. It's a script
I found on GitHub, used for testing various default Python capabilities. I've also
added some available macros such as IS_OBFUSCATED and GET_HWID for experimentation."

---

## Version 1.1 | First update
Changelog:
- Reworked the Variable Renamer so there are no more errors.
- Added an Integer Obfuscator
- Created the Documentation
Everything written above only applies on the first layer of the obfuscated code.

## Version 1.2 | 31.05.2025
Changelog:
- Implemented anti-debugging countermeasures to safeguard against specialized Python debugging tools.
- Redesigned the globals system with improved security.
- Added SELF_DELETE(), you can check everything about it in our documentation.
- Added SECURE_DELETE(), you can check everything about it in our documentation.
- Enhanced system security by implementing additional obfuscation layers, providing improved protection against reverse engineering.
- Refined the Discord bot's UI, improving navigation and overall user experience.
- Updated the Documentation.
nyami.cc

## Version 2.0 | 29.06.2025
Changelog:
- Reworked anti-debugging countermeasures to safeguard against specialized Python debugging tools & Virtual Machines (more info in our documentation).
- Added VM_CONFIDENCE, you can check everything about it in our documentation.
- Recoded all features for better security against reverse engineering & for a wider compatibility.
- Added Version Selection when obfuscating.
- Added KOD when obfuscating (more info about it in our documentation).
- Updated the Documentation.

## Version 2.1 | 30.06.2025
Changelog:
- Updated the Variable Renamer to be compatible with more complex scripts.
- Updated the String Obfuscator to be compatible with more complex scripts.
nyami.cc

## Version 2.2 | 07.07.2025
Changelog:
- Updated the Variable Renamer to be compatible with more complex scripts.
- Updated the Function Obfuscator for even more security.
- Added Import Protection (more info about it in our documentation).
- Improved KOD (more info about it in our documentation).
- Added Variable Renamer as an option in our bot (more info about it in our documentation).
- Added Trial as an option in our bot.
- Re-Added old Anti-Tampering checks for more security.
- Fixed Pyinstaller not extracting the modules (imports) from the obfuscated script.
- Fixed Obfuscation Options not updating the main "panel".
- Added Suggestions; Added Bug Reports.

## Version 2.3 | 19.07.2025
Changelog:
- Fixed Variable Renamer (bug id: U7ITQTV4QSOATGNJ).
- Reworked the Function Obfuscator for even more security.
- Added default Preset in our bot for efficiency.
- Fixed Deprecation Warning (bug id: ARQWMMQP7WLHKZMJ)
- Added Function Obfuscator as an option in our bot (more info about it in our documentation).
- Reworked Obfuscated Code Structure, this does not apply for the outer layers.
nyami.cc

## Version 2.4 | 22.07.2025
Changelog:
- Added Optimization as an option in our bot (more info about it in our documentation).
- Complex scripts that have gamepad support or have GUIs would often break (thanks to @tequilla). Fixed in this update with the inclusion of Optimization.

## Version 2.5 | 05.08.2025
Added Features:
- Control Flow Flattening & Obfuscation.
- Opaque Predicates.
- Wrap In Function.
- Minifier For File Optimization.
- Number Convertor.
- Junk Code Injection.
- Bytecode Transformation.
Recoded Features:
- Recoded MBA Obfuscator.
- Recoded Import Protection.
- Recoded Bytecode Protection.
- Reduced File Memory Utilisation.
- Recoded Medium Anti-Debugger.
Improved Features:
- Improved Polimorphic Layers.
- Improved Builtin Anti-Tampering.
Bug Fixes: 47VXEAV3JECD4R6N; DZE69E934HJD651M.

## Version 2.6 | 09.08.2025
Added: Customer Role (all buyers/users, never removed, bot-handled); User Role (active subscription/tokens, bot-handled).
Improved: more Optimization Levels (see docs).
Bug Fixes: 55MMCANCNG19MG4C — Function Obfuscator not compatible with Wrap In Function (WIF auto-disabled when both selected).

## Version 2.7 | 25.08.2025
Added: Beta Tester Role; Lua Obfuscator in bot (beta-only); Free Day (gives free day to everyone, no @Users role for security).
Bug Fixes: !suggest command not working.
[Note: #py-updates covers @Nyami BOT updates, not only python obfuscator updates.]
JustManiak — 9/27/25, 9:03 PM

## Version 2.8 | 27.09.2025
Added: Compress Code (extra layer compressing everything using pyzstd); Version Check; Auto Module Install (installs missing modules the obfuscator uses).
Changed: Default Preset in the discord bot; how Anti-Tampering operates.
Bug Fixes: minor bugs.

## Version 2.9 | 07.10.2025 (JustManiak — 10/8/25, 2:23 AM)
Recoded: Control Flow Flattening & Obfuscator; String Obfuscator/Encryptor.
Added: !support for staff.

## Version 2.9.5 | 16.10.2025
Added: pyinstaller option now also returns the .spec file.
Bug Fixes: couldn't build exes (thanks @Scoopy); other fixes.

## Version 2.9.6 | 25.10.2025
Bug Fixes: Anti-Debugger crashing scripts (thanks @Cu+Mg+Si+Zn); KOD crashing scripts (thanks @Whale).

## Version 3.0 | 27.10.2025
Reskin: Reskinned @Nyami using containers.

## Version 3.1 | 08.11.2025
Added: Lite Function Obfuscator (works best with wrap-in-function); Script Interconnectivity (obfuscated scripts usable as modules via `__all__` macro).
Updated: Compressor; Bytecode Protection; Anti-Tampering; Wrapper; Junk Code Inserter; Import Protection; Documentation.
Update Info: junk code removed from the outer (visible) layer and moved to another layer (people mistook it for the real code / asked AI about it / malware false-positives).

## Version 3.2 | 19.11.2025
Added: Python 3.14 Compatibility; Polymorphic Key Derivation.
Updated: Global Variables/Functions (each function compressed separately); Stub Loader; Encryption Methods — now [AES-256/SHA-512/XOR/ChaCha20/Custom]; Polymorphic Layers; Check Python Version; Lite Function Obfuscator (optional args support); Discord Bot Version (3.13 → 3.14).
Bug Fixes: Version Select.

## Version 3.3 | 07.12.2025
Added: Python To C [BETA] — Python -> C -> compiled machine code [first layer only]. Eliminates the python source while keeping one singular python file; Shards Currency (roulette); Roulette (https://nyami.cc/roulette); Leaderboard (https://nyami.cc/leaderboard); Roles [Admin/Moderator/User] (https://nyami.cc/dashboard); Admin Panel.
Updated: Dashboard (https://nyami.cc/dashboard); Settings Page; Home Page (https://nyami.cc/); Winter logo theme.
Bug Fixes: minor bugs.
Info: report bugs via !bug-report. PYTOC public beta, known problems: unicode variable names fail; macros don't work with PYTOC; incompatible with WIF (fixes in progress).

## Version 3.4 | 19.12.2025
Added: Memory Protection — memory dumping for keys/payloads is useless; keys & payloads deleted from memory, never kept in one place.
Updated: Bytecode Protection (perf & security); Compression (~64% smaller: v3.3 default 783 KB → v3.4 282 KB; PYTOC ~2.5 MB → ~534 KB); PYTOC (anti-tampering, compatibility, polymorphic encryption, Lite Function Obfuscator for compression & security + Decompiler Breaker, custom compression); Optimization (faster); Anti-Tampering; Function Obfuscator.
Bug Fixes: PYTOC compatibility with WIF.
Info: security not compromised by smaller size; compression info is benchmark-only.

## Version 3.4.1 | 06.01.2026
Bug Fixes: Anti-Debug dropdown not appearing in discord bot (thanks @polarbypass).

## Version 3.5 | 09.01.2026
Added: DETECT_FILE_TYPE() (docs link in announcement).
Updated: Decompiler Breaker (after Pylingual update — decompiled .pyc is useless, source already lost; usually won't even decompile); Anti-Tampering (fully redone); Function Obfuscator (+Decompiler Breaker); Lite Function Obfuscator (+Decompiler Breaker).
Bug Fixes: Watermark Anti-Tampering with PYTOC; Pyinstaller on obfuscated scripts (thanks @polarbypass); compatibility.
Info: file sizes higher due to new Anti-Tampering.

## Version 3.6 | 11.01.2026
Recoded: Pyinstaller Integration.
Updated: Function Obfuscator; Lite Function Obfuscator; String Obfuscator.
Bug Fixes: DETECT_FILE_TYPE() returning only unknown; PYTOC broken by Decompiler Breaker.
Info: all bug credits @polarbypass.

## Version 4.0 - PUBLIC BETA | 22.01.2026
Recoded: Discord Bot; Obfuscation System; Design; command prefix '!' → '/'.
Added: Ticket System; Booster Rewards; Auto Role Management; Auto Error Logging; Custom Discord Event Logging; Automod; Ticket Transcripts; Leveling System; Giveaway System; Admin Commands; Obfuscation Preset Auto-Save.
Removed: Compression Layer.
Bug Fixes: minor.

## Version 4.1 - PUBLIC BETA | 23.01.2026
Added: PYTOC & Macro Compatibility.
Bug Fixes: PYTOC vs Anti-Debugger Medium/Extreme; Discord Bot dying every 5 minutes.
Info: all credits @polarbypass.

## Version 4.5 | 14.02.2026 (JustManiak — 2/14/26, 9:25 PM)
Added: API System; On-Website Obfuscation; Anti-Monkey Patcher (+docs); Trial System docs.
Recoded: HWID Encryption; Trial System.
Updated: Decompiler Breaker; Variable Renamer; Lite Function Obfuscator.
Bug Fixes/Improvements: common issues; performance & file size.
Removed: Import Protection (in favor of Anti-Monkey Patcher).
Docs:
- https://nyami.gitbook.io/nyami/global-variables/anti-monkey-patcher
- https://nyami.gitbook.io/nyami/api/api-obfuscate
- https://nyami.gitbook.io/nyami/other-info/trial

## Version 5.0 | 27.04.2026
Added: Ragebait (see attached photo).
Recoded: Minifier; Decompiler Breaker; PYTOC (true in-memory execution on windows/linux).
Updated: Variable Renamer; Control Flow Flattening; Opaque Predicates; Junk Code.
Bug Fixes/Improvements: string formatting; Function Obfuscator (3.14+); performance & file size.

## Version 6.0 | 08.07.2026
Added:
- White-Box Cryptography — 8-round Feistel cipher with key embedded as S-boxes, no key bytes at runtime, renders cryptographic hooking ineffective.
- Anti-Memory-Dump — PyMarshal_ReadObjectFromString-only deserialization, ctypes-based co_code buffer zeroing via ob_sval offset detection, gc.get_objects() scan + wipe, deliberate segfault fallback.
- Memory Page Protection — VirtualProtect/mprotect, co_code page-level read-only at runtime, prevents bytecode patching by deobfuscators.
- Namespace-Isolated Executor — SHA-256 code hash verification before execution, sys.addaudithook blocking, sys.settrace/sys.gettrace integrity restore, debugger import scan.
- Custom Code Object Serializer — proprietary dumps()/loads() for CodeType, variable-length int encoding, const marshaling.
- Bootstrap Payload System — XOR-stream encrypted payload with base85 encoding, per-file random salt, addaudithook blocking.
Recoded:
- Bytecode Obfuscator — secrets.SystemRandom RNG, __slots__ optimization, HMAC-based bytecode integrity with session-keyed tagging, multi-layer protection chains.
- Lite Function Obfuscator — AST transformer, 4 compression backends (zlib/bz2/lzma/pyzstd) auto-selected, Decompiler Breaker integration.
- Integrity Check — ctypes PyMarshal_ReadObjectFromString only, zero fallback to hookable marshal.loads.
- Excepthook/Traceback Handling — sys.tracebacklimit = 0, sys.excepthook override to suppress all tracebacks.
Updated:
- Variable Renamer — randomized auto-incrementing short names (a, b, … aa, ab…), smaller output.
- String Obfuscation — new ChaCha20 version.
- Anti-Debug Monitor — thread checks sys.getprofile()/sys.gettrace monkey-patching, periodic sys.settrace re-assertion.
- Wrap-In-Function — no longer blocks lite function obfuscation.
Bug Fixes/Improvements:
- marshal.loads Hook Vulnerability — eliminated all marshal.loads from critical paths.
- exec()/eval() Interception — namespace-isolated execution with code hash verification prevents __builtins__ patching.
- String formatting in security preamble template.
- Function Obfuscator compatibility with Python 3.12+.
- HWID Lock — PBKDF2-HMAC-SHA256 key derivation for stronger HWID binding.
- Performance & File Size — 30s startup → 3s.
- Anti-Deobfuscation — removed single __nyami__ choke-point; multi-path (serializer + deserializer + bootstrap + custom exec) execution model.

## Version 7.0 | 04.08.2026 (@Mike; poster admits incomplete log)
- ZIPL — compresses python scripts, archive extraction impossible without other scripts.
- ZIP — recovery of the right script from the compressed archive very hard.
- Rewrote most parts of the obfuscator.
- Python 3.10 support (@Brianb153's request).
- ZIPL/ZIP API-only for now (too lazy to add to discord bot); ZIP unusable on discord (file sizes).

## Version 8.0 | 30.08.2026
"I won't even bother remembering, too many to keep track of."

## Version 9.0 | 01.09.2026
General Updates:
- All kernel API exports randomized per build — no fixed _nyk_* names in the pyd export table.
- IAT verification: every import slot vs GetProcAddress ground truth at end-of-init + periodic.
- _verify_eval(): python-dll address-range checks on resolved PyEval_EvalCode.
- Kernel key + layer keys compiled in as scrambled byte-lists, reconstructed in C.
- All salt/magic strings now runtime-assembled byte-lists, no plaintext in binary.
- Kernel-owned bind-once host dict: _host_g set by bind_host() (frame-walk); removed externally-settable _nyk_host_g.
- All exec paths enforce exact host-dict identity.
- Native watchdog thread: trace/profile detection, eval-pointer verification, periodic IAT re-verification.
- _nyk_kill export removed entirely.
- HWID commitment compiled into the kernel, verified natively in hwid_open before decryption.
- Removed NYAMI_*_* plaintext-dump backdoor [CENSORED TILL EVERYONE UPDATES TO THE LATEST VERSION OF NYAMI] — "left by me by accident, I was doing some testing and forgot to delete it up on releasing the update".
- All legacy key-derivation bytecode stripped from __nyami__/__load__.
- Python-level watchdog loop removed (superseded by native).
- Decryptors route through native kernel dispatch.
- (more changes untracked).
Build Time: ~15% faster (outer compression contest parallelized via ThreadPoolExecutor — C compressors release the GIL; per-byte XOR → C-level big-int XOR, byte-identical; per-function compression contest parallelized).
Added: Kernel Driver Detection [BETA].
("the update itself is much bigger btw, these are the only ones I kept track of in the 27+ hours of actively working on Nyami this update has been sponsored by my insomnia")

## Version 10 (announced, details pending as of 2026-09-20)

Past announcement summary (Discord `#announcements`, author JustManiak):
"biggest update Nyami has seen in a long time", claimed "something no
python obfuscator ever did before". Core claim: **"removal of python
inside of python"** — "everything you remember as default python thing
will be turned into something like this, for example `a + b` will become
`xyzw(a,b)` which function `xyzw` is never stored inside of python".
Author confirms: "if you use PYTOC he never will" (i.e. PYTOC path hides
the helpers natively). Community guess recorded in chat: the `xyzw`-style
helpers live in the `.pyd`s as custom decryption/dispatch.

Context notes (ours, not vendor claims):
- This reads as: Python-level operators/builtins lowered to calls into
  native (Cython `.pyd`) helpers — i.e. a **native intrinsic-dispatch /
  operator-lowering** layer on top of their existing PYTOC path.
- Business context in the same announcement: crackmes now require funding
  (paid in Nyami subscriptions unless the community brings buyers);
  author says hosting/crackmes came out of pocket.
- No changelog detail yet ("more info on that tomorrow"). Treat the above
  as a pre-release claim, not established behavior.
