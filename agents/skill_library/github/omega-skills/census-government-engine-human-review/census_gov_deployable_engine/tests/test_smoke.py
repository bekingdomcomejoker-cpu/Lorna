from census_engine.engine import CensusEngine


def test_manifest_counts():
    engine = CensusEngine()
    manifest = engine.manifest()
    assert manifest["bucket_files"]["canon_core"]["records"] == 357


def test_report_builds():
    report = CensusEngine().build_report()
    assert report.total_records > 0
    assert "canon_core" in report.bucket_counts
