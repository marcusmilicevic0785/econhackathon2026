import numpy as np
import pandas as pd

from econhack.nyc import clean_acs, nearby_counts, sphere_coordinates


def test_acs_sentinels_never_become_zero_or_values():
    actual = clean_acs(pd.Series(["-666666666", "0", "123", "bad"]))
    assert actual.isna().tolist() == [True, False, False, True]
    assert actual.iloc[1] == 0
    assert actual.iloc[2] == 123


def test_great_circle_radius_counts_and_invalid_coordinates():
    tracts = pd.DataFrame({"INTPTLAT": [40.75], "INTPTLONG": [-74.0]})
    facilities = pd.DataFrame({"latitude": [40.75, 40.754, 40.77, 40.75],
                               "longitude": [-74.0] * 4, "valid_coordinate": [True, True, True, False]})
    assert nearby_counts(tracts, facilities, 400).tolist() == [1]
    assert nearby_counts(tracts, facilities, 800).tolist() == [2]


def test_sphere_coordinates_have_unit_radius():
    coordinates = sphere_coordinates([40.75, 40.8], [-74, -73.9])
    np.testing.assert_allclose(np.linalg.norm(coordinates, axis=1), 1)
