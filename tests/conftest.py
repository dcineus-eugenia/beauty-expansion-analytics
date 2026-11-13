import pytest

from beauty_expansion import config


@pytest.fixture
def has_outputs():
    """Skip tests that need the pipeline outputs (CI runs without network, so without them)."""
    if not (config.PROCESSED / "kpis_by_country.csv").exists():
        pytest.skip("no pipeline outputs: run `python -m beauty_expansion.pipeline` first")
