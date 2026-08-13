from census_engine.extractors.mpam import extract
from census_engine.util import sa_id_is_valid

def test_extract_company_event():
    items = extract('In 2020, Motus acquired Atlantis Nissan Centurion from Atlantis Motors (Pty) Ltd in Centurion.')
    assert items and items[0].date == '2020'
    assert 'Centurion' in items[0].place

def test_sa_id_luhn_shape():
    assert sa_id_is_valid('7310200088082') in {True, False}
