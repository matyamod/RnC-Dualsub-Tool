"""Localization assets (*.localization)."""

import ctypes as c
import io
from typing import Final
from io_util import (
    get_size,
    read_uint32, read_uint32_array, read_uint16_array,
    write_uint32, write_uint32_array, write_uint16_array,
    read_str, write_str,
    get_align_length
)

TAG_TO_CLASS = {
    b"\x03\xa9\x40\xd5": "EntriesCountSection",
    b"\x50\x80\xa5\x06": "KeyHashesSection",
    b"\xb5\x31\x37\xc4": "SortedKeyHashesSection",
    b"\xe9\xcf\xd2\x0c": "SortedIndexesSection",
    b"\xbd\xce\x73\x4d": "KeysDataSection",
    b"\xb2\x55\xea\xa4": "KeysOffsetsSection",
    b"\x43\x32\x65\xb0": "UnknownSection",
    b"\xb8\x82\xa3\x70": "ValuesDataSection",
    b"\xb4\xee\x0d\xf8": "ValuesOffsetsSection",
}

CLASS_TO_TAG = {v: k for k, v in TAG_TO_CLASS.items()}


class Entry:
    def read_key_offset(self, f: io.BufferedReader):
        self.key_offset = read_uint32(f)

    def read_value_offset(self, f: io.BufferedReader):
        self.value_offset = read_uint32(f)

    def read_key(self, f: io.BufferedReader):
        start = f.tell()
        f.seek(self.key_offset, 1)
        self.key = read_str(f)
        f.seek(start)

    def read_value(self, f: io.BufferedReader):
        start = f.tell()
        f.seek(self.value_offset, 1)
        self.value = read_str(f)
        f.seek(start)

    def collect_values(self, values: list[str], offset: int):
        if (self.value == "" and self.value in values):
            self.value_offset = 0
            return offset
        values.append(self.value)
        self.value_offset = offset
        offset += len(self.value.encode("utf-8")) + 1
        return offset

    def write_key_offset(self, f: io.BufferedReader):
        write_uint32(f, self.key_offset)

    def write_value_offset(self, f: io.BufferedReader):
        write_uint32(f, self.value_offset)

    def add_to_json(self, j: dict):
        j[self.key] = self.value

    def print(self):
        print("entry:")
        print(f"  key_offset: {self.key_offset}")
        print(f"  value_offset: {self.value_offset}")
        print(f"  key: {self.key}")
        print(f"  value: {self.value}")


class SectionInfo(c.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("tag", c.c_char * 4),
        ("offset", c.c_uint32),
        ("size", c.c_uint32),
    ]

    def print(self):
        if (self.tag not in TAG_TO_CLASS):
            raise RuntimeError(f"Unknown section tag detected. ({self.tag})")
        print(f"{TAG_TO_CLASS[self.tag]} (offset: {self.offset}, size: {self.size})")


class DAT1:
    TAG: Final[bytes] = b"1TAD"

    def read(self, f: io.BufferedReader, parent_tag: bytes):
        tag = f.read(4)
        if tag != DAT1.TAG:
            raise RuntimeError("Invalid DAT1 tag.")

        tag = f.read(4)
        if tag != parent_tag:
            raise RuntimeError("Invalid parent tag.")

        data_size = read_uint32(f)
        actual_size = get_size(f)
        if data_size != actual_size:
            raise RuntimeError("DAT1 info doesn't match the actual data size. "
                               f"(info: {data_size}, actual: {actual_size})")

        section_count = read_uint32(f)
        self.section_info_list = [SectionInfo() for i in range(section_count)]
        list(map(lambda x: f.readinto(x), self.section_info_list))
        self.unk = f.read(36)

        self.read_entry_count(f)
        self.entries = [Entry() for i in range(self.entry_count)]

        self.read_key_hashes(f)
        self.read_sorted_key_hashes(f)
        self.read_sorted_indexes(f)
        self.read_key_offsets(f)
        self.read_value_offsets(f)
        self.read_unknown_ints(f)
        self.read_keys(f)
        self.read_values(f)

    def get_section_info(self, tag: bytes) -> SectionInfo:
        for section in self.section_info_list:
            if section.tag == tag:
                return section
        return None

    def check_section_size(self, f: io.BufferedReader, section: SectionInfo):
        actual_size = f.tell() - section.offset
        if (section.size != actual_size):
            raise RuntimeError("Unexpected section size."
                               f" (class: {TAG_TO_CLASS[section.tag]},"
                               f" expected: {section.size}, actual: {actual_size})")

    def read_entry_count(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["EntriesCountSection"])
        f.seek(section.offset)
        self.entry_count = read_uint32(f)
        self.check_section_size(f, section)

    def read_key_hashes(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["KeyHashesSection"])
        f.seek(section.offset)
        self.key_hashes = read_uint32_array(f, self.entry_count)
        self.check_section_size(f, section)

    def read_sorted_key_hashes(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["SortedKeyHashesSection"])
        f.seek(section.offset)
        self.sorted_key_hashes = read_uint32_array(f, self.entry_count)
        self.check_section_size(f, section)

    def read_sorted_indexes(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["SortedIndexesSection"])
        f.seek(section.offset)
        self.sorted_indexes = read_uint16_array(f, self.entry_count)
        self.check_section_size(f, section)

    def read_key_offsets(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["KeysOffsetsSection"])
        f.seek(section.offset)
        list(map(lambda x: x.read_key_offset(f), self.entries))
        self.check_section_size(f, section)

    def read_unknown_ints(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["UnknownSection"])
        f.seek(section.offset)
        self.unknown_ints = read_uint32_array(f, self.entry_count)
        self.check_section_size(f, section)

    def read_value_offsets(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["ValuesOffsetsSection"])
        f.seek(section.offset)
        list(map(lambda x: x.read_value_offset(f), self.entries))
        self.check_section_size(f, section)

    def read_keys(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["KeysDataSection"])
        f.seek(section.offset)
        self.keys = f.read(section.size)
        f.seek(section.offset)
        list(map(lambda x: x.read_key(f), self.entries))

    def read_values(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["ValuesDataSection"])
        f.seek(section.offset)
        list(map(lambda x: x.read_value(f), self.entries))

    def write(self, f: io.BufferedWriter, parent_tag: bytes):
        # write tags
        f.write(DAT1.TAG)
        f.write(parent_tag)

        # skip data_size, section info
        offset_to_data_size = f.tell()
        f.write(b"\x00" * (8 + 12 * len(self.section_info_list)))

        f.write(self.unk)
        self.write_entry_count(f)
        self.write_key_hashes(f)
        self.write_sorted_key_hashes(f)
        self.write_sorted_indexes(f)
        self.write_key_offsets(f)

        values = []
        offset = 0
        for e in self.entries:
            offset = e.collect_values(values, offset)

        self.write_value_offsets(f)
        self.write_unknown_ints(f)
        self.write_keys(f)
        self.write_values(f, values)

        # write data_size, section info
        data_size = f.tell()
        f.seek(offset_to_data_size)
        write_uint32(f, data_size)
        write_uint32(f, len(self.section_info_list))
        list(map(lambda x: f.write(x), self.section_info_list))

        # seek to end
        f.seek(0, 2)

    def align(self, f: io.BufferedReader, align: int):
        pad = get_align_length(f, align)
        f.write(b"\x00" * pad)

    def write_entry_count(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["EntriesCountSection"])
        section.offset = f.tell()
        write_uint32(f, len(self.entries))
        section.size = f.tell() - section.offset
        self.align(f, 16)

    def write_key_hashes(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["KeyHashesSection"])
        section.offset = f.tell()
        write_uint32_array(f, self.key_hashes)
        section.size = f.tell() - section.offset
        self.align(f, 16)

    def write_sorted_key_hashes(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["SortedKeyHashesSection"])
        section.offset = f.tell()
        write_uint32_array(f, self.sorted_key_hashes)
        section.size = f.tell() - section.offset
        self.align(f, 16)

    def write_sorted_indexes(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["SortedIndexesSection"])
        section.offset = f.tell()
        write_uint16_array(f, self.sorted_indexes)
        section.size = f.tell() - section.offset
        self.align(f, 16)

    def write_key_offsets(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["KeysOffsetsSection"])
        section.offset = f.tell()
        list(map(lambda x: x.write_key_offset(f), self.entries))
        section.size = f.tell() - section.offset
        self.align(f, 16)

    def write_unknown_ints(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["UnknownSection"])
        section.offset = f.tell()
        write_uint32_array(f, self.unknown_ints)
        section.size = f.tell() - section.offset
        self.align(f, 16)

    def write_value_offsets(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["ValuesOffsetsSection"])
        section.offset = f.tell()
        list(map(lambda x: x.write_value_offset(f), self.entries))
        section.size = f.tell() - section.offset
        self.align(f, 16)

    def write_keys(self, f: io.BufferedReader):
        section = self.get_section_info(CLASS_TO_TAG["KeysDataSection"])
        section.offset = f.tell()
        f.write(self.keys)
        section.size = f.tell() - section.offset
        self.align(f, 16)

    def write_values(self, f: io.BufferedReader, values: list[str]):
        section = self.get_section_info(CLASS_TO_TAG["ValuesDataSection"])
        section.offset = f.tell()
        list(map(lambda x: write_str(f, x), values))
        section.size = f.tell() - section.offset

    def get_json(self) -> dict:
        j = {}

        for e in self.entries:
            e.add_to_json(j)

        return j

    def import_json(self, j: dict):

        i = 0
        max_i = len(j)
        for key, value in j.items():
            for e in self.entries:
                if e.key == key:
                    e.value = value
                    break
            i += 1
            if (i % 100 == 0 or i == len(j)):
                print(f"\r{i}/{max_i}", end="", flush=True)
        print("")


class Localization:
    TAG: Final[bytes] = b"\xAB\xB0\x2B\x12"

    def read(self, f: io.BufferedReader):
        tag = f.read(4)
        if tag != Localization.TAG:
            raise RuntimeError("Invalid localization tag.")

        data_size = read_uint32(f)
        actual_size = get_size(f) - 36
        if data_size != actual_size:
            raise RuntimeError("header info doesn't match the actual file size. "
                               f"(info: {data_size}, actual: {actual_size})")
        self.unk = f.read(28)
        data = f.read(data_size)
        reader = io.BytesIO(data)
        self.data = DAT1()
        self.data.read(reader, tag)
        reader.close()

    def write(self, f: io.BufferedWriter):
        # Write DAT1
        writer = io.BytesIO(b"")
        self.data.write(writer, Localization.TAG)
        writer.seek(0)
        data = writer.read()

        f.write(Localization.TAG)
        write_uint32(f, len(data))
        f.write(self.unk)
        f.write(data)

    def get_json(self) -> dict:
        return self.data.get_json()

    def import_json(self, j: dict):
        self.data.import_json(j)

    def get_ext(self):
        return ".localization"
