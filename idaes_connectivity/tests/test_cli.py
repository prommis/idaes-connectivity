"""
Tests for command-line interface module.
"""

import pytest
from idaes_connectivity.cli import main
from idaes_connectivity.tests.example_flowsheet_data import (
    example_csv,
    example_mermaid,
    example_d2,
)

# avoid warnings about unused imports
_1, _2, _3 = example_csv, example_d2, example_mermaid

ex_mod = "idaes_connectivity.tests.example_flowsheet"
ex_csv = "example_flowsheet.csv"


@pytest.mark.unit
def test_usage():
    assert 0 == main(["--usage"])


@pytest.mark.unit
def test_help():
    with pytest.raises(SystemExit):
        main(["-h"])
    with pytest.raises(SystemExit):
        main(["--help"])


run_matrix = []
for source in "file", "module":
    for fmt in ("csv", "mermaid", "d2"):
        for fs_name in (None, "fs"):
            for build_func in (None, "build"):
                for labels in (False, True):
                    for direction in (None, "LR", "TD"):
                        for verbosity in (None, "v", "vv", "vvv"):
                            run_matrix.append(
                                (
                                    source,
                                    fmt,
                                    fs_name,
                                    build_func,
                                    labels,
                                    direction,
                                    verbosity,
                                )
                            )


@pytest.mark.unit
@pytest.mark.parametrize(
    "source_type,output_format,fs_name,build_func,labels,direction,verbosity",
    run_matrix,
)
def test_cli(
    tmp_path,
    example_csv,
    source_type,
    output_format,
    fs_name,
    build_func,
    labels,
    direction,
    verbosity,
):
    args = []
    if source_type == "file":
        input_path = tmp_path / "test.csv"
        with open(input_path, "w") as f:
            f.write("\n".join(example_csv))
        args.append(str(input_path))
    elif source_type == "module":
        input_module = "idaes_connectivity.tests.example_flowsheet"
        args.append(input_module)
    else:
        raise ValueError(f"Bad test parameter: source_type='{source_type}'")
    output_path = tmp_path / "output.{output_format}"
    args.extend(["-O", str(output_path), "--to", output_format])
    if fs_name is not None:
        args.extend(["--fs", fs_name])
    if build_func is not None:
        args.extend(["--build", build_func])
    if labels:
        args.append("--labels")
    if direction is not None:
        args.extend(["--direction", direction])
    if verbosity is not None:
        args.append(f"-{verbosity}")
    assert 0 == main(args)
    assert output_path.exists()
