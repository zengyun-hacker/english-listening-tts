"""
English Listening Exam TTS — Streamlit Web UI
Run: streamlit run app.py
"""

import asyncio
import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _get_openai_key_from_env() -> str:
    """Read OpenAI key from local .env or Streamlit Cloud Secrets."""
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "")


def _get_deepseek_key_from_env() -> str:
    """Read DeepSeek key from local .env or Streamlit Cloud Secrets."""
    try:
        return st.secrets.get("DEEPSEEK_API_KEY", "")
    except Exception:
        pass
    return os.getenv("DEEPSEEK_API_KEY", "")


# ─────────────────────────────────────────────
# Page config (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="英语听力 TTS 工具",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Password gate
# ─────────────────────────────────────────────
def _check_auth():
    """Block access unless the visitor knows APP_PASSWORD.

    - If APP_PASSWORD is not set in secrets / env, the gate is disabled
      (safe for local development).
    - Authentication is persisted in st.session_state for the browser session.
    """
    try:
        required = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        required = os.getenv("APP_PASSWORD", "")

    if not required:
        return  # No password configured → open access

    if st.session_state.get("_authed"):
        return  # Already authenticated this session

    # ── Login screen ──────────────────────────
    st.markdown(
        "<h2 style='text-align:center;margin-top:3rem;'>🔐 请输入访问密码</h2>",
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        entered = st.text_input("密码", type="password", label_visibility="collapsed",
                                placeholder="请输入密码…")
        if st.button("进入", use_container_width=True, type="primary"):
            if entered == required:
                st.session_state["_authed"] = True
                st.rerun()
            else:
                st.error("密码错误，请重试。")
    st.stop()


_check_auth()


# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main-title  { font-size:2rem; font-weight:700; color:#1a1a2e; margin-bottom:.2rem; }
    .sub-title   { color:#555; font-size:1rem; margin-bottom:1.5rem; }
    .sec-header  { font-size:1.1rem; font-weight:600; color:#2c3e50;
                   border-left:4px solid #4CAF50; padding-left:10px;
                   margin:1rem 0 .5rem 0; }
    .speaker-tag { display:inline-block; background:#e8f5e9; color:#2e7d32;
                   border-radius:12px; padding:2px 10px; font-size:.85rem;
                   font-weight:600; margin:2px; }
    .q-tag       { display:inline-block; background:#fff3e0; color:#e65100;
                   border-radius:12px; padding:2px 10px; font-size:.85rem;
                   font-weight:600; }
    .tip-box     { background:#e3f2fd; border:1px solid #90caf9; border-radius:8px;
                   padding:10px 14px; font-size:.9rem; color:#1565c0; }
    .ans-box     { background:#f1f8e9; border:1px solid #aed581; border-radius:8px;
                   padding:10px 14px; font-size:.88rem; color:#33691e;
                   font-family:monospace; white-space:pre-wrap; }
    footer { visibility:hidden; }
    #MainMenu { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Core generation function (shared by both tabs)
# ─────────────────────────────────────────────
def run_generate(script_text, provider, voice_a, voice_b,
                 openai_key, openai_model, openai_speed,
                 pause_between, q_pause):
    """Synthesize audio and render the result (player + download) into Streamlit."""
    import config
    from parser.script_parser import parse_script
    from audio.processor import render_audio

    # Apply runtime audio settings
    config.AUDIO_SETTINGS["pause_between_speakers"] = pause_between
    config.AUDIO_SETTINGS["pause_after_question_number"] = q_pause
    if provider == "openai":
        config.AUDIO_SETTINGS["openai_speed"] = openai_speed

    # Build TTS provider
    if provider == "openai":
        from tts.openai_provider import get_provider
        tts = get_provider(api_key=openai_key, model=openai_model, speed=openai_speed)
    else:
        from tts.edge_provider import get_provider
        tts = get_provider()

    script = parse_script(script_text)

    # Voice overrides — cover all common role names
    voice_overrides = {"a": voice_a, "b": voice_b,
                       "man": voice_a, "male": voice_a, "男": voice_a, "男生": voice_a, "男士": voice_a,
                       "woman": voice_b, "female": voice_b, "女": voice_b, "女生": voice_b, "女士": voice_b}
    speakers = script.speakers
    if speakers:
        voice_overrides[speakers[0].lower()] = voice_a
    if len(speakers) > 1:
        voice_overrides[speakers[1].lower()] = voice_b

    progress_bar = st.progress(0, text="正在准备合成…")
    status_ph = st.empty()

    def on_progress(cur, tot, spk):
        progress_bar.progress(cur / tot, text=f"正在合成第 {cur}/{tot} 段 — {spk}")

    tmp_path = Path(tempfile.mktemp(suffix=".mp3"))
    try:
        asyncio.run(render_audio(script, tts, tmp_path, voice_overrides, on_progress))
        progress_bar.progress(1.0, text="✅ 合成完成！")
        status_ph.empty()

        audio_bytes = tmp_path.read_bytes()
        st.success("🎉 音频生成成功！")
        st.audio(audio_bytes, format="audio/mp3")

        slug = script.title.replace(" ", "_").replace("/", "-")[:30]
        st.download_button(
            label="⬇️ 下载 MP3",
            data=audio_bytes,
            file_name=f"{slug}.mp3",
            mime="audio/mpeg",
            use_container_width=True,
            type="primary",
        )
    except Exception as e:
        progress_bar.empty()
        st.error(f"生成失败：{e}")
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            st.info("请检查左侧面板中的 OpenAI API Key 是否正确。")
    finally:
        tmp_path.unlink(missing_ok=True)


# ─────────────────────────────────────────────
# Example scripts (Tab 1)
# ─────────────────────────────────────────────
EXAMPLES = {
    "（选择示例快速体验）": "",
    "🍽️ 餐厅对话": """\
Number 1.
[Man]: Good evening. Do you have a reservation?
[Woman]: Yes, I booked a table for two under the name Johnson.
[Man]: Right this way. Would you prefer a window seat?
[Woman]: That would be lovely, thank you.

Number 2.
[Man]: Are you ready to order, or do you need a few more minutes?
[Woman]: I'll have the grilled salmon, please.
[Man]: Excellent choice. And to drink?
[Woman]: Just sparkling water, please.""",

    "🌍 气候讲座（独白）": """\
Good morning, everyone. Today I'd like to talk about climate change and our oceans.

The ocean covers about seventy percent of Earth's surface and plays a crucial role in regulating the global climate. It absorbs around thirty percent of the carbon dioxide humans produce.

Number 3. Scientists have recorded a thirty percent increase in ocean acidity since the Industrial Revolution.

Therefore, reducing carbon emissions is not only about protecting the atmosphere — it is about protecting our oceans as well. Thank you.""",

    "✈️ 机场广播": """\
[Announcer]: Good afternoon, ladies and gentlemen. This is a passenger announcement for Flight BA two-seven-five to London Heathrow.

[Announcer]: We regret to inform you that this flight has been delayed by approximately forty-five minutes due to late arrival of the incoming aircraft.

[Announcer]: The new departure time is seventeen thirty. Please proceed to Gate Twelve when boarding begins. Thank you for your patience.""",

    "💼 求职面试": """\
Interviewer: Good morning. Please take a seat.
Candidate: Thank you. Good morning.

Interviewer: Tell me about yourself and why you're interested in this position.
Candidate: Certainly. I graduated from the University of Manchester with a degree in Business Administration. I'm particularly drawn to this role because it combines data analysis with client-facing work.

Interviewer: Can you describe a time you worked under pressure?
Candidate: Last year my team had to deliver a major report in three days. I divided the workload and we submitted on time. The client was very pleased.

Interviewer: Do you have any questions for us?
Candidate: Yes — could you tell me more about opportunities for professional development?""",
}

# ─────────────────────────────────────────────
# AI generation example prompts (Tab 2)
# ─────────────────────────────────────────────
AI_EXAMPLE_PROMPTS = {
    "（选择示例提示词）": "",
    "🎓 大学英语四级·15题": (
        "请生成一套完整的大学英语四级听力试题，包含：\n"
        "- Part I 短对话 8题（每题一段简短对话）\n"
        "- Part II 长对话 2段，共4题\n"
        "- Part III 短文听力 1篇，共3题\n"
        "话题涵盖校园生活、职场、日常交流。难度适合大学生。"
    ),
    "🏫 高中英语听力·10题": (
        "请生成一套高中英语听力模拟题，共10题：\n"
        "- 第一节 短对话 5题\n"
        "- 第二节 长对话 1段3题 + 独白1段2题\n"
        "语言难度适合高中生，话题贴近日常生活和学校场景。"
    ),
    "💼 职场英语听力·8题": (
        "请生成一套商务职场英语听力题，共8题：\n"
        "- 3段职场对话（会议、邮件、电话）各2题\n"
        "- 1段商务简报独白 2题\n"
        "使用正式职场英语，话题包括项目汇报、客户沟通、会议安排。"
    ),
    "🌏 新闻广播听力·6题": (
        "请生成一套英语新闻广播听力题，共6题：\n"
        "- 2篇新闻报道，每篇3题\n"
        "- 类型：独白（播音员口吻）\n"
        "话题：科技新闻和环境新闻。语速适中，适合大学英语水平。"
    ),
}


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown('<div class="main-title">🎧 英语听力 TTS 工具</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">将听力原文脚本一键转为标准英语语音 · 支持对话、独白、广播、采访等全部题型</div>',
            unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar — settings
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 设置")

    st.markdown("### 语音引擎")
    provider = st.radio(
        "选择语音引擎",
        options=["edge", "openai"],
        format_func=lambda x: "✅ edge-tts（免费推荐）" if x == "edge" else "⭐ OpenAI TTS（更自然）",
        help="edge-tts 完全免费，无需注册；OpenAI TTS 需要 API Key，语音更自然流畅。",
    )

    if provider == "openai":
        openai_key = st.text_input("OpenAI API Key", value=_get_openai_key_from_env(),
                                    type="password", placeholder="sk-...")
        openai_model = st.selectbox("模型", ["tts-1-hd", "tts-1"],
                                     help="tts-1-hd 质量更高；tts-1 更快更便宜")
        openai_speed = st.slider("语速", 0.7, 1.2, 0.95, 0.05,
                                  help="1.0 为正常速度，听力考试建议 0.90–0.95")
    else:
        openai_key, openai_model, openai_speed = "", "tts-1-hd", 0.95

    st.markdown("---")
    st.markdown("### 🎙️ 说话人声音")

    EDGE_VOICES_UI = {
        "美式男声": "male_us", "英式男声": "male_uk", "澳式男声": "male_au",
        "美式女声": "female_us", "英式女声": "female_uk", "澳式女声": "female_au",
        "播音员（中性）": "narrator",
    }
    OPENAI_VOICES_UI = {
        "Onyx（低沉男声）": "onyx", "Echo（清晰男声）": "echo", "Fable（英式男声）": "fable",
        "Nova（标准女声）": "nova", "Shimmer（柔和女声）": "shimmer", "Alloy（中性）": "alloy",
    }
    voice_opts = EDGE_VOICES_UI if provider == "edge" else OPENAI_VOICES_UI
    v_keys = list(voice_opts.keys())

    voice_a_label = st.selectbox("说话人 A / [Man]", v_keys, index=0)
    voice_b_label = st.selectbox("说话人 B / [Woman]", v_keys, index=3)
    voice_a = voice_opts[voice_a_label]
    voice_b = voice_opts[voice_b_label]

    st.markdown("---")
    st.markdown("### 🔊 停顿设置")
    pause_between = st.slider("句子间停顿（毫秒）", 200, 1500, 600, 100)
    q_pause = st.slider("题号后停顿（毫秒）", 500, 2000, 900, 100,
                         help="播报 'Number 1' 后的停顿时间")

    st.markdown("---")

    # DeepSeek API Key (shown when env var not set)
    _ds_key_from_env = _get_deepseek_key_from_env()
    if _ds_key_from_env:
        deepseek_key = _ds_key_from_env
        st.markdown("### 🤖 AI 生成")
        st.success("✅ DeepSeek API Key 已从环境变量加载")
    else:
        st.markdown("### 🤖 AI 生成（可选）")
        deepseek_key = st.text_input(
            "DeepSeek API Key",
            type="password",
            placeholder="sk-...",
            help="在 platform.deepseek.com 获取 API Key，用于 AI 自动出题功能。",
        )

    deepseek_model = st.selectbox(
        "DeepSeek 模型",
        ["deepseek-chat", "deepseek-reasoner"],
        help="deepseek-chat 速度快，deepseek-reasoner 推理更强。",
    )

    st.markdown("---")
    st.caption("仅供教学用途 · 基于 Microsoft edge-tts / OpenAI TTS / DeepSeek")


# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["✍️ 手动输入", "🤖 AI 生成"])


# ═════════════════════════════════════════════
# Tab 1 — Manual input (existing functionality)
# ═════════════════════════════════════════════
with tab1:
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown('<div class="sec-header">📝 粘贴听力脚本</div>', unsafe_allow_html=True)

        with st.expander("📖 脚本格式说明（点击展开）", expanded=False):
            st.markdown("""
**对话**（自动分配男女声）：
```
Number 1.
[Man]: Good morning. Can I help you?
[Woman]: Yes, I'd like to book a table for two.
```
**独白 / 讲座**（直接写正文）：
```
Today I'd like to talk about climate change...
Number 3. Scientists have found that...
```
**广播通知**：
```
[Announcer]: Attention all passengers. Flight BA275 is now boarding...
```
**中文角色名也支持**：`[男]: ...` `[女]: ...`

**题号格式均可识别**：`Number 1.` / `Q1.` / `(Q1)` — 会自动语音播报
            """)

        selected = st.selectbox("快速加载示例", list(EXAMPLES.keys()))
        script_text = st.text_area(
            "脚本输入区",
            value=EXAMPLES[selected],
            height=340,
            placeholder="在这里粘贴听力原文…\n\nNumber 1.\n[Man]: Good morning!\n[Woman]: Hello there.",
            label_visibility="collapsed",
        )

    with col_right:
        st.markdown('<div class="sec-header">🔍 脚本预览</div>', unsafe_allow_html=True)

        if script_text.strip():
            from parser.script_parser import parse_script
            parsed = parse_script(script_text)

            c1, c2 = st.columns(2)
            c1.metric("识别片段数", len(parsed.segments))
            type_map = {"dialogue": "对话", "monologue": "独白", "broadcast": "广播"}
            c2.metric("题型", type_map.get(parsed.script_type, parsed.script_type))

            if parsed.speakers:
                tags = " ".join(f'<span class="speaker-tag">{s}</span>' for s in parsed.speakers)
                st.markdown("**说话人：** " + tags, unsafe_allow_html=True)

            lines_html = []
            for seg in parsed.segments:
                if seg.is_question_marker:
                    lines_html.append(f'<span class="q-tag">🔔 {seg.text}</span>')
                else:
                    spk = f"<b>[{seg.speaker}]</b>" if seg.speaker else "<i>[旁白]</i>"
                    txt = (seg.text[:58] + "…") if len(seg.text) > 58 else seg.text
                    lines_html.append(f"{spk}&nbsp;&nbsp;{txt}")
            st.markdown("<br>".join(lines_html), unsafe_allow_html=True)
        else:
            st.info("在左侧输入脚本后，这里会显示解析预览。")

        st.markdown("---")
        st.markdown('<div class="sec-header">🎵 生成语音</div>', unsafe_allow_html=True)

        if not script_text.strip():
            st.warning("请先在左侧输入听力脚本。")
        elif provider == "openai" and not openai_key:
            st.error("使用 OpenAI TTS 需要在左侧填入 API Key。")
        else:
            if st.button("🚀 一键生成音频", type="primary", use_container_width=True, key="gen_manual"):
                run_generate(
                    script_text=script_text,
                    provider=provider,
                    voice_a=voice_a,
                    voice_b=voice_b,
                    openai_key=openai_key,
                    openai_model=openai_model,
                    openai_speed=openai_speed,
                    pause_between=pause_between,
                    q_pause=q_pause,
                )

    st.markdown("---")
    st.markdown(
        '<div class="tip-box">💡 <b>新手建议</b>：先从上方「快速加载示例」选一个体验效果，'
        '再把 AI 生成的听力原文按照 <code>[Man]: ...</code> / <code>[Woman]: ...</code> 格式粘贴进来即可。</div>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════
# Tab 2 — AI generation
# ═════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec-header">🤖 AI 自动出题</div>', unsafe_allow_html=True)
    st.markdown("输入要求，DeepSeek 将自动生成完整听力试卷（原文 + 题目 + 答案），然后一键合成音频并下载 Word 试卷。")

    ai_col_left, ai_col_right = st.columns([1, 1], gap="large")

    with ai_col_left:
        st.markdown("#### 📋 描述你的出题需求")

        # Example prompt selector
        ai_selected = st.selectbox("快速加载示例提示词", list(AI_EXAMPLE_PROMPTS.keys()), key="ai_example_sel")
        ai_prompt_default = AI_EXAMPLE_PROMPTS[ai_selected]

        ai_prompt = st.text_area(
            "提示词",
            value=ai_prompt_default,
            height=260,
            placeholder=(
                "例如：\n"
                "请生成一套大学英语四级听力试题，共15题：\n"
                "- Part I 短对话 8题\n"
                "- Part II 长对话 4题\n"
                "- Part III 独白 3题\n"
                "话题涵盖校园生活和职场场景。"
            ),
            label_visibility="collapsed",
        )

        # Generate test button
        can_generate = bool(ai_prompt.strip() and deepseek_key)
        if not deepseek_key:
            st.warning("请在左侧边栏填入 DeepSeek API Key。")

        gen_btn = st.button(
            "✨ AI 生成试卷",
            type="primary",
            use_container_width=True,
            disabled=not can_generate,
            key="gen_ai_test",
        )

        if gen_btn and can_generate:
            with st.spinner("🤖 DeepSeek 正在生成听力试卷，请稍候（约 20–60 秒）…"):
                try:
                    from llm.deepseek import generate_listening_test
                    ai_test = generate_listening_test(
                        prompt=ai_prompt,
                        api_key=deepseek_key,
                        model=deepseek_model,
                    )
                    st.session_state["ai_test"] = ai_test
                    st.success(f"✅ 生成成功！共 {sum(len(s.items) for s in ai_test.sections)} 题")
                except Exception as e:
                    st.error(f"生成失败：{e}")
                    if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                        st.info("请检查 DeepSeek API Key 是否正确。")

    with ai_col_right:
        st.markdown("#### 📄 生成结果预览")

        ai_test = st.session_state.get("ai_test")

        if ai_test is None:
            st.info("点击左侧「AI 生成试卷」后，题目和答案将在这里显示。")
        else:
            # Show test overview
            total_q = sum(len(s.items) for s in ai_test.sections)
            st.markdown(f"**{ai_test.title}**  ·  共 {total_q} 题，{len(ai_test.sections)} 个 Part")
            st.markdown("---")

            for sec in ai_test.sections:
                with st.expander(f"📂 {sec.name}（{len(sec.items)} 题）", expanded=True):
                    if sec.instructions:
                        st.caption(sec.instructions)
                    for item in sec.items:
                        st.markdown(f"**{item.number}. {item.question}**")
                        for letter in ("A", "B", "C", "D"):
                            opt = item.options.get(letter, "")
                            if opt:
                                prefix = "✅" if letter == item.answer else "　"
                                st.markdown(f"{prefix} {letter}. {opt}")
                        if item.explanation:
                            st.caption(f"解析：{item.explanation}")
                        st.markdown("")

    # ── Bottom action bar ──────────────────────────────────────────────
    if st.session_state.get("ai_test"):
        ai_test = st.session_state["ai_test"]
        st.markdown("---")
        st.markdown('<div class="sec-header">🎵 生成音频 & 下载试卷</div>', unsafe_allow_html=True)

        action_col1, action_col2, action_col3, action_col4 = st.columns([2, 1, 1, 1], gap="medium")

        with action_col1:
            if provider == "openai" and not openai_key:
                st.error("使用 OpenAI TTS 需要在侧边栏填入 OpenAI API Key。")
            else:
                if st.button("🎙️ 生成音频", type="primary", use_container_width=True, key="gen_ai_audio"):
                    tts_script = ai_test.to_tts_script()
                    run_generate(
                        script_text=tts_script,
                        provider=provider,
                        voice_a=voice_a,
                        voice_b=voice_b,
                        openai_key=openai_key,
                        openai_model=openai_model,
                        openai_speed=openai_speed,
                        pause_between=pause_between,
                        q_pause=q_pause,
                    )

        safe_title = ai_test.title.replace(" ", "_").replace("/", "-")[:40]
        _mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        with action_col2:
            # Word — questions + answers only (student exam sheet)
            try:
                from export.docx_export import export_to_docx
                docx_bytes = export_to_docx(ai_test)
                st.download_button(
                    label="📄 试卷（无原文）",
                    data=docx_bytes,
                    file_name=f"{safe_title}_试卷.docx",
                    mime=_mime,
                    use_container_width=True,
                    help="包含题目和答案页，适合学生答题使用",
                )
            except ImportError:
                st.warning("请安装 python-docx：`pip install python-docx`")
            except Exception as e:
                st.error(f"Word 导出失败：{e}")

        with action_col3:
            # Word — script + questions + answers (teacher reference)
            try:
                from export.docx_export import export_to_docx_full
                docx_full_bytes = export_to_docx_full(ai_test)
                st.download_button(
                    label="📖 原文+试题+答案",
                    data=docx_full_bytes,
                    file_name=f"{safe_title}_含原文.docx",
                    mime=_mime,
                    use_container_width=True,
                    help="每道题附有听力原文和答案解析，适合教师备课或课后复习",
                )
            except ImportError:
                st.warning("请安装 python-docx：`pip install python-docx`")
            except Exception as e:
                st.error(f"Word 导出失败：{e}")

        with action_col4:
            # Show answer key inline
            with st.expander("📋 查看答案表"):
                st.markdown(
                    f'<div class="ans-box">{ai_test.to_answer_key()}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.markdown(
            '<div class="tip-box">💡 <b>下载说明</b>：'
            '「试卷（无原文）」适合打印给学生作答；'
            '「原文+试题+答案」每题附听力原文和解析，适合老师备课或课后对答案。</div>',
            unsafe_allow_html=True,
        )
