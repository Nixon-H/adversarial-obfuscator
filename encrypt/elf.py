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
      - save(path) -> None

Dependencies:
    - None (standard library only: struct)
"""

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
            raise ValueError(f"Only little-endian ELF is supported")
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
        return self.e_entry - text_sec['addr']

    def replace_text(self, new_text_data: bytes, add_stub_size: int = 0):
        idx, text_sec = self.get_text_section()
        old_size = text_sec['size']
        new_size = old_size + add_stub_size
        old_offset = text_sec['offset']

        need_expand = new_size > old_size
        extra = new_size - old_size if need_expand else 0

        text_start = old_offset
        text_end = old_offset + old_size
        before = self.data[:text_start]
        after = self.data[text_end:]
        self.data = before + new_text_data + after

        text_sec['size'] = new_size
        self._set_shdr_field(idx, 'offset', text_start)
        self._set_shdr_field(idx, 'size', new_size)

        if need_expand:
            self._shift_sections_after(text_end, extra)
            self._shift_program_headers(text_sec, old_offset, new_size, extra)

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

    def _shift_sections_after(self, from_offset, delta):
        for i, sec in enumerate(self.sections):
            if sec['type'] == SHT_NULL:
                continue
            sec_off = sec['offset']
            if sec_off >= from_offset and sec['type'] != SHT_NOBITS:
                new_off = sec_off + delta
                sec['offset'] = new_off
                self._set_shdr_field(i, 'offset', new_off)

    def _shift_program_headers(self, text_sec, old_offset, new_size, delta):
        if self.e_phnum == 0:
            return
        for i, ph in enumerate(self.program_headers):
            if ph['type'] == PT_LOAD:
                ph_off = ph['offset']
                if ph_off >= old_offset:
                    ph['offset'] += delta
                    ph['filesz'] += delta
                    self._set_phdr_field(i, 'offset', ph['offset'])
                    self._set_phdr_field(i, 'filesz', ph['filesz'])

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
        if self._shstrtab is not None:
            name_offset = len(self._shstrtab)
        else:
            name_offset = 0

        shstrtab_sec = self.sections[self.e_shstrndx]
        old_shstr_size = shstrtab_sec['size']
        old_shstr_data = self.data[shstrtab_sec['offset']:shstrtab_sec['offset'] + old_shstr_size]
        new_shstr_data = old_shstr_data + name_padded
        new_shstr_size = len(new_shstr_data)

        self.data = (self.data[:shstrtab_sec['offset']] +
                     new_shstr_data +
                     self.data[shstrtab_sec['offset'] + old_shstr_size:])
        shstrtab_sec['size'] = new_shstr_size
        self._set_shdr_field(self.e_shstrndx, 'size', new_shstr_size)

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
        prev_shdr_end = self.e_shoff + (self.e_shnum - 1) * self._shdr_size

        if prev_shdr_end >= len(self.data):
            self.data += shdr_data
        else:
            self.data = (self.data[:prev_shdr_end] +
                         shdr_data +
                         self.data[prev_shdr_end:])

        if self.is_64:
            self.data = (self.data[:60] +
                         struct.pack('<H', self.e_shnum) +
                         struct.pack('<H', self.e_shstrndx) +
                         self.data[64:])
        else:
            self.data = (self.data[:48] +
                         struct.pack('<H', self.e_shnum) +
                         struct.pack('<H', self.e_shstrndx) +
                         self.data[52:])

    def save(self, path: str):
        with open(path, 'wb') as f:
            f.write(self.data)
