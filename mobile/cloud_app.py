"""Private cloud entry point. Missing credentials block all feed/research access."""
import hmac
from pathlib import Path
import runpy
import sys
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title='BTC/ETH Private Watch', page_icon='⚠️')
try:
    password = st.secrets.get('dashboard_access_password', '')
except st.errors.StreamlitSecretNotFoundError:
    password = ''
if not isinstance(password, str) or len(password) < 20:
    st.error('Dashboard locked. Administrator must configure a strong access password in hosting secrets.')
    st.stop()

if not st.session_state.get('dashboard_authenticated', False):
    st.title('Private BTC / ETH dashboard')
    with st.form('dashboard_login', clear_on_submit=True):
        supplied = st.text_input('Dashboard password', type='password')
        submitted = st.form_submit_button('Unlock read-only dashboard')
    if submitted:
        if hmac.compare_digest(supplied.encode(), password.encode()):
            st.session_state['dashboard_authenticated'] = True
            st.rerun()
        else:
            st.error('Access denied.')
    st.stop()

if st.button('Lock dashboard'):
    st.session_state.pop('dashboard_authenticated', None)
    st.rerun()
from analysis import NO_TRADE_HOLD
if NO_TRADE_HOLD is not True:
    st.error('Safety lock disabled. Dashboard blocked.')
    st.stop()

st.warning('Cloud storage is temporary. Observations here are not a permanent research archive. No background collection guarantee.')
runpy.run_path(str(ROOT / 'mobile_app.py'), run_name='__main__')
