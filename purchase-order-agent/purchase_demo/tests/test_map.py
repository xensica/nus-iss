import pytest
from purchase_demo.ui_location import clicked_location, location_map

@pytest.mark.parametrize('point', [None, {}, {'lat':float('nan'),'lng':103.8}, {'lat':51,'lng':0}])
def test_invalid_map_points(point):
    with pytest.raises(ValueError): clicked_location(point)

def test_radius_and_marker_match_selected_point():
    point=clicked_location({'lat':1.29,'lng':103.85})
    html=location_map(point,2).get_root().render()
    assert '2000' in html
    assert '[1.29, 103.85]' in html
    assert 'OpenStreetMap' in html
