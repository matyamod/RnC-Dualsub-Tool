import io
import struct


def get_size(f: io.BufferedReader):
    pos = f.tell()
    f.seek(0, 2)
    size = f.tell()
    f.seek(pos)
    return size


def read_uint32(f: io.BufferedReader) -> int:
    return struct.unpack("<I", f.read(4))[0]


def read_uint16_array(f: io.BufferedReader, num: int) -> list[int]:
    return struct.unpack("<" + "H".__mul__(num), f.read(2 * num))


def read_uint32_array(f: io.BufferedReader, num: int) -> list[int]:
    return struct.unpack("<" + "I".__mul__(num), f.read(4 * num))


def read_str(f: io.BufferedReader) -> str:
    start: int = f.tell()
    while f.read(1) != b"\x00":
        pass
    length: int = f.tell() - start
    f.seek(-length, 1)
    string: str = f.read(length - 1).decode(encoding="utf-8")
    f.seek(1, 1)
    return string


def write_str(f: io.BufferedWriter, string: str):
    f.write(string.encode(encoding="utf-8"))
    f.write(b"\x00")


def write_uint32(f: io.BufferedWriter, num: int):
    f.write(struct.pack("<I", num))


def write_uint16_array(f: io.BufferedWriter, ary: list[int]):
    num: int = len(ary)
    f.write(struct.pack("<" + "H".__mul__(num), *ary))


def write_uint32_array(f: io.BufferedWriter, ary: list[int]):
    num: int = len(ary)
    f.write(struct.pack("<" + "I".__mul__(num), *ary))


def get_align_length(f, align: int) -> int:
    return (align - f.tell() % align) % align


def check_type(x, name: str, obj_type: type, elm_type: type = None):
    is_safe: bool = isinstance(x, obj_type)
    if obj_type in [list, tuple] and elm_type is not None:
        is_safe = is_safe and all(isinstance(elm, elm_type) for elm in x)
    if not is_safe:
        obj_type_str: str = obj_type.__name__
        x_type_str: str = type(x).__name__
        if elm_type is not None:
            obj_type_str += " of " + elm_type.__name__
            if type(x) in [list, tuple]:
                x_type_str += " of " + type(x[0]).__name__

        raise TypeError(f"{name} should be {obj_type_str}, not {x_type_str}")


def check_length(x, name: str, length: int):
    if len(x) != length:
        raise TypeError(f"Length of {name} should be {length}")


def compare(file1: str, file2: str):
    f1 = open(file1, "rb")
    f2 = open(file2, "rb")
    print(f"Comparing {file1} and {file2}...")

    f1_size = get_size(f1)
    f2_size = get_size(f2)

    f1_bin = f1.read()
    f2_bin = f2.read()
    f1.close()
    f2.close()

    if f1_size == f2_size and f1_bin == f2_bin:
        print("They have the same data!")
        return

    i = 0
    for b1, b2 in zip(f1_bin, f2_bin):
        if b1 != b2:
            break
        i += 1

    raise RuntimeError(f"Not the same :{i} ({file1})")
