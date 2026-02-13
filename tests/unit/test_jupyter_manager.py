from src.web.jupyter_manager import JupyterManager


def test_jupyter_manager_health_disabled():
    manager = JupyterManager(enabled=False)
    out = manager.health_check()
    assert out["status"] == "disabled"
    assert out["enabled"] is False


def test_jupyter_manager_start_disabled_returns_false():
    manager = JupyterManager(enabled=False)
    assert manager.start() is False
    assert manager.is_alive() is False


def test_jupyter_manager_provisions_templates(tmp_path):
    seed = tmp_path / "seed"
    seed.mkdir(parents=True)
    (seed / "sample.ipynb").write_text("{}", encoding="utf-8")
    notebook_root = tmp_path / "notebooks"

    manager = JupyterManager(enabled=False, notebook_dir=str(notebook_root), template_seed_dir=str(seed))
    copied = manager.provision_templates()
    assert copied == 1
    assert (notebook_root / "templates" / "sample.ipynb").exists()
