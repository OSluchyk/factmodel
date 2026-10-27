import pytest

from tests.install.wheel import Installed, install


@pytest.fixture(scope="session")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Installed:
    return install(tmp_path_factory.mktemp("wheel"))
