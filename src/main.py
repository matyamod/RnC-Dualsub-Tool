import argparse
import io
import json
import os
from localization import Localization
from dualsub import make_dualsub
from io_util import compare


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, help=".localization")
    parser.add_argument("json", nargs="?", type=str, help=".json")
    parser.add_argument("--mode", type=str, default="extract", help="extract, merge, inject, or validate")
    args = parser.parse_args()
    return args


def add_new_to_filename(file, ext):
    if file.endswith(ext):
        new_file = file[:-len(ext)] + ".new" + ext
    else:
        new_file = file + ".new"
    return new_file


def extract_json_from_loc(file: str) -> str:
    loc = Localization()
    with io.open(file, "rb") as f:
        loc.read(f)
    j = loc.get_json()

    new_file = file + ".json"
    with open(new_file, 'w', encoding='utf-8') as f:
        json.dump(j, f, indent=4, ensure_ascii=False)
    return new_file


def inject_json_to_loc(file: str, json_file: str) -> str:
    with open(json_file, encoding='utf-8') as f:
        j = json.load(f)

    loc = Localization()
    with io.open(file, "rb") as f:
        loc.read(f)

    loc.import_json(j)
    new_file = add_new_to_filename(file, ".localization")
    with io.open(new_file, "wb") as f:
        loc.write(f)
    return new_file


def merge_subtitles(file: str, json_file: str) -> str:
    with open(file, encoding='utf-8') as f:
        main_j = json.load(f)

    with open(json_file, encoding='utf-8') as f:
        sub_j = json.load(f)

    main_j = make_dualsub(main_j, sub_j)

    new_file = add_new_to_filename(file, ".json")
    with open(new_file, 'w', encoding='utf-8') as f:
        json.dump(main_j, f, indent=4, ensure_ascii=False)
    return new_file


def validate(file: str) -> bool:
    print(f"processing {file}...")

    loc = Localization()
    with io.open(file, "rb") as f:
        loc.read(f)

    new_file = file + ".new"
    with open(new_file, 'wb') as f:
        loc.write(f)

    print(f"saved as {new_file}")
    compare(file, new_file)
    return True


def has_ext(file, ext):
    return file.split(".")[-1] == ext


def main(file, json, mode, strict=True):
    if mode == "merge":
        if not has_ext(file, "json"):
            if strict:
                raise RuntimeError(f"Input file should be *.json. ({file})")
            return
    else:
        if not has_ext(file, "localization"):
            if strict:
                raise RuntimeError(f"Input file should be *.localization. ({file})")
            return

    print(f"processing {file}...")
    if mode == "extract":
        # convert .localization to .json
        new_file = extract_json_from_loc(file)
    elif mode == "merge":
        # merge two json files
        new_file = merge_subtitles(file, json)
    elif mode == "inject":
        # inject .json into .localization
        new_file = inject_json_to_loc(file, json)
    elif mode == "validate":
        validate(file)
        return
    print(f"saved as {new_file}")
    return


if __name__ == "__main__":
    args = get_args()
    if os.path.isfile(args.file):
        main(args.file, args.json, args.mode, strict=True)
    elif os.path.isdir(args.file):
        directory = args.file
        for file in os.listdir(directory):
            main(os.path.join(directory, file), args.json, args.mode, strict=False)
            print("", end="", flush=True)
    else:
        raise RuntimeError(f"Specified path doesn't exist. ({args.file})")
