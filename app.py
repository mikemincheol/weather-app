import streamlit as st

MENUS = ["제육볶음", "스시", "수제버거", "파스타", "타코", "샐러드"]

st.set_page_config(page_title="모두의 점심", layout="centered")

# 접속해 있는 동안만 유지되는 투표 목록
if "votes" not in st.session_state:
    st.session_state.votes = []

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
    else:
        st.session_state.votes.append({"nickname": nickname, "menu": menu})
        st.success(f"{nickname}님의 투표가 등록되었습니다")

st.subheader(f"투표 현황 ({len(st.session_state.votes)}표)")

if st.session_state.votes:
    for i, vote in enumerate(reversed(st.session_state.votes), start=1):
        st.write(f"{i}. **{vote['nickname']}** - {vote['menu']}")
else:
    st.info("아직 투표가 없습니다. 첫 번째로 투표해 보세요")
