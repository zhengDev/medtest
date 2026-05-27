import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tempfile
import time
import streamlit as st

from core.pipeline.question_pipeline_v2 import (
    import_questions_v2, preview_questions,
    list_papers, list_groups, get_questions, get_question_count_v2,
    start_practice_session, submit_answer, complete_session,
    get_session_history, get_store,
)
from core.question_bank.models import (
    Q_TYPE_SINGLE, Q_TYPE_MULTI, Q_TYPE_JUDGE, Q_TYPE_FILL, Q_TYPE_ESSAY,
    Q_TYPE_LABELS,
)
from config.settings import SUPPORTED_QUESTION_EXTENSIONS, MAX_UPLOAD_MB

st.set_page_config(page_title="题目练习", page_icon="📚", layout="wide")
st.title("📚 题目练习")

tab1, tab2, tab3, tab4 = st.tabs(["📥 导入试卷", "✏️ 题目练习", "📋 题库管理", "📊 练习记录"])

# ══════════════════════════════════════════════════════
# Tab 1：导入试卷
# ══════════════════════════════════════════════════════
with tab1:
    st.subheader("上传并解析试卷")

    uploaded = st.file_uploader(
        f"支持格式：{', '.join(SUPPORTED_QUESTION_EXTENSIONS)}，最大 {MAX_UPLOAD_MB}MB",
        type=[e.lstrip(".") for e in SUPPORTED_QUESTION_EXTENSIONS],
    )

    if uploaded:
        if uploaded.size > MAX_UPLOAD_MB * 1024 * 1024:
            st.error(f"文件超过 {MAX_UPLOAD_MB}MB 限制")
        else:
            paper_name = st.text_input(
                "试卷名称（留空则使用文件名）",
                placeholder=uploaded.name,
                key="import_paper_name",
            )

            col_preview, col_import = st.columns(2)

            with col_preview:
                if st.button("🔍 解析预览", use_container_width=True):
                    with tempfile.NamedTemporaryFile(
                        suffix=Path(uploaded.name).suffix, delete=False
                    ) as tmp:
                        tmp.write(uploaded.read())
                        tmp_path = Path(tmp.name)
                    uploaded.seek(0)
                    with st.spinner("正在解析..."):
                        preview = preview_questions(
                            tmp_path, source_name=uploaded.name, max_count=10
                        )
                    tmp_path.unlink(missing_ok=True)
                    st.session_state["import_preview"] = preview

            with col_import:
                if st.button("✅ 确认入库", use_container_width=True, type="primary"):
                    with tempfile.NamedTemporaryFile(
                        suffix=Path(uploaded.name).suffix, delete=False
                    ) as tmp:
                        tmp.write(uploaded.read())
                        tmp_path = Path(tmp.name)
                    uploaded.seek(0)
                    with st.spinner("正在导入..."):
                        inserted, skipped = import_questions_v2(
                            tmp_path,
                            source_name=uploaded.name,
                            paper_name=paper_name or uploaded.name,
                        )
                    tmp_path.unlink(missing_ok=True)
                    st.session_state.pop("import_preview", None)
                    if inserted > 0:
                        st.success(f"导入完成：新增 **{inserted}** 道题，跳过重复 **{skipped}** 道")
                    else:
                        st.warning(f"未识别到新题目（跳过重复 {skipped} 道）")

    # 预览展示
    preview = st.session_state.get("import_preview")
    if preview:
        st.divider()
        st.caption(f"预览前 {len(preview)} 道题（未入库）")
        for i, q in enumerate(preview, 1):
            with st.expander(f"[{q.type_label}] 第{i}题：{q.stem[:40]}…"):
                st.markdown(f"**题干：** {q.stem}")
                if q.options:
                    for letter in sorted(q.options):
                        marker = "✅ " if letter == q.answer.upper() else ""
                        st.markdown(f"　{marker}{letter}. {q.options[letter]}")
                if q.answer:
                    st.markdown(f"**答案：** `{q.answer}`")
                if q.explanation:
                    st.markdown(f"**解析：** {q.explanation}")


# ══════════════════════════════════════════════════════
# Tab 2：题目练习
# ══════════════════════════════════════════════════════
with tab2:
    # 初始化 session_state
    for key, default in [
        ("practice_phase", "config"),
        ("practice_session_id", None),
        ("practice_questions", []),
        ("practice_index", 0),
        ("practice_submitted", set()),
        ("practice_results", {}),
        ("practice_user_answers", {}),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    phase = st.session_state["practice_phase"]

    # ── 配置页 ────────────────────────────────────────
    if phase == "config":
        st.subheader("练习配置")
        total_count = get_question_count_v2()
        if total_count == 0:
            st.info("题库为空，请先在「导入试卷」Tab 上传题目。")
        else:
            st.caption(f"题库共 {total_count} 道题")

            c1, c2 = st.columns(2)
            with c1:
                source_option = st.radio(
                    "练习来源",
                    ["全部题库", "指定试卷", "指定分组"],
                    horizontal=True,
                    key="cfg_source_option",
                )
            with c2:
                q_type_option = st.selectbox(
                    "题型过滤",
                    ["全部题型"] + list(Q_TYPE_LABELS.values()),
                    key="cfg_q_type",
                )

            source_type = "all"
            source_id = None

            if source_option == "指定试卷":
                papers = list_papers()
                if papers:
                    chosen = st.selectbox(
                        "选择试卷",
                        papers,
                        format_func=lambda p: f"{p['name']} ({p['total_count']}题)",
                        key="cfg_paper",
                    )
                    source_type = "paper"
                    source_id = chosen["id"]
                else:
                    st.warning("暂无试卷，请先导入。")

            elif source_option == "指定分组":
                groups = list_groups()
                if groups:
                    chosen = st.selectbox(
                        "选择分组",
                        groups,
                        format_func=lambda g: f"{g['name']} ({g['question_count']}题)",
                        key="cfg_group",
                    )
                    source_type = "group"
                    source_id = chosen["id"]
                else:
                    st.warning("暂无分组，请在「题库管理」中创建。")

            q_type_map = {v: k for k, v in Q_TYPE_LABELS.items()}
            selected_type = q_type_map.get(q_type_option)

            avail = get_question_count_v2(
                paper_id=source_id if source_type == "paper" else None,
                group_id=source_id if source_type == "group" else None,
            )
            max_q = max(1, avail)
            question_count = st.slider(
                "题目数量",
                min_value=1,
                max_value=min(max_q, 50),
                value=min(10, max_q),
                key="cfg_count",
            )

            if st.button("🚀 开始练习", type="primary", use_container_width=True):
                sid, qs = start_practice_session(
                    source_type=source_type,
                    source_id=source_id,
                    question_count=question_count,
                    q_type=selected_type,
                )
                if sid == -1 or not qs:
                    st.error("没有找到符合条件的题目，请检查筛选条件。")
                else:
                    st.session_state["practice_phase"] = "answering"
                    st.session_state["practice_session_id"] = sid
                    st.session_state["practice_questions"] = qs
                    st.session_state["practice_index"] = 0
                    st.session_state["practice_submitted"] = set()
                    st.session_state["practice_results"] = {}
                    st.session_state["practice_user_answers"] = {}
                    st.rerun()

    # ── 答题页 ────────────────────────────────────────
    elif phase == "answering":
        questions = st.session_state["practice_questions"]
        idx = st.session_state["practice_index"]
        submitted = st.session_state["practice_submitted"]
        results = st.session_state["practice_results"]

        # 进度条
        total_q = len(questions)
        answered = len(submitted)
        st.progress(answered / total_q, text=f"进度：{answered}/{total_q}")

        if idx >= total_q:
            st.session_state["practice_phase"] = "summary"
            st.rerun()

        q = questions[idx]
        already_submitted = q.id in submitted

        st.markdown(f"### 第 {idx + 1} / {total_q} 题　`{q.type_label}`")
        st.markdown(f"**{q.stem}**")

        # ── 根据题型渲染 ──────────────────────────────
        user_answer = None

        if q.q_type in (Q_TYPE_SINGLE, Q_TYPE_MULTI):
            options_list = [f"{k}. {v}" for k, v in sorted(q.options.items())]

            if already_submitted:
                # 展示选项，标记正确/用户选择
                correct_letters = set(q.answer.upper())
                user_letters = set(st.session_state["practice_user_answers"].get(q.id, ""))
                for opt in options_list:
                    letter = opt[0]
                    is_correct = letter in correct_letters
                    was_chosen = letter in user_letters
                    if is_correct and was_chosen:
                        st.success(f"✅ {opt}（正确）")
                    elif is_correct:
                        st.info(f"✅ {opt}（正确答案）")
                    elif was_chosen:
                        st.error(f"❌ {opt}（你的选择）")
                    else:
                        st.write(f"　{opt}")
            else:
                if q.q_type == Q_TYPE_SINGLE:
                    sel = st.radio(
                        "选择答案：",
                        options_list,
                        index=None,
                        key=f"ans_{q.id}",
                    )
                    user_answer = sel[0] if sel else None
                else:
                    sel = st.multiselect(
                        "选择所有正确答案：",
                        options_list,
                        key=f"ans_{q.id}",
                    )
                    user_answer = "".join(sorted(s[0] for s in sel)) if sel else None

        elif q.q_type == Q_TYPE_JUDGE:
            if already_submitted:
                user_ans = st.session_state["practice_user_answers"].get(q.id, "")
                correct_ans = "T"
                if results.get(q.id):
                    st.success(f"✅ 回答正确：{'正确' if user_ans == 'T' else '错误'}")
                else:
                    st.error(f"❌ 你选了「{'正确' if user_ans == 'T' else '错误'}」，正确答案是「{'正确' if correct_ans == q.answer else '错误'}」")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✔ 正确", key=f"judge_T_{q.id}", use_container_width=True):
                        user_answer = "T"
                        is_correct, explanation = submit_answer(
                            st.session_state["practice_session_id"], q.id, user_answer
                        )
                        submitted.add(q.id)
                        results[q.id] = is_correct
                        st.session_state["practice_user_answers"][q.id] = user_answer
                        st.rerun()
                with c2:
                    if st.button("✘ 错误", key=f"judge_F_{q.id}", use_container_width=True):
                        user_answer = "F"
                        is_correct, explanation = submit_answer(
                            st.session_state["practice_session_id"], q.id, user_answer
                        )
                        submitted.add(q.id)
                        results[q.id] = is_correct
                        st.session_state["practice_user_answers"][q.id] = user_answer
                        st.rerun()

        elif q.q_type == Q_TYPE_FILL:
            if already_submitted:
                user_ans = st.session_state["practice_user_answers"].get(q.id, "")
                if results.get(q.id):
                    st.success(f"✅ 正确：{user_ans}")
                else:
                    st.error(f"❌ 你的答案：{user_ans}")
                    st.info(f"正确答案：{q.answer}")
            else:
                fill_ans = st.text_input("填写答案：", key=f"ans_{q.id}", placeholder="输入答案...")
                user_answer = fill_ans.strip() if fill_ans else None

        elif q.q_type == Q_TYPE_ESSAY:
            if already_submitted:
                user_ans = st.session_state["practice_user_answers"].get(q.id, "")
                st.markdown("**你的回答：**")
                st.info(user_ans or "（未作答）")
                st.markdown("**参考答案：**")
                st.success(q.answer)
            else:
                essay_ans = st.text_area("作答：", key=f"ans_{q.id}", height=120)
                user_answer = essay_ans.strip() if essay_ans else None

        # ── 反馈区 ───────────────────────────────────
        if already_submitted and q.q_type not in (Q_TYPE_JUDGE,):
            if results.get(q.id):
                st.success("✅ 回答正确！")
            elif q.q_type != Q_TYPE_ESSAY:
                st.error("❌ 回答有误")

        if already_submitted and q.explanation:
            with st.expander("📖 查看解析"):
                st.write(q.explanation)

        st.divider()

        # ── 操作按钮 ─────────────────────────────────
        btn_cols = st.columns([1, 1, 1])

        # 提交按钮（仅对非判断题显示）
        if not already_submitted and q.q_type != Q_TYPE_JUDGE:
            with btn_cols[0]:
                if st.button("提交答案", key=f"submit_{q.id}", type="primary"):
                    if user_answer is None:
                        st.warning("请先选择/填写答案")
                    else:
                        is_correct, _ = submit_answer(
                            st.session_state["practice_session_id"], q.id, user_answer
                        )
                        submitted.add(q.id)
                        results[q.id] = is_correct
                        st.session_state["practice_user_answers"][q.id] = user_answer
                        st.rerun()

        # 下一题
        if already_submitted or q.q_type == Q_TYPE_ESSAY:
            with btn_cols[1]:
                label = "下一题 →" if idx + 1 < total_q else "查看结果 →"
                if st.button(label, key=f"next_{idx}", type="primary" if already_submitted else "secondary"):
                    if not already_submitted:
                        # 问答题直接记录
                        ans = st.session_state.get(f"ans_{q.id}", "")
                        submit_answer(st.session_state["practice_session_id"], q.id, ans)
                        submitted.add(q.id)
                        results[q.id] = False
                        st.session_state["practice_user_answers"][q.id] = ans
                    st.session_state["practice_index"] = idx + 1
                    if idx + 1 >= total_q:
                        st.session_state["practice_phase"] = "summary"
                    st.rerun()

        with btn_cols[2]:
            if st.button("结束练习", key=f"end_{idx}"):
                st.session_state["practice_phase"] = "summary"
                st.rerun()

    # ── 汇总页 ────────────────────────────────────────
    elif phase == "summary":
        sid = st.session_state.get("practice_session_id")
        if sid:
            session = complete_session(sid)
            st.subheader("🎉 练习结束")
            m1, m2, m3 = st.columns(3)
            m1.metric("总题数", session.total)
            m2.metric("正确数", session.correct)
            m3.metric("准确率", f"{session.accuracy:.0%}")

            # 错题回顾
            details = get_store().get_session_detail(sid)
            wrong = [d for d in details if not d["is_correct"] and d["q_type"] != Q_TYPE_ESSAY]
            if wrong:
                st.divider()
                st.subheader(f"❌ 错题回顾（{len(wrong)} 道）")
                for i, d in enumerate(wrong, 1):
                    with st.expander(f"第{i}题：{d['stem'][:50]}…"):
                        st.markdown(f"**题干：** {d['stem']}")
                        opts = d.get("options", {})
                        if opts:
                            for letter in sorted(opts):
                                prefix = "✅ " if letter == d["correct_answer"].upper() else "　"
                                if letter == d["user_answer"].upper():
                                    prefix = "❌ "
                                st.markdown(f"　{prefix}{letter}. {opts[letter]}")
                        st.markdown(f"**你的答案：** `{d['user_answer']}`　**正确答案：** `{d['correct_answer']}`")
                        if d.get("explanation"):
                            st.info(f"解析：{d['explanation']}")

        if st.button("🔄 重新练习", type="primary"):
            for key in ["practice_phase", "practice_session_id", "practice_questions",
                        "practice_index", "practice_submitted", "practice_results",
                        "practice_user_answers"]:
                st.session_state.pop(key, None)
            st.rerun()


# ══════════════════════════════════════════════════════
# Tab 3：题库管理
# ══════════════════════════════════════════════════════
with tab3:
    mgmt_view = st.radio(
        "浏览方式",
        ["按试卷", "按分组"],
        horizontal=True,
        key="mgmt_view",
    )

    if mgmt_view == "按试卷":
        papers = list_papers()
        if not papers:
            st.info("题库为空，请先在「导入试卷」Tab 上传题目。")
        else:
            col_list, col_detail = st.columns([1, 2])
            with col_list:
                st.subheader("试卷列表")
                for p in papers:
                    with st.expander(f"📄 {p['name']} ({p['total_count']}题)"):
                        st.caption(f"来源：{p['source_file']}")
                        st.caption(f"导入时间：{p['import_time'][:10]}")
                        if st.button(
                            "查看题目", key=f"view_paper_{p['id']}", use_container_width=True
                        ):
                            st.session_state["mgmt_selected_paper"] = p["id"]
                        if st.button(
                            "🗑 删除试卷", key=f"del_paper_{p['id']}",
                            use_container_width=True,
                        ):
                            store = get_store()
                            n = store.delete_paper(p["id"])
                            st.success(f"已删除试卷及 {n} 道题目")
                            st.session_state.pop("mgmt_selected_paper", None)
                            st.rerun()

            with col_detail:
                pid = st.session_state.get("mgmt_selected_paper")
                if pid:
                    page = st.session_state.get("mgmt_page", 0)
                    page_size = 20
                    total = get_question_count_v2(paper_id=pid)
                    qs = get_questions(paper_id=pid, limit=page_size, offset=page * page_size)

                    paper_info = get_store().get_paper(pid)
                    name = paper_info["name"] if paper_info else "试卷"
                    st.subheader(f"{name}（共 {total} 道）")

                    for q in qs:
                        with st.expander(f"[{q.type_label}] {q.stem[:60]}"):
                            st.markdown(f"**题干：** {q.stem}")
                            if q.options:
                                for letter in sorted(q.options):
                                    prefix = "✅ " if letter == q.answer.upper() else "　"
                                    st.markdown(f"　{prefix}{letter}. {q.options[letter]}")
                            st.markdown(f"**答案：** `{q.answer}`")
                            if q.explanation:
                                st.markdown(f"**解析：** {q.explanation}")
                            if q.subject:
                                st.caption(f"科目：{q.subject}")

                            # 加入分组
                            groups = list_groups()
                            if groups:
                                sel_group = st.selectbox(
                                    "加入分组",
                                    groups,
                                    format_func=lambda g: g["name"],
                                    key=f"add_group_{q.id}",
                                )
                                if st.button("➕ 加入", key=f"do_add_{q.id}"):
                                    get_store().add_to_group([q.id], sel_group["id"])
                                    st.success(f"已加入「{sel_group['name']}」")

                            if st.button("🗑 删除此题", key=f"del_q_{q.id}"):
                                get_store().delete_question(q.id)
                                st.success("已删除")
                                st.rerun()

                    # 翻页
                    total_pages = max(1, (total - 1) // page_size + 1)
                    if total_pages > 1:
                        new_page = st.number_input(
                            f"页码（共{total_pages}页）",
                            min_value=1, max_value=total_pages,
                            value=page + 1, step=1,
                            key="mgmt_page_input",
                        ) - 1
                        if new_page != page:
                            st.session_state["mgmt_page"] = new_page
                            st.rerun()
                else:
                    st.info("← 从左侧选择一个试卷查看题目")

    else:  # 按分组
        col_g, col_gd = st.columns([1, 2])
        with col_g:
            st.subheader("分组管理")
            with st.form("new_group_form", clear_on_submit=True):
                new_name = st.text_input("新建分组名称")
                new_desc = st.text_input("描述（可选）")
                if st.form_submit_button("➕ 创建分组"):
                    if new_name.strip():
                        try:
                            get_store().create_group(new_name.strip(), new_desc.strip())
                            st.success(f"分组「{new_name}」已创建")
                            st.rerun()
                        except Exception:
                            st.error("分组名称已存在")
                    else:
                        st.warning("请输入分组名称")

            groups = list_groups()
            for g in groups:
                with st.expander(f"🗂 {g['name']} ({g['question_count']}题)"):
                    if g["description"]:
                        st.caption(g["description"])
                    if st.button("查看题目", key=f"view_g_{g['id']}", use_container_width=True):
                        st.session_state["mgmt_selected_group"] = g["id"]
                    if st.button("🗑 删除分组", key=f"del_g_{g['id']}", use_container_width=True):
                        get_store().delete_group(g["id"])
                        st.session_state.pop("mgmt_selected_group", None)
                        st.rerun()

        with col_gd:
            gid = st.session_state.get("mgmt_selected_group")
            if gid:
                total_g = get_question_count_v2(group_id=gid)
                qs_g = get_questions(group_id=gid, limit=50)
                groups = list_groups()
                gname = next((g["name"] for g in groups if g["id"] == gid), "分组")
                st.subheader(f"{gname}（{total_g} 道题）")
                for q in qs_g:
                    with st.expander(f"[{q.type_label}] {q.stem[:60]}"):
                        st.markdown(f"**题干：** {q.stem}")
                        if q.options:
                            for letter in sorted(q.options):
                                prefix = "✅ " if letter == q.answer.upper() else "　"
                                st.markdown(f"　{prefix}{letter}. {q.options[letter]}")
                        st.markdown(f"**答案：** `{q.answer}`")
                        if st.button("➖ 从分组移除", key=f"rm_{q.id}_{gid}"):
                            get_store().remove_from_group([q.id], gid)
                            st.rerun()
            else:
                st.info("← 从左侧选择分组查看题目")


# ══════════════════════════════════════════════════════
# Tab 4：练习记录
# ══════════════════════════════════════════════════════
with tab4:
    st.subheader("练习历史")
    sessions = get_session_history(limit=50)
    if not sessions:
        st.info("还没有练习记录，去「题目练习」Tab 开始吧！")
    else:
        for s in sessions:
            label = (
                f"{'试卷' if s.source_type == 'paper' else '分组' if s.source_type == 'group' else '全部题库'} | "
                f"{s.start_time[:10]} {s.start_time[11:16]} | "
                f"✅ {s.correct}/{s.total} ({s.accuracy:.0%})"
            )
            with st.expander(label):
                if s.status == "in_progress":
                    st.warning("练习未完成")
                else:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("总题数", s.total)
                    m2.metric("正确数", s.correct)
                    m3.metric("准确率", f"{s.accuracy:.0%}")

                if st.button("查看错题", key=f"detail_{s.id}"):
                    st.session_state["history_detail"] = s.id

                if st.session_state.get("history_detail") == s.id:
                    detail = get_store().get_session_detail(s.id)
                    wrong = [d for d in detail if not d["is_correct"]]
                    if not wrong:
                        st.success("全部答对！")
                    else:
                        for d in wrong:
                            st.markdown(f"**题干：** {d['stem']}")
                            st.markdown(
                                f"你的答案：`{d['user_answer']}`　正确答案：`{d['correct_answer']}`"
                            )
                            if d.get("explanation"):
                                st.caption(f"解析：{d['explanation']}")
                            st.divider()
