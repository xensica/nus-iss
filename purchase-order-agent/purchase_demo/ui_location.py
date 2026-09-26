"""Search or click a map, then explicitly confirm the store location."""
import math
import folium
import streamlit as st
from streamlit_folium import st_folium
from .local_context import search_places
from .ui_state import change_location


def clicked_location(point):
    """Validate untrusted component coordinates before storing them."""
    try:
        lat, lon = float(point['lat']), float(point['lng'])
    except (KeyError, TypeError, ValueError):
        raise ValueError('Choose a point on the map.') from None
    if not (math.isfinite(lat) and math.isfinite(lon) and 1.1 <= lat <= 1.5 and 103.5 <= lon <= 104.2):
        raise ValueError('Choose a location in the Singapore map area.')
    return dict(label=f'Selected map point ({lat:.5f}, {lon:.5f})', lat=lat, lon=lon,
                source='User-selected OpenStreetMap point')


def location_map(location, radius):
    center = [location['lat'], location['lon']]
    result = folium.Map(location=center, zoom_start=14, tiles='OpenStreetMap', control_scale=True)
    folium.Marker(center, tooltip='Proposed store location', icon=folium.Icon(color='green')).add_to(result)
    folium.Circle(center, radius=radius * 1000, color='#28785f', weight=2,
                  fill=True, fill_opacity=.08, tooltip=f'{radius:g} km search radius').add_to(result)
    return result


def location_setup():
    S = st.session_state
    st.subheader('Pin your store')
    st.caption('Search a mall or street, or click the map. Confirm the pin below to update your plan.')
    with st.form('location_search'):
        query = st.text_input('Mall, street or postal code', value='Marina Bay Sands', max_chars=180)
        find = st.form_submit_button('Find store location')
    if find:
        S.pop('place_matches', None)
        try:
            with st.spinner('Finding matching places…'):
                S.place_matches = search_places(query)
            if not S.place_matches:
                st.info('No match found. You can still choose a point on the map.')
        except ValueError as error:
            st.warning(str(error))
    if S.get('place_matches'):
        index = st.selectbox('Matching places', range(len(S.place_matches)),
                             format_func=lambda i: S.place_matches[i]['label'])
        if st.button('Show this place on the map'):
            S.map_candidate = dict(S.place_matches[index])
            S.map_revision = S.get('map_revision', 0) + 1
            S.pop('map_last_click', None)
            S.pop('map_location_label', None)
            st.rerun()
    candidate = S.get('map_candidate') or S.location or dict(
        label='Near Marina Bay Sands', lat=1.2834, lon=103.8607)
    output = st_folium(location_map(candidate, S.radius), height=350,
                       use_container_width=True, returned_objects=['last_clicked'],
                       key=f'store_map_{S.get("map_revision", 0)}')
    point = (output or {}).get('last_clicked')
    if point and point != S.get('map_last_click'):
        S.map_last_click = point
        try:
            S.map_candidate = clicked_location(point)
            S.pop('map_location_label', None)
            st.rerun()
        except ValueError as error:
            st.warning(str(error))
    label = st.text_input('Name this location', value=candidate['label'],
                          max_chars=180, key='map_location_label')
    st.caption(f"Proposed pin: {candidate['lat']:.5f}, {candidate['lon']:.5f} · radius {S.radius:g} km")
    if st.button('Use this store location', type='primary', width='stretch'):
        change_location(dict(candidate, label=label.strip() or candidate['label']))
        S.pop('place_matches', None)
        S.map_candidate = dict(S.location)
        S.location_saved = True
        st.rerun()
    if S.pop('location_saved', False):
        st.success('Store location saved. Nearby-event scenarios have been reset for this location.')
    if S.location:
        st.caption('Saved location: ' + S.location['label'])
    st.caption('Map © OpenStreetMap contributors. Search uses Photon. Map tiles and search need internet. Distance is straight-line.')
    with st.expander('Enter coordinates if the map cannot load'):
        with st.form('coordinates'):
            a, b = st.columns(2)
            lat = a.number_input('Latitude', 1.1, 1.5, float(candidate['lat']), format='%.6f')
            lon = b.number_input('Longitude', 103.5, 104.2, float(candidate['lon']), format='%.6f')
            if st.form_submit_button('Save map point'):
                location = clicked_location(dict(lat=lat, lng=lon))
                change_location(location)
                S.map_candidate = location
                S.map_revision = S.get('map_revision', 0) + 1
                S.pop('map_last_click', None)
                S.pop('map_location_label', None)
                S.location_saved = True
                st.rerun()
