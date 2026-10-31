#!/usr/bin/env python3
"""Verify the pinned ownership-only revision without generating maps or images."""

import argparse
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def read(revision, path):
    return git("show", revision + ":" + path)


def verify(previous, candidate, formatter):
    def formatted(text, path):
        return subprocess.check_output(
            [formatter, "--assume-filename=" + str(ROOT / path)], input=text, text=True)

    codec = read(previous, "libs/drape_frontend/metaline_data.hpp")
    codec = codec.replace("namespace df\n", "namespace feature::metalines\n")
    codec = codec.replace("namespace detail\n{\n", "").replace("}  // namespace detail\n", "")
    path = "libs/indexer/metaline_data.hpp"
    if formatted(codec, path) != read(candidate, path):
        raise ValueError("Codec changed beyond namespace ownership")

    path = "generator/metalines_builder.cpp"
    writer = read(previous, path).replace('#include "drape_frontend/metaline_data.hpp"\n\n', "")
    writer = writer.replace('#include "indexer/feature_processor.hpp"',
                            '#include "indexer/feature_processor.hpp"\n#include "indexer/metaline_data.hpp"')
    writer = writer.replace("df::kLegacyMetalinesSectionVersion", "metalines::kLegacyMetalinesSectionVersion")
    writer = writer.replace("df::kMetaLinesSectionVersion", "metalines::kMetaLinesSectionVersion")
    if formatted(writer, path) != read(candidate, path):
        raise ValueError("Writer changed beyond ownership and formatting")

    path = "libs/drape_frontend/read_metaline_task.cpp"
    reader = read(previous, path).replace(
        '#include "indexer/feature_decl.hpp"',
        '#include "indexer/feature_decl.hpp"\n#include "indexer/metaline_data.hpp"')
    for name in ("MetalineData", "ReadMetalines", "TryReadMetalineOffsets"):
        reader = reader.replace("detail::" + name, "feature::metalines::" + name)
    if formatted(reader, path) != read(candidate, path):
        raise ValueError("Reader changed beyond ownership")

    path = "libs/drape_frontend/read_metaline_task.hpp"
    header = read(previous, path).replace('#include "drape_frontend/metaline_data.hpp"\n\n', "")
    if header != read(candidate, path):
        raise ValueError("Renderer header changed beyond removing the transitive codec include")

    permitted = {"generator/metalines_builder.cpp", "libs/drape_frontend/read_metaline_task.cpp",
                 "libs/drape_frontend/read_metaline_task.hpp", "libs/drape_frontend/metaline_data.hpp",
                 "libs/indexer/metaline_data.hpp", "libs/drape_frontend/CMakeLists.txt",
                 "libs/indexer/CMakeLists.txt", "libs/drape_frontend/drape_frontend_tests/CMakeLists.txt",
                 "libs/indexer/indexer_tests/CMakeLists.txt",
                 "libs/drape_frontend/drape_frontend_tests/metaline_data_tests.cpp",
                 "libs/indexer/indexer_tests/metaline_data_tests.cpp"}
    changed = set(git("diff", "--name-only", previous, candidate, "--").splitlines())
    if changed - permitted:
        raise ValueError("Unrelated runtime sources or assets changed: " + str(sorted(changed - permitted)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clang-format", default="clang-format")
    args = parser.parse_args()
    record = json.loads(Path(__file__).with_name("code-quality-review.json").read_text())
    for item in record["comparisons"]:
        verify(item["previous"], item["candidate"], args.clang_format)
        print("PASS", item["previous"][:10], "->", item["candidate"][:10])
    formatting = Path(__file__).with_name("merge-readiness-format-audit.json")
    if formatting.exists():
        for item in json.loads(formatting.read_text())["comparisons"]:
            previous, candidate = item["previous"], item["candidate"]
            changed = git("diff", "--name-only", previous, candidate, "--").splitlines()
            if changed != item["changed_paths"]:
                raise ValueError("Formatting audit path list changed")
            for path in changed:
                if not path.endswith((".cpp", ".hpp")):
                    raise ValueError("Non-C++ changes in formatting revision")
                expected = subprocess.check_output(
                    [args.clang_format, "--assume-filename=" + str(ROOT / path)],
                    input=read(previous, path), text=True)
                if expected != read(candidate, path):
                    raise ValueError("Change is not exact formatter output: " + path)
            print("PASS formatting", previous[:10], "->", candidate[:10])


if __name__ == "__main__":
    main()
