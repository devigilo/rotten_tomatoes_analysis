import pytest
from batch_processor import extract_release_date_from_filename, extract_movie_name_from_filename


def test_extract_release_date():
    name = "Top_Gun_Maverick_2022-05-27_20250531_235717.csv"
    assert extract_release_date_from_filename(name) == "2022-05-27"


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("Movie_Title_2024-01-01_20240101_000000.csv", "Movie Title"),
        ("Another_Movie_2022-12-12_20221212_121212.csv", "Another Movie"),
    ],
)
def test_extract_movie_name(filename, expected):
    assert extract_movie_name_from_filename(filename) == expected
