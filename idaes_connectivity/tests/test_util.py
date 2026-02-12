import os
import re
import time
import pytest

from . import example_flowsheet
from idaes_connectivity import util


@pytest.fixture
def flowsheet():
    return example_flowsheet.build()


def test_get_stream_display_values(flowsheet):
    tbl = flowsheet.fs.stream_table()
    dict_spec = {
        "temperature": ("kelvin", ".3g"),
        re.compile("conc_mass_comp.*"): ("kg/m^3", ".4g"),
    }
    simple_spec = {"temperature": ".3g", "~conc.mass.comp.*": ".4g"}
    r1 = util.get_stream_display_values(tbl, dict_spec)
    r2 = util.get_stream_display_values(tbl, simple_spec)
    assert r1 == r2


def test_file_server(tmpdir):
    server = util.FileServer(run_dir=tmpdir)
    key = str(int(time.time()))
    print(f"key={key}")
    server.start(".", client_key=key)
    assert server.pid > 0
    assert server.port > 0
    server.kill_all()
