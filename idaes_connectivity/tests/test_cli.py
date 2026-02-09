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
return_code = 0  # Should succeed
fs_name, build_func, labels, direction = None, None, False, None
# multiplicative
for source in "file", "module":
    for fmt in ("csv", "mermaid", "d2"):
        for verbosity in (None, "v", "vv", "vvv"):
            for infer_output in (True, False):
                for infer_type in (True, False):
                    run_matrix.append(
                        (
                            return_code,
                            source,
                            fmt,
                            fs_name,
                            build_func,
                            labels,
                            direction,
                            verbosity,
                            infer_output,
                            infer_type,
                        )
                    )
# additive (mostly)
for infer_type in (True, False):
    source, fmt, verbosity, infer_output = "module", "csv", None, False
    for fs_name in (None, "fs"):
        run_matrix.append(
            (
                return_code,
                source,
                fmt,
                fs_name,
                build_func,
                labels,
                direction,
                verbosity,
                infer_output,
                infer_type,
            )
        )
    for build_func in (None, "build"):
        run_matrix.append(
            (
                return_code,
                source,
                fmt,
                fs_name,
                build_func,
                labels,
                direction,
                verbosity,
                infer_output,
                infer_type,
            )
        )
    for labels in (False, True):
        for fmt in ("csv", "mermaid", "d2"):
            for direction in (None, "LR", "TD"):
                run_matrix.append(
                    (
                        return_code,
                        source,
                        fmt,
                        fs_name,
                        build_func,
                        labels,
                        direction,
                        verbosity,
                        infer_output,
                        infer_type,
                    )
                )


def set_arg(pos, value, retcode, source="module"):
    entry = list(run_matrix[0])
    entry[0] = retcode
    entry[1] = source
    entry[-1] = False
    entry[pos] = value
    return entry


# bad args
for i in (2, 6):
    run_matrix.append(set_arg(i, "foobar", -1))
run_matrix.append(set_arg(1, "file-missing", 2))
# processing error
for i in (3, 4):
    run_matrix.append(set_arg(i, "foobar", 1))
# bad input file
run_matrix.append(set_arg(1, "file-bad", 1))
# bad model
run_matrix.append(set_arg(1, "module-missing", 1))


@pytest.mark.unit
@pytest.mark.parametrize(
    "return_code,source_type,output_format,fs_name,"
    "build_func,labels,direction,verbosity,infer_output,infer_type",
    run_matrix,
)
def test_cli(
    tmp_path,
    example_csv,
    return_code,
    source_type,
    output_format,
    fs_name,
    build_func,
    labels,
    direction,
    verbosity,
    infer_output,
    infer_type,
):
    args = []
    if source_type.startswith("file"):
        if source_type.endswith("-bad"):
            input_path = tmp_path / "testbad.csv"
            with open(input_path, "w") as f:
                f.write("garbage!\n")
        elif source_type.endswith("-missing"):
            input_path = tmp_path / "missing"
        else:
            input_path = tmp_path / "test.csv"
            with open(input_path, "w") as f:
                f.write("\n".join(example_csv))
        args.append(str(input_path))
        if not infer_type:
            args.extend(["--type", "csv"])
    elif source_type.startswith("module"):
        if source_type.endswith("-missing"):
            input_module = "idaes_connectivity.no.such.module"
        else:
            input_module = "idaes_connectivity.tests.example_flowsheet"
        args.append(input_module)
        if not infer_type:
            args.extend(["--type", "module"])
    else:
        raise ValueError(f"Bad test parameter: source_type='{source_type}'")
    if infer_output:
        if source_type == "file" and output_format != "csv":
            output_path = None
        else:
            return  # skip infer_output=True cases
    else:
        output_path = tmp_path / f"output.{output_format}"
        args.extend(["-O", str(output_path)])
    args.extend(["--to", output_format])
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
    print(f"run cli.main with args: {args}")
    if return_code == -1:
        with pytest.raises(SystemExit):
            main(args)
    else:
        assert return_code == main(args)
    if return_code == 0 and output_path is not None:
        assert output_path.exists()
