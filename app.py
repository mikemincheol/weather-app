import pandas as pd
import requests
import streamlit as st

MENUS = ["제육볶음", "스시", "수제버거", "파스타", "타코", "샐러드"]
VOTE_TYPE = "희망 메뉴"
GET_TIMEOUT = 10   # 초
POST_TIMEOUT = 15  # 초 (연결 프로그램이 최대 10초 줄을 설 수 있어 조금 더 길게)

st.set_page_config(page_title="모두의 점심", layout="centered")


def get_sheet_url():
    """secrets에서 주소를 가져온다. 없으면 None."""
    try:
        url = st.secrets["SHEET_URL"]
    except Exception:
        return None
    return url or None


def fetch_records():
    """시트 전체 기록을 불러온다. 성공하면 (행 목록, True), 실패하면 (None, False).
    예외 내용에는 주소가 들어 있을 수 있어 화면에 내보내지 않는다."""
    url = get_sheet_url()
    if not url:
        return None, False
    try:
        resp = requests.get(url, timeout=GET_TIMEOUT)
        resp.raise_for_status()
        rows = resp.json()
    except (requests.RequestException, ValueError):
        return None, False
    # 연결 프로그램 오류는 {"ok": false, ...} 처럼 목록이 아닌 형태로 온다
    if not isinstance(rows, list) or not rows or not all(isinstance(r, list) for r in rows):
        return None, False
    return rows, True


def post_vote(member, menu):
    """투표 한 건을 저장한다. 응답의 ok가 True일 때만 True."""
    url = get_sheet_url()
    if not url:
        return False
    payload = {"data": {"member": member, "menu": menu, "type": VOTE_TYPE}}
    try:
        resp = requests.post(url, json=payload, timeout=POST_TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
    except (requests.RequestException, ValueError):
        return False
    return isinstance(result, dict) and result.get("ok") is True


def reload_records():
    rows, ok = fetch_records()
    st.session_state.records = rows
    st.session_state.load_failed = not ok


if "records" not in st.session_state:
    reload_records()

st.title("모두의 점심")
st.caption("닉네임과 먹고 싶은 메뉴를 고르고 투표해 주세요")

with st.form("vote_form", clear_on_submit=True):
    nickname = st.text_input("닉네임", max_chars=20, placeholder="예) 점심요정")
    menu = st.radio("먹고 싶은 메뉴", MENUS, horizontal=True)
    submitted = st.form_submit_button("투표")

if submitted:
    nickname = nickname.strip()
    if not nickname:
        st.warning("닉네임을 입력해 주세요")
    elif post_vote(nickname, menu):
        st.success(f"{nickname}님의 투표가 등록되었습니다")
        reload_records()
    else:
        st.error("투표를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요")

st.subheader("투표 현황")

if st.button("결과 새로 읽기"):
    reload_records()

rows = st.session_state.records
if st.session_state.load_failed or rows is None:
    st.error("투표 기록을 불러오지 못했습니다. '결과 새로 읽기'를 눌러 다시 시도해 주세요")
else:
    header, body = rows[0], rows[1:]
    if body:
        df = pd.DataFrame(body, columns=header).iloc[::-1]  # 최근 투표가 위로
        st.caption(f"총 {len(df)}표")
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("아직 투표가 없습니다. 첫 번째로 투표해 보세요")
