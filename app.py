from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

MENUS = ["제육볶음", "스시", "수제버거", "파스타", "타코", "샐러드"]
VOTE_TYPE = "희망 메뉴"
GET_TIMEOUT = 10    # 초
POST_TIMEOUT = 15   # 초 (연결 프로그램이 최대 10초 줄을 설 수 있어 조금 더 길게)
REFRESH_SECONDS = 10
KST = ZoneInfo("Asia/Seoul")

st.set_page_config(page_title="모두의 점심", layout="centered")


# ---------- 구글 시트 통신 ----------
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


# ---------- 오늘의 결과 계산 ----------
def parse_ts(value):
    """시각 칸을 한국 시간 기준 naive datetime으로 바꾼다. 읽을 수 없으면 None."""
    text = str(value).strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    try:  # 시트가 날짜 값으로 바꿔 ISO 형식으로 내려오는 경우
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(KST).replace(tzinfo=None)
    return dt


def tally_today(rows):
    """오늘(한국 날짜)의 '희망 메뉴' 기록에서 닉네임별 마지막 투표만 세어
    (메뉴별 득표 dict, 투표한 사람 수, 제외한 기록 수)를 돌려준다.
    시각이 같으면 시트에서 뒤에 있는 행을 마지막으로 본다."""
    header = [str(h).strip() for h in rows[0]]

    def col(name, default):
        return header.index(name) if name in header else default

    i_ts, i_member, i_menu, i_type = col("시각", 0), col("팀원", 1), col("메뉴", 2), col("구분", 3)

    def cell(row, i):
        return str(row[i]).strip() if i < len(row) else ""

    today = datetime.now(KST).date()
    last = {}      # 닉네임 -> ((시각, 행 번호), 메뉴)
    excluded = 0
    for idx, row in enumerate(rows[1:]):
        if cell(row, i_type) != VOTE_TYPE:
            continue
        ts = parse_ts(cell(row, i_ts))
        member = cell(row, i_member)
        if ts is None or not member:
            excluded += 1
            continue
        if ts.date() != today:
            continue
        key = (ts, idx)
        if member not in last or key >= last[member][0]:
            last[member] = (key, cell(row, i_menu))

    counts = {m: 0 for m in MENUS}
    voters = 0
    for _, menu in last.values():
        if menu in counts:
            counts[menu] += 1
            voters += 1
        else:
            excluded += 1
    return counts, voters, excluded


# ---------- 화면 ----------
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
        # 아래 결과 영역이 이 실행에서 시트를 새로 읽으므로 방금 투표가 바로 반영된다
        st.success(f"{nickname}님의 투표가 등록되었습니다")
    else:
        st.error("투표를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요")


@st.fragment(run_every=REFRESH_SECONDS)
def results_section():
    """결과 영역만 주기적으로 다시 읽는다. 입력 폼은 영향을 받지 않는다."""
    st.subheader("오늘의 투표 결과")
    st.button("결과 새로 읽기")  # 누르면 이 영역이 다시 실행되며 시트를 새로 읽는다

    rows, ok = fetch_records()
    if ok:
        st.session_state.last_read = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    last_read = st.session_state.get("last_read")
    if last_read:
        st.caption(f"마지막으로 읽은 시각 {last_read} (한국 시간, {REFRESH_SECONDS}초마다 자동 갱신)")

    if not ok:
        st.error("투표 기록을 불러오지 못했습니다. 잠시 후 자동으로 다시 시도하며, '결과 새로 읽기'로 바로 시도할 수도 있습니다")
        return

    counts, voters, excluded = tally_today(rows)

    if voters == 0:
        st.info("아직 투표가 없습니다")
    else:
        top = max(counts.values())
        winners = [m for m, c in counts.items() if c == top]
        st.metric("투표한 사람", f"{voters}명")
        if len(winners) > 1:
            st.success(f"공동 1위 ({top}표) - {', '.join(winners)}")
        else:
            st.success(f"1위 ({top}표) - {winners[0]}")

        df = pd.DataFrame({"메뉴": list(counts.keys()), "득표 수": list(counts.values())})
        st.bar_chart(df, x="메뉴", y="득표 수")
        st.dataframe(df, hide_index=True)

    if excluded:
        st.caption(f"형식이 맞지 않아 집계에서 제외한 기록이 {excluded}건 있습니다")

    with st.expander("전체 기록 보기"):
        header, body = rows[0], rows[1:]
        if body:
            st.dataframe(pd.DataFrame(body, columns=header).iloc[::-1], hide_index=True)
        else:
            st.write("기록이 없습니다")


results_section()
