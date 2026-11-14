"""ELF binary parser and manipulator.

Parses ELF32/ELF64 headers, section tables, and program headers. Supports
finding/replacing the .text section, modifying the entry point, and adding
a custom `.shadorenc` metadata section for the encryption pipeline.

Public API:
    - ELFParser(data): main parser class
      - find_section(name) -> (index, section_dict)
      - get_text_section() -> (index, section_dict)
      - get_entry_offset_in_text() -> int
      - replace_text(new_text_data, add_stub_size) -> None
      - set_entry_point(new_entry) -> None
      - add_shadorenc_section(metadata) -> None
      - save(path, mode=None) -> None

Dependencies:
    - None (standard library only: os, struct)
"""

import os
import struct

EI_NIDENT = 16
EI_CLASS = 4
EI_DATA = 5
ELFCLASS32 = 1
ELFCLASS64 = 2
ELFDATA2LSB = 1
ELFDATA2MSB = 2

SHT_NULL = 0
SHT_PROGBITS = 1
SHT_NOBITS = 8

PT_LOAD = 1
PT_PHDR = 6

SHADORENC_SECTION_NAME = b'.shadorenc'

EHDR_FMT_64 = '<16sHHIQQQIHHHHHH'
EHDR_FMT_32 = '<16sHHIIIIIHHHHHH'

SHDR_FMT_64 = '<IIQQQQIIQQ'
SHDR_FMT_32 = '<IIIIIIIIII'

PHDR_FMT_64 = '<IIQQQQQQ'
PHDR_FMT_32 = '<IIIIIIII'

EHDR_SIZE_64 = struct.calcsize(EHDR_FMT_64)
EHDR_SIZE_32 = struct.calcsize(EHDR_FMT_32)
SHDR_SIZE_64 = struct.calcsize(SHDR_FMT_64)
SHDR_SIZE_32 = struct.calcsize(SHDR_FMT_32)
PHDR_SIZE_64 = struct.calcsize(PHDR_FMT_64)
PHDR_SIZE_32 = struct.calcsize(PHDR_FMT_32)

_SHDR_FIELD_OFFSETS_64 = {
    'name_idx': 0, 'type': 1, 'flags': 2, 'addr': 3,
    'offset': 4, 'size': 5, 'link': 6, 'info': 7,
    'addralign': 8, 'entsize': 9,
}
_SHDR_FIELD_OFFSETS_32 = {
    'name_idx': 0, 'type': 1, 'flags': 2, 'addr': 3,
    'offset': 4, 'size': 5, 'link': 6, 'info': 7,
    'addralign': 8, 'entsize': 9,
}

_PHDR_FIELD_OFFSETS_64 = {'type': 0, 'flags': 1, 'offset': 2, 'vaddr': 3,
                           'paddr': 4, 'filesz': 5, 'memsz': 6, 'align': 7}
_PHDR_FIELD_OFFSETS_32 = {'type': 0, 'flags': 1, 'offset': 2, 'vaddr': 3,
                           'paddr': 4, 'filesz': 5, 'memsz': 6, 'align': 7}


class ELFParser:
    def __init__(self, data: bytes):
        self.data = data
        self._parse_ident()
        self._parse_headers()

    def _parse_ident(self):
        if len(self.data) < EI_NIDENT:
            raise ValueError("Not a valid ELF: too short")
        if self.data[:4] != b'\x7fELF':
            raise ValueError("Not a valid ELF: missing magic")
        self.elf_class = self.data[EI_CLASS]
        self.elf_data = self.data[EI_DATA]
        if self.elf_class not in (ELFCLASS32, ELFCLASS64):
            raise ValueError(f"Unsupported ELF class: {self.elf_class}")
        if self.elf_data != ELFDATA2LSB:
            raise ValueError("Only little-endian ELF is supported")
        self.is_64 = self.elf_class == ELFCLASS64

    def _parse_headers(self):
        data = self.data

        if self.is_64:
            if len(data) < EHDR_SIZE_64:
                raise ValueError("ELF64 header truncated")
            fields = struct.unpack_from(EHDR_FMT_64, data, 0)
            self.e_type = fields[1]
            self.e_machine = fields[2]
            self.e_version = fields[3]
            self.e_entry = fields[4]
            self.e_phoff = fields[5]
            self.e_shoff = fields[6]
            self.e_flags = fields[7]
            self.e_ehsize = fields[8]
            self.e_phentsize = fields[9]
            self.e_phnum = fields[10]
            self.e_shentsize = fields[11]
            self.e_shnum = fields[12]
            self.e_shstrndx = fields[13]
            self._shdr_fmt = SHDR_FMT_64
            self._phdr_fmt = PHDR_FMT_64
            self._shdr_size = SHDR_SIZE_64
            self._phdr_size = PHDR_SIZE_64
        else:
            if len(data) < EHDR_SIZE_32:
                raise ValueError("ELF32 header truncated")
            fields = struct.unpack_from(EHDR_FMT_32, data, 0)
            self.e_type = fields[1]
            self.e_machine = fields[2]
            self.e_version = fields[3]
            self.e_entry = fields[4]
            self.e_phoff = fields[5]
            self.e_shoff = fields[6]
            self.e_flags = fields[7]
            self.e_ehsize = fields[8]
            self.e_phentsize = fields[9]
            self.e_phnum = fields[10]
            self.e_shentsize = fields[11]
            self.e_shnum = fields[12]
            self.e_shstrndx = fields[13]
            self._shdr_fmt = SHDR_FMT_32
            self._phdr_fmt = PHDR_FMT_32
            self._shdr_size = SHDR_SIZE_32
            self._phdr_size = PHDR_SIZE_32

        self.sections = []
        if self.e_shoff > 0 and self.e_shnum > 0:
            ssize = self._shdr_size
            for i in range(self.e_shnum):
                offset = self.e_shoff + i * ssize
                if offset + ssize > len(data):
                    break
                self.sections.append(self._parse_shdr(data, offset))

        self.program_headers = []
        if self.e_phoff > 0 and self.e_phnum > 0:
            psize = self._phdr_size
            for i in range(self.e_phnum):
                offset = self.e_phoff + i * psize
                if offset + psize > len(data):
                    break
                self.program_headers.append(self._parse_phdr(data, offset))

        self._shstrtab = None
        if self.e_shstrndx < len(self.sections):
            shstr = self.sections[self.e_shstrndx]
            if shstr['offset'] > 0 and shstr['size'] > 0:
                end = shstr['offset'] + shstr['size']
                if end <= len(data):
                    self._shstrtab = data[shstr['offset']:end]

    def _parse_shdr(self, data, offset):
        fields = struct.unpack_from(self._shdr_fmt, data, offset)
        return {
            'name_idx': fields[0],
            'type': fields[1],
            'flags': fields[2],
            'addr': fields[3],
            'offset': fields[4],
            'size': fields[5],
            'link': fields[6],
            'info': fields[7],
            'addralign': fields[8],
            'entsize': fields[9],
        }

    def _parse_phdr(self, data, offset):
        fields = struct.unpack_from(self._phdr_fmt, data, offset)
        return {
            'type': fields[0],
            'flags': fields[1],
            'offset': fields[2],
            'vaddr': fields[3],
            'paddr': fields[4],
            'filesz': fields[5],
            'memsz': fields[6],
            'align': fields[7],
        }

    def section_name(self, section):
        if self._shstrtab is not None and section['name_idx'] < len(self._shstrtab):
            end = self._shstrtab.find(b'\x00', section['name_idx'])
            if end >= section['name_idx']:
                return self._shstrtab[section['name_idx']:end]
        return b''

    def find_section(self, name):
        for i, sec in enumerate(self.sections):
            if self.section_name(sec) == name:
                return i, sec
        return None, None

    def section_data(self, section):
        offset = section['offset']
        size = section['size']
        if offset + size > len(self.data):
            raise ValueError("Section data extends beyond file")
        return self.data[offset:offset + size]

    def get_text_section(self):
        idx, sec = self.find_section(b'.text')
        if sec is None:
            raise ValueError("No .text section found")
        return idx, sec

    def get_entry_offset_in_text(self):
        _, text_sec = self.get_text_section()
        off = self.e_entry - text_sec['addr']
        if off < 0 or off >= text_sec['size']:
            raise ValueError(
                f"entry point {self.e_entry:#x} is outside .text "
                f"[{text_sec['addr']:#x}, "
                f"{text_sec['addr'] + text_sec['size']:#x})")
        return off

    def replace_text(self, new_text_data: bytes, add_stub_size: int = 0):
        idx, text_sec = self.get_text_section()
        old_size = text_sec['size']
        new_size = len(new_text_data)
        if add_stub_size and new_size != old_size + add_stub_size:
            raise ValueError(
                f"new_text_data is {new_size} bytes but old_size + "
                f"add_stub_size is {old_size + add_stub_size}")
        old_offset = text_sec['offset']
        text_end = old_offset + old_size
        delta = new_size - old_size

        self.data = (self.data[:old_offset] + new_text_data
                     + self.data[text_end:])

        if delta:
            # The section header table usually sits after .text.  Move it
            # with the splice before any _set_shdr_field call reads e_shoff.
            if self.e_shoff >= text_end:
                self.e_shoff += delta
                self._set_e_shoff(self.e_shoff)
            if self.e_phoff >= text_end:
                self.e_phoff += delta
                self._set_e_phoff(self.e_phoff)
            self._shift_sections_after(text_end, delta)
            self._shift_program_headers(old_offset, old_size, new_size, delta)

        text_sec['size'] = new_size
        self._set_shdr_field(idx, 'offset', old_offset)
        self._set_shdr_field(idx, 'size', new_size)

    def _shdr_field_index(self, name):
        if self.is_64:
            return _SHDR_FIELD_OFFSETS_64[name]
        return _SHDR_FIELD_OFFSETS_32[name]

    def _phdr_field_index(self, name):
        if self.is_64:
            return _PHDR_FIELD_OFFSETS_64[name]
        return _PHDR_FIELD_OFFSETS_32[name]

    def _get_shdr_fields(self, idx):
        offset = self.e_shoff + idx * self._shdr_size
        return list(struct.unpack_from(self._shdr_fmt, self.data, offset))

    def _set_shdr_field(self, idx, field_name, value):
        fi = self._shdr_field_index(field_name)
        offset = self.e_shoff + idx * self._shdr_size
        fields = list(struct.unpack_from(self._shdr_fmt, self.data, offset))
        fields[fi] = value
        self.data = (self.data[:offset] +
                     struct.pack(self._shdr_fmt, *fields) +
                     self.data[offset + self._shdr_size:])

    def _get_phdr_fields(self, idx):
        offset = self.e_phoff + idx * self._phdr_size
        return list(struct.unpack_from(self._phdr_fmt, self.data, offset))

    def _set_phdr_field(self, idx, field_name, value):
        fi = self._phdr_field_index(field_name)
        offset = self.e_phoff + idx * self._phdr_size
        fields = list(struct.unpack_from(self._phdr_fmt, self.data, offset))
        fields[fi] = value
        self.data = (self.data[:offset] +
                     struct.pack(self._phdr_fmt, *fields) +
                     self.data[offset + self._phdr_size:])

    def _set_e_shoff(self, value):
        off = 0x28 if self.is_64 else 0x20
        fmt = '<Q' if self.is_64 else '<I'
        size = struct.calcsize(fmt)
        self.data = (self.data[:off] + struct.pack(fmt, value)
                     + self.data[off + size:])

    def _set_e_phoff(self, value):
        off = 0x20 if self.is_64 else 0x1c
        fmt = '<Q' if self.is_64 else '<I'
        size = struct.calcsize(fmt)
        self.data = (self.data[:off] + struct.pack(fmt, value)
                     + self.data[off + size:])

    def _set_e_phnum(self, value):
        off = 56 if self.is_64 else 44
        self.data = (self.data[:off] + struct.pack('<H', value)
                     + self.data[off + 2:])

    def _set_e_shnum(self, value):
        off = 60 if self.is_64 else 48
        self.data = (self.data[:off] + struct.pack('<H', value)
                     + self.data[off + 2:])

    def _shift_sections_after(self, from_offset, delta):
        for i, sec in enumerate(self.sections):
            if sec['type'] == SHT_NULL:
                continue
            sec_off = sec['offset']
            if sec_off >= from_offset and sec['type'] != SHT_NOBITS:
                new_off = sec_off + delta
                sec['offset'] = new_off
                self._set_shdr_field(i, 'offset', new_off)

    def _shift_program_headers(self, old_offset, old_size, new_size, delta):
        if self.e_phnum == 0:
            return
        text_end = old_offset + old_size
        for i, ph in enumerate(self.program_headers):
            ph_off = ph['offset']
            if ph['type'] == PT_LOAD:
                ph_filesz = ph['filesz']
                contains_text = (ph_off <= old_offset
                                 and text_end <= ph_off + ph_filesz)
                if contains_text:
                    ph['filesz'] = ph_filesz + delta
                    if ph['memsz'] == ph_filesz:
                        ph['memsz'] = ph['filesz']
                    else:
                        ph['memsz'] = max(ph['memsz'], ph['filesz'])
                    self._set_phdr_field(i, 'filesz', ph['filesz'])
                    self._set_phdr_field(i, 'memsz', ph['memsz'])
                    continue
            # Every other header that points past the splice (PT_DYNAMIC,
            # PT_GNU_RELRO, PT_GNU_EH_FRAME, ...) moves with the data.
            if ph_off >= text_end:
                ph['offset'] = ph_off + delta
                self._set_phdr_field(i, 'offset', ph['offset'])

    def plan_load_segment(self, length: int, flags: int = 5) -> dict:
        """Plan a new PT_LOAD segment appended at EOF.

        Returns the file offset, virtual address and program-header table
        size so the caller can compute the stub's text_base_delta before
        generating it.  The table is placed at the start of the new segment
        so it stays mapped (AT_PHDR stays valid).
        """
        page = 0x1000
        file_off = (len(self.data) + page - 1) & ~(page - 1)
        max_end = 0
        for ph in self.program_headers:
            if ph['type'] == PT_LOAD:
                max_end = max(max_end, ph['vaddr'] + ph['memsz'])
        vaddr = (max_end + page - 1) & ~(page - 1)
        if vaddr == 0:
            vaddr = page
        table_size = (len(self.program_headers) + 1) * self._phdr_size
        return {'file_off': file_off, 'vaddr': vaddr,
                'table_size': table_size, 'length': length, 'flags': flags}

    def add_load_segment(self, data: bytes, plan: dict) -> int:
        """Append ``data`` as a new executable PT_LOAD segment.

        The program-header table is relocated into the new segment (so it
        remains mapped) and PT_PHDR, when present, is updated.  Returns the
        virtual address of ``data``.
        """
        file_off = plan['file_off']
        vaddr = plan['vaddr']
        table_size = plan['table_size']
        stub_vaddr = vaddr + table_size

        # The segment covers the relocated header table *and* the payload,
        # so PT_PHDR's vaddr stays mapped.
        new_ph = {'type': PT_LOAD, 'flags': plan['flags'], 'offset': file_off,
                  'vaddr': vaddr, 'paddr': vaddr,
                  'filesz': table_size + len(data),
                  'memsz': table_size + len(data), 'align': 0x1000}
        phdrs = list(self.program_headers) + [new_ph]
        for ph in phdrs:
            if ph['type'] == PT_PHDR:
                ph['offset'] = file_off
                ph['vaddr'] = vaddr
                ph['paddr'] = vaddr
                ph['filesz'] = table_size
                ph['memsz'] = table_size

        table = b''.join(
            struct.pack(self._phdr_fmt, ph['type'], ph['flags'], ph['offset'],
                        ph['vaddr'], ph['paddr'], ph['filesz'], ph['memsz'],
                        ph['align'])
            for ph in phdrs)
        if len(table) != table_size:
            raise ValueError("program header table size mismatch")

        self.data += b'\x00' * (file_off - len(self.data))
        self.data += table + data
        self.program_headers = phdrs
        self.e_phoff = file_off
        self.e_phnum = len(phdrs)
        self._set_e_phoff(file_off)
        self._set_e_phnum(self.e_phnum)
        return stub_vaddr

    def set_entry_point(self, new_entry: int):
        self.e_entry = new_entry
        if self.is_64:
            self.data = (self.data[:24] +
                         struct.pack('<Q', new_entry) +
                         self.data[32:])
        else:
            self.data = (self.data[:24] +
                         struct.pack('<I', new_entry) +
                         self.data[28:])

    def add_shadorenc_section(self, metadata: bytes):
        name_padded = SHADORENC_SECTION_NAME + b'\x00'
        shstrtab_sec = self.sections[self.e_shstrndx]
        old_shstr_size = shstrtab_sec['size']
        old_shstr_off = shstrtab_sec['offset']
        name_offset = old_shstr_size

        # Relocate the string table to EOF instead of splicing into it:
        # splicing would shift every later section and break the
        # p_offset == p_vaddr (mod p_align) rule the kernel enforces.
        new_shstr_data = (self.data[old_shstr_off:old_shstr_off
                                    + old_shstr_size] + name_padded)
        new_shstr_off = len(self.data)
        self.data += new_shstr_data
        shstrtab_sec['offset'] = new_shstr_off
        shstrtab_sec['size'] = len(new_shstr_data)
        self._set_shdr_field(self.e_shstrndx, 'offset', new_shstr_off)
        self._set_shdr_field(self.e_shstrndx, 'size', len(new_shstr_data))
        self._shstrtab = new_shstr_data

        new_sec_offset = len(self.data)
        self.data += metadata

        new_sec = {
            'name_idx': name_offset,
            'type': SHT_PROGBITS,
            'flags': 0,
            'addr': 0,
            'offset': new_sec_offset,
            'size': len(metadata),
            'link': 0,
            'info': 0,
            'addralign': 1,
            'entsize': 0,
        }
        self.sections.append(new_sec)
        self.e_shnum += 1
        self._append_shdr(new_sec)

    def _append_shdr(self, sec):
        shdr_data = struct.pack(self._shdr_fmt,
                                sec['name_idx'], sec['type'], sec['flags'],
                                sec['addr'], sec['offset'], sec['size'],
                                sec['link'], sec['info'],
                                sec['addralign'], sec['entsize'])
        # Relocate the whole table to EOF so appending the new entry cannot
        # land between the old table and the metadata appended above.
        old_count = self.e_shnum - 1
        old_table = self.data[self.e_shoff:
                              self.e_shoff + old_count * self._shdr_size]
        new_shoff = len(self.data)
        self.data += old_table + shdr_data
        self.e_shoff = new_shoff
        self._set_e_shoff(new_shoff)
        self._set_e_shnum(self.e_shnum)

    def save(self, path: str, mode: int | None = None):
        """Write the image out.

        ``mode`` should be the source file's permission bits: an encrypted
        executable that lands as 0644 cannot be run, which makes the tool look
        broken even though the transform succeeded.
        """
        with open(path, 'wb') as f:
            f.write(self.data)
        if mode is not None:
            os.chmod(path, mode)
