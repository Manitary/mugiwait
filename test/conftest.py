from typing import Generator

import pytest

from mugiclient import AssetType, Mugiwait


@pytest.fixture
def mugi() -> Generator[Mugiwait, None, None]:
    client = Mugiwait()
    client.asset_type = AssetType.FILE
    yield client
