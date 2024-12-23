"""
Tests for command-line interface module.
"""

import pytest
from idaes_connectivity.cli import main

ex_mod = "idaes_connectivity.tests.example_flowsheet"
ex_csv = "example_flowsheet.csv"


@pytest.mark.unit
@pytest.mark.parametrize(
    "args,code",
    [
        (["--usage"], 0),
        (
            [
                ex_mod,
                "-O",
                "{path}/" + ex_csv,
                "--to",
                "csv",
            ],
            0,
        ),
        ([ex_mod, "-O", "-", "--to", "csv"], 0),
        (
            [
                ex_mod,
                "-tmodule",
                "-O",
                "{path}/" + ex_csv,
                "--to",
                "csv",
            ],
            0,
        ),
        (["invalidmodule.1.name"], 2),
        (
            ["prommis.me.this"],
            1,
        ),
        (["{path}/" + ex_csv], 0),
        (["{path}/" + ex_csv, "-v"], 0),
        (["{path}/" + ex_csv, "-vv"], 0),
        (["{path}/" + ex_csv, "-q"], 0),
        (["{path}/" + ex_csv, "-q", "-v"], 0),
        (["{path}/output.txt"], 0),
        (["{path}/" + ex_csv, "-tcsv"], 0),
        (
            [
                "{path}/" + ex_csv,
                "--to",
                "mermaid",
                "--output-file",
                "-",
            ],
            0,
        ),
        (["{path}/" + ex_csv, "--to", "mermaid", "--labels"], 0),
        (["{path}/nope.csv", "--to", "mermaid", "--labels"], 2),
        (["{path}/nope.csv", "--to", "mermaid", "--type", "csv"], 2),
        (["{path}/nope.mmd", "--to", "mermaid", "--labels"], 2),
        (["--labels"], 2),
        (["{path}/junk.csv", "--to", "csv"], 1),
    ],
)
def test_main(tmp_path, args, code):
    from_model = args and (args[0] == ex_mod)
    if not from_model:
        csv_file = tmp_path / ex_csv
        with csv_file.open("w") as f:
            for line in uky_csv_data:
                f.write(line)
                f.write("\n")
        csv_txt_file = tmp_path / "uky_conn.txt"
        with csv_txt_file.open("w") as f:
            for line in uky_csv_data:
                f.write(line)
                f.write("\n")
        (tmp_path / "junk.csv").open(mode="w").write("This,is,some\njunk\n")
    for i in range(len(args)):
        if "{" in args[i]:
            args[i] = args[i].format(path=tmp_path)
    print(f"Run CLI with args: {args}")
    ret_code = main(command_line=args)
    assert ret_code == code
