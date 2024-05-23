
def ends_with_three_digits(string) -> bool:
    if string.endswith("_EX"):
        string = string[:-3]
    if len(string) <= 4:
        return False
    if string[-4] != "_":
        return False
    return string[-3:].isdecimal()


def filter_subtitles(j: dict):
    for k, v in list(j.items()):
        # each subtitle has a three-digit id in its key
        if not ends_with_three_digits(k) or v == "":
            j.pop(k)
    return j


def split_by_ts_tag(string):
    # split a string by the ts tag ("<ts=&quot;*;*&quot;>")
    a = string.split("<ts=")
    if len(a) <= 1:
        return a
    split = [a[0]]
    for b in a[1:]:
        c = b.split(">")
        split.append("<ts=" + c[0] + ">")
        split.append(">".join(c[1:]))
    return split


def get_span_from_ts_tag(tag: str) -> tuple[float, float]:
    # tag = "<ts=&quot;start;end&quot;>"
    # split = "start;end"
    split = tag.split("&quot;")[1]
    # split = ["start", "end"]
    split = split.split(";")
    return split[0], split[1]


def join_ts_tag(tag1: str, tag2: str) -> str:
    start, _ = get_span_from_ts_tag(tag1)
    _, end = get_span_from_ts_tag(tag2)
    return f"<ts=&quot;{start};{end}&quot;>"


def sorted_index(sorted_list):
    return sorted(range(len(sorted_list)), key=sorted_list.__getitem__)


def split_to_end_points(split):
    parsed = (get_span_from_ts_tag(split[i]) for i in range(0, len(split) - 2, 2))
    return [float(p[1]) for p in parsed]


def calc_end_diff(t, end_points):
    min_diff = min(abs(t - t2) for t2 in end_points)
    return min_diff


def join_pages(split, split2, len_diff):
    if (len(split2) > 2):
        # end points of time spans
        ends = split_to_end_points(split)
        ends2 = split_to_end_points(split2)

        # get indexes of end points that should be joined.
        end_diff = [calc_end_diff(t, ends2) for t in ends]
        sorted_end_index = list(sorted(sorted_index(end_diff)[-len_diff // 2:]))
    else:
        sorted_end_index = list(range(len_diff // 2))

    # joins some time spans
    for i in range(len_diff // 2):
        index = sorted_end_index.pop(0)
        index_x_2 = index * 2
        split[index_x_2] = join_ts_tag(split[index_x_2], split[index_x_2 + 2])
        split[index_x_2 + 1] = split[index_x_2 + 1] + split[index_x_2 + 3]
        sorted_end_index = [i - 1 for i in sorted_end_index]
        split.pop(index_x_2 + 3)
        split.pop(index_x_2 + 2)
    return split


def concat_subtitle(str1: str, str2: str):
    # The ts tag works like pagenation. so, we should split strings by the tags first.
    split1 = split_by_ts_tag(str1)
    split2 = split_by_ts_tag(str2)

    if len(split1) == 1 and len(split2) == 1:
        # just concatenate them with a linefeed because there is no ts tag.
        return split1[0] + "<br>" + split2[0]

    # add a fake ts tag if it doesn't have
    if len(split1) == 1 and len(split2) > 1 and not split1[0].startswith("<name"):
        split1 = ["", split2[1]] + split1
    if len(split2) == 1 and len(split1) > 1 and not split2[0].startswith("<name"):
        split2 = ["", split1[1]] + split2

    len_diff = len(split1) - len(split2)
    if len_diff % 2 != 0 or (split1[0] != "" and not split1[0].startswith("<name")):
        # error
        print(len(split1))
        print(split1)
        print(len(split2))
        print(split2)
        raise RuntimeError("Unknown pattern.")

    # split1[0] and split2[0] should be the name tags or empty strings.
    # so, we don't need to concatenate them.
    res = split1[0]
    split1 = split1[1:]
    split2 = split2[1:]

    # join pages if they have different numbers of ts tags.
    if (len_diff > 0):
        split1 = join_pages(split1, split2, len_diff)
    if (len_diff < 0):
        split2 = join_pages(split2, split1, -len_diff)

    # concatenate each page
    for i in range(0, len(split1), 2):
        res += split1[i]
        if split1[i + 1] == "":
            res += split2[i + 1]
        elif split2[i + 1] == "":
            res += split1[i + 1]
        else:
            res += split1[i + 1] + "<br>" + split2[i + 1]
    return res


def make_dualsub(main_j: dict, sub_j: dict):
    # remove non-subtitile strings from json
    main_j = filter_subtitles(main_j)
    sub_j = filter_subtitles(sub_j)

    for key, value in sub_j.items():
        if key in main_j and value != "":
            main_val = main_j[key]
            if main_val != "":
                # when they are not empty strings
                main_j[key] = concat_subtitle(main_val, value)
    return main_j
