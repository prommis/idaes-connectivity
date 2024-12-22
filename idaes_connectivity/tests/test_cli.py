"""
Tests for command-line interface module.
"""

import pytest
from idaes_connectivity.cli import main
from idaes_connectivity.tests import connectivity_data as cdata

# this roundabout method avoids pylint warnings
uky_csv_data, uky_mermaid_data = cdata.uky_csv, cdata.uky_mermaid


@pytest.mark.unit
@pytest.mark.parametrize(
    "args,code",
    [
        (["--usage"], 0),
        # TODO: Replace with flowsheet not dependent on Prommis
        #        (["prommis.uky.uky_flowsheet", "-O", "{path}/uky_conn.csv", "--to", "csv"], 0),
        #        (["prommis.uky.uky_flowsheet", "-O", "-", "--to", "csv"], 0),
        #        (
        #            [
        #                "prommis.uky.uky_flowsheet",
        #                "-tmodule",
        #                "-O",
        #                "{path}/uky_conn.csv",
        #                "--to",
        #                "csv",
        #            ],
        #            0,
        #        ),
        (["invalidmodule.1.name"], 2),
        (
            ["prommis.me.this"],
            1,
        ),
        (["{path}/uky_conn.csv"], 0),
        (["{path}/uky_conn.csv", "-v"], 0),
        (["{path}/uky_conn.csv", "-vv"], 0),
        (["{path}/uky_conn.csv", "-q"], 0),
        (["{path}/uky_conn.csv", "-q", "-v"], 0),
        (["{path}/uky_conn.txt"], 0),
        (["{path}/uky_conn.csv", "-tcsv"], 0),
        (["{path}/uky_conn.csv", "--to", "mermaid", "--output-file", "-"], 0),
        (["{path}/uky_conn.csv", "--to", "mermaid", "--labels"], 0),
        (["{path}/nope.csv", "--to", "mermaid", "--labels"], 2),
        (["{path}/nope.csv", "--to", "mermaid", "--type", "csv"], 2),
        (["{path}/nope.mmd", "--to", "mermaid", "--labels"], 2),
        (["--labels"], 2),
        (["{path}/junk.csv", "--to", "csv"], 1),
    ],
)
def test_main(tmp_path, args, code, uky_csv_data):
    from_model = args and "uky_flowsheet" in args[0]
    if not from_model:
        csv_file = tmp_path / "uky_conn.csv"
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
