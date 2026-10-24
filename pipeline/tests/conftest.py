import pytest

from ccpipe.paths import data_file


@pytest.fixture(scope="session")
def cc_csv():
    path = data_file("carecompass_csv")
    if not path.exists():
        pytest.skip("CareCompass CSV not available")
    return path
