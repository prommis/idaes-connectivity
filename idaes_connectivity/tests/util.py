"""
Test utility.
"""

import logging

from tempfile import NamedTemporaryFile
from shutil import copyfile
from idaes_connectivity.base import Connectivity, CSV, Mermaid, D2

TAB = "    "


def init_logger(logger):
    _h = logging.StreamHandler()
    _h.setFormatter(
        logging.Formatter("{asctime} {levelname} {name} - {message}", style="{")
    )
    logger.addHandler(_h)


def generate(
    conn: Connectivity = None, filename: str = None, log: logging.Logger = None
):
    """
    Generate/replace a source code file with pytest
    fixtures containing data for a given connectivity.
    """
    data = {
        "csv": CSV(conn).write(None),
        "mermaid": Mermaid(conn).write(None),
        "d2": D2(conn).write(None),
    }
    outfile = NamedTemporaryFile("w", encoding="utf-8")
    with open(filename, "r") as infile:
        fixture_name, in_fixture, wrote_data = None, False, False
        for line in infile:
            if in_fixture:
                if wrote_data:
                    rline = line.rstrip()
                    if rline == "" or rline.endswith("]"):
                        in_fixture, wrote_data = False, False
                elif line.startswith("def"):
                    func = line.split(" ")[1].split("(")[0]
                    fixture_name = func.split("_")[-1]
                    outfile.write(line)
                    log.debug(f"add {fixture_name} data")
                elif line.startswith(f"{TAB}return"):
                    outfile.write(f"{TAB}return [\n")
                    for row in data[fixture_name].split("\n"):
                        row = row.rstrip()
                        if row:
                            outfile.write(f'{TAB}{TAB}"{row}",\n')
                    outfile.write(f"{TAB}]\n")
                    wrote_data = True
            else:
                outfile.write(line)
                if line.startswith("@pytest.fixture"):
                    in_fixture = True
    outfile.flush()
    outfile.seek(0)
    log.info(f"overwrite '{infile.name}'")
    copyfile(outfile.name, infile.name)

    return 0
