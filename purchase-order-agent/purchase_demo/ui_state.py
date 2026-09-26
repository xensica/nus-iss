"""Session actions shared by the app and store setup."""
import streamlit as st
from .catalogue import DEFAULTS, analyse
from .workspace import clear_event_overrides

S = st.session_state

def recalculate():
    S.analysis=analyse(S.dataset,S.settings,S.overrides);S.pop('briefing',None)
def reset_selection():
    S.selection_version=S.get('selection_version',0)+1
    S.selected=[pid for pid,r in S.analysis['results'].items() if r['plan']['status']=='ready']
def load_data(data,as_of):
    S.dataset=data;S.settings=dict(DEFAULTS,date=as_of);S.overrides={}
    S.pop('event_report',None);S.pop('evaluation',None);recalculate();reset_selection()

def change_location(location):
    S.location=dict(location);S.pop('event_report',None)
    S.overrides=clear_event_overrides(S.overrides);recalculate();reset_selection()

