# Nixon IR Specification

## 1. Overview

Nixon IR is a custom SSA-like intermediate representation that sits between
obfuscated Python AST and LLVM IR. It represents program semantics in a
simple, typed, block-structured form designed for easy analysis and
transformation.

## 2. Module Structure

A Nixon IR module is the compilation unit. It contains:

- A module name (prefixed with `@`)
- Zero or more function declarations/definitions
- Zero or more global variable declarations

```
module @module_name
  func @func_name(%0: i32, %1: i64) -> i32 {
    ...
  }
```

## 3. Types

### 3.1 Primitive Types

| Type     | Description                     |
|----------|---------------------------------|
| `i8`     | 8-bit signed integer            |
| `i16`    | 16-bit signed integer           |
| `i32`    | 32-bit signed integer           |
| `i64`    | 64-bit signed integer           |
| `float`  | 32-bit IEEE 754 floating point  |
| `double` | 64-bit IEEE 754 floating point  |
| `ptr`    | Generic pointer                 |
| `void`   | No value (for returns/procedures) |
| `i1`     | 1-bit boolean                   |

### 3.2 Derived Types

| Type               | Syntax              | Description                    |
|--------------------|---------------------|--------------------------------|
| Array              | `array(type, size)` | Fixed-size contiguous array    |
| Struct             | `struct(type*)`     | Heterogeneous field collection |
| Pointer to type    | `ptr`               | Opaque pointer                 |

## 4. SSA Form

Every instruction that produces a value defines a unique virtual register
identified by an ordinal number prefixed with `%` (e.g., `%1`, `%42`).
Each register is defined exactly once (static single assignment).

```
%1 = add i32 %0, 1
%2 = mul i32 %1, 2
```

## 5. Block Structure

A function consists of a list of basic blocks. Each block has:

- A **label**: human-readable name followed by a colon (e.g., `entry:`, `loop:`)
- A **list of instructions** (non-terminator)
- A **terminator instruction** (last instruction in the block)

```
entry:
  %0 = alloca i32
  store i32 42, ptr %0
  jmp label %next

next:
  %1 = load i32, ptr %0
  ret i32 %1
```

Valid terminators: `br`, `jmp`, `ret`, `unreachable`.

## 6. Instruction Set

### 6.1 Arithmetic

All arithmetic ops produce a value of the same type as their operands.

| Opcode | Syntax                                  | Semantics              |
|--------|-----------------------------------------|------------------------|
| `add`  | `%r = add i32 %a, %b`                  | Integer addition       |
| `sub`  | `%r = sub i32 %a, %b`                  | Integer subtraction    |
| `mul`  | `%r = mul i32 %a, %b`                  | Integer multiplication |
| `div`  | `%r = div i32 %a, %b`                  | Integer division       |
| `mod`  | `%r = mod i32 %a, %b`                  | Integer modulo         |
| `and`  | `%r = and i32 %a, %b`                  | Bitwise AND            |
| `or`   | `%r = or i32 %a, %b`                   | Bitwise OR             |
| `xor`  | `%r = xor i32 %a, %b`                  | Bitwise XOR            |
| `shl`  | `%r = shl i32 %a, %b`                  | Shift left             |
| `shr`  | `%r = shr i32 %a, %b`                  | Shift right            |

### 6.2 Comparison

Comparisons produce an `i1` boolean value.

| Opcode | Syntax                                  | Semantics              |
|--------|-----------------------------------------|------------------------|
| `eq`   | `%r = eq i32 %a, %b`                   | Equal                  |
| `ne`   | `%r = ne i32 %a, %b`                   | Not equal              |
| `lt`   | `%r = lt i32 %a, %b`                   | Less than              |
| `le`   | `%r = le i32 %a, %b`                   | Less or equal          |
| `gt`   | `%r = gt i32 %a, %b`                   | Greater than           |
| `ge`   | `%r = ge i32 %a, %b`                   | Greater or equal       |

### 6.3 Control Flow

| Opcode        | Syntax                                                    | Semantics                    |
|---------------|-----------------------------------------------------------|------------------------------|
| `br`          | `br i1 %cond, label %true, label %false`                  | Conditional branch           |
| `jmp`         | `jmp label %target`                                       | Unconditional jump           |
| `ret`         | `ret i32 %val` _or_ `ret void`                            | Return from function         |
| `call`        | `%r = call @func(%arg0, %arg1)`                           | Function call                |
| `phi`         | `%r = phi i32 [%v1, label %bb1], [%v2, label %bb2]`      | Phi node for SSA             |

### 6.4 Memory

| Opcode   | Syntax                                          | Semantics                  |
|----------|-------------------------------------------------|----------------------------|
| `alloca` | `%r = alloca i32`                               | Stack allocate             |
| `load`   | `%r = load i32, ptr %p`                         | Load from pointer          |
| `store`  | `store i32 %val, ptr %p`                        | Store to pointer           |
| `gep`    | `%r = gep ptr %base, i32 %index`                | Get element pointer        |

### 6.5 Cast

| Opcode     | Syntax                                    | Semantics               |
|------------|-------------------------------------------|-------------------------|
| `zext`     | `%r = zext i1 %val to i32`               | Zero extend             |
| `trunc`    | `%r = trunc i32 %val to i1`              | Truncate                |
| `sitofp`   | `%r = sitofp i32 %val to double`         | Signed int to float     |
| `fptosi`   | `%r = fptosi double %val to i32`         | Float to signed int     |
| `bitcast`  | `%r = bitcast ptr %val to ptr`           | Reinterpret bits        |

### 6.6 Special

| Opcode        | Syntax        | Semantics                   |
|---------------|---------------|-----------------------------|
| `nop`         | `nop`         | No operation                |
| `unreachable` | `unreachable` | Marks unreachable code      |

### 6.7 Opaque handles

The IR has no module or object type. A value that stands for
something the runtime owns — an imported module, a builtin used as a
value, a string — is represented by an **opaque handle**: a
module-level global of type `i32`, loaded where it is used.

```
global i32 @__nx_mod_hashlib = 0
...
%7 = load i32, ptr @__nx_mod_hashlib
```

The handle is an identity, not a value: what it points to is the
runtime's business. A name the IR cannot represent at all is an
error in strict mode (`UnresolvedNameError`), never the integer 0.

## 7. Text Format Grammar

```
module    ::= "module" "@" ident "\n" { func | global }

func      ::= "func" "@" ident "(" [ param { "," param } ] ")" [ "->" type ]
              "{" { block } "}"

param     ::= "%" ident ":" type

block     ::= label ":" "\n" { inst } terminator

label     ::= ident

inst      ::= [ value "=" ] opcode [ type ] operands "\n"

terminator ::= "br" cond_operands "\n"
             | "jmp" jmp_operand "\n"
             | "ret" [ type value ] "\n"
             | "unreachable" "\n"

value     ::= "%" int

opcode    ::= "add" | "sub" | "mul" | "div" | "mod"
            | "and" | "or" | "xor" | "shl" | "shr"
            | "eq" | "ne" | "lt" | "le" | "gt" | "ge"
            | "alloca" | "load" | "store"
            | "call" | "phi" | "gep"
            | "zext" | "trunc" | "sitofp" | "fptosi" | "bitcast"
            | "nop" | "unreachable"

type      ::= "i8" | "i16" | "i32" | "i64"
            | "float" | "double" | "ptr" | "void" | "i1"

operand   ::= value | constant

constant  ::= int_literal | float_literal | string_literal | "null"
```

## 8. Example

Input Python:
```python
def factorial(n):
    result = 1
    while n > 1:
        result = result * n
        n = n - 1
    return result
```

Output Nixon IR:
```nir
module @example
  func @factorial(%0: i32) -> i32 {
  entry:
    %1 = alloca i32
    store i32 1, ptr %1
    %2 = alloca i32
    store i32 %0, ptr %2
    jmp label %header
  header:
    %3 = load i32, ptr %2
    %4 = gt i32 %3, 1
    br i1 %4, label %body, label %exit
  body:
    %5 = load i32, ptr %1
    %6 = load i32, ptr %2
    %7 = mul i32 %5, %6
    store i32 %7, ptr %1
    %8 = load i32, ptr %2
    %9 = sub i32 %8, 1
    store i32 %9, ptr %2
    jmp label %header
  exit:
    %10 = load i32, ptr %1
    ret i32 %10
  }
```
