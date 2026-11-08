import pytest

import base_de_donnees


@pytest.fixture(autouse=True)
def base_de_test(tmp_path, monkeypatch):
    monkeypatch.setattr(base_de_donnees, "chemin_base", tmp_path / "test.db")
