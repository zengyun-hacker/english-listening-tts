"""
English Listening Exam TTS — Streamlit Web UI
Run: streamlit run app.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Ensure stdout/stderr can handle UTF-8 (Chinese chars in print logs)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

APP_VERSION = "2.0"

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
    page_title=f"英语听力音频生成工具 v{APP_VERSION}",
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
# DeepSeek script formatter
# ─────────────────────────────────────────────
_FORMAT_SYSTEM_PROMPT = """\
# Role
你是一个专业的英语听力材料编辑器，专门负责将各种格式的原始听力文本（Raw Text）转换为适合 TTS（文本转语音）生成的标准脚本格式。

# Goal
请读取我提供的听力文本，并严格按照以下规则进行清洗和格式化。

# Rules

1. **对话处理 (Dialogues)**：
   - 识别文本中的对话部分。
   - 如果原文有角色标识（如 M/W, Man/Woman, A/B），请统一转换为标准标签：`[Man]:` 和 `[Woman]:`。
   - 如果原文没有角色标识，请根据语境自动推断并分配 `[Man]:` 和 `[Woman]:`（通常是一男一女交替）。
   - 每个角色的发言必须独占一行。

2. **独白/讲座处理 (Monologues/Lectures)**：
   - 如果是长段独白，不需要添加 `[Narrator]` 标签，直接保留正文即可。
   - 保持段落的完整性，不要随意换行。

3. **题号与结构 (Numbering & Structure)**：
   - 必须保留题号或段落编号（如 `Number 1.`, `Q1.`, `Set 1.`, `Question 15.`）。
   - 题号应该单独占一行，作为语音播报的提示。

4. **清洗杂质 (Cleaning)**：
   - 删除所有无关的元数据，例如："听力原文"、"Section A"、"Answer Key"、"(02:15)"（时间戳）、`**`（Markdown加粗符号）等。
   - 修正明显的拼写错误或OCR识别错误（如将 `l` 误识别为 `1`）。

5. **输出格式示例 (Output Format Example)**：

   Number 1.
   [Man]: Good morning. Can I help you?
   [Woman]: Yes, I'd like to book a table for two.

   Set 2.
   Attention all passengers. Flight BA275 is now boarding at Gate 15. Please have your boarding passes ready.

   Q3.
   [Man]: Did you finish the report?
   [Woman]: Not yet, I need more time.

# Workflow
1. 接收用户输入的原始文本。
2. 判断文本类型（对话、独白或混合）。
3. 应用上述规则进行格式化。
4. 直接输出整理好的文本，不要包含任何解释性语言（如"这是整理好的文本..."）。
"""


def format_script_with_deepseek(text: str, api_key: str, output_ph=None) -> str:
    """Send raw script text to DeepSeek for formatting, streaming the result."""
    import time
    from openai import OpenAI

    t0 = time.perf_counter()
    print(f"[DeepSeek] 开始流式请求 — 输入 {len(text)} 字符 (~{len(text)//4} tokens)", flush=True)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    stream = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": _FORMAT_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.2,
        stream=True,
    )

    chunks = []
    first_chunk_logged = False
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            if not first_chunk_logged:
                ttfb = (time.perf_counter() - t0) * 1000
                print(f"[DeepSeek] 首个 token 到达 (TTFB): {ttfb:.0f}ms", flush=True)
                first_chunk_logged = True
            chunks.append(delta)
            if output_ph is not None:
                output_ph.code("".join(chunks), language=None)

    result = "".join(chunks).strip()
    total_ms = (time.perf_counter() - t0) * 1000
    print(f"[DeepSeek] 完成 — 输出 {len(result)} 字符，总耗时 {total_ms:.0f}ms ({total_ms/1000:.1f}s)", flush=True)
    print("[DeepSeek] ===== 格式化结果 =====", flush=True)
    print(result, flush=True)
    print("[DeepSeek] ===== 结果结束 =====", flush=True)
    return result


# ─────────────────────────────────────────────
# Core audio generation — returns bytes
# ─────────────────────────────────────────────
def generate_audio_bytes(script_text, provider, voice_a, voice_b,
                         openai_key, openai_model, openai_speed,
                         pause_between, q_pause, progress_ph):
    """Synthesize audio and return (audio_bytes, slug). Updates progress_ph in place."""
    import config
    from parser.script_parser import parse_script
    from audio.processor import render_audio

    config.AUDIO_SETTINGS["pause_between_speakers"] = pause_between
    config.AUDIO_SETTINGS["pause_after_question_number"] = q_pause
    if provider == "openai":
        config.AUDIO_SETTINGS["openai_speed"] = openai_speed

    if provider == "openai":
        from tts.openai_provider import get_provider
        tts = get_provider(api_key=openai_key, model=openai_model, speed=openai_speed)
    else:
        from tts.edge_provider import get_provider
        tts = get_provider()

    script = parse_script(script_text)

    voice_overrides = {"a": voice_a, "b": voice_b,
                       "man": voice_a, "male": voice_a, "男": voice_a, "男生": voice_a, "男士": voice_a,
                       "woman": voice_b, "female": voice_b, "女": voice_b, "女生": voice_b, "女士": voice_b}
    speakers = script.speakers
    if speakers:
        voice_overrides[speakers[0].lower()] = voice_a
    if len(speakers) > 1:
        voice_overrides[speakers[1].lower()] = voice_b

    progress_bar = progress_ph.progress(0, text="正在准备合成…")

    def on_progress(cur, tot, spk):
        progress_bar.progress(cur / tot, text=f"正在合成第 {cur}/{tot} 段 — {spk}")

    tmp_path = Path(tempfile.mktemp(suffix=".mp3"))
    try:
        asyncio.run(render_audio(script, tts, tmp_path, voice_overrides, on_progress))
        progress_bar.progress(1.0, text="✅ 音频合成完成！")
        audio_bytes = tmp_path.read_bytes()
        slug = script.title.replace(" ", "_").replace("/", "-")[:30]
        return audio_bytes, slug
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

    # ── 格式化测试用例（原始杂乱格式，用于测试 DeepSeek 格式化功能）──
    "🧪 测试1：角色标识混乱的对话": """\
听力原文 Section A

**Question 1 (00:12)**
M: Hey, have you seen the new science building on campus?
W: Yeah, l walked past it yesterday. It looks amazing — way bigger than the old one.
M: I heard it has three new labs and a rooftop garden.
W: That's so cool. When does it officially open?
M: Some time next month, l think. There's going to be a ceremony.

Answer: B

**Q2 (00:45)**
W: Excuse me, does this bus go to Central Station?
M: No, you need the Number 12. This one only goes to the airport.
W: Oh no. How long does it take to walk?
M: About 20 minutes, but you could take a taxi — it's much faster.
W: Good idea, thank you so much.

Answer: C""",

    "🧪 测试2：无角色标识的自然对话": """\
Section B Long Conversation

Questions 11 to 13 are based on the following conversation.

(02:30)
So did you manage to book the hotel for the conference?
Not yet, I've been trying all morning but the website keeps crashing.
Have you tried calling them directly? Sometimes that's faster.
Good point. Do you have their number?
It should be on the confirmation email Sarah sent last week.
Oh right, I'll check that now. By the way, do you know if meals are included?
I think breakfast is, but you'll need to pay for dinner separately.
OK, I'll ask when I call. Thanks for the tip.

Answer Key: 11.B  12.A  13.C""",

    "🧪 测试3：独白含杂质标记": """\
**听力原文**
Part III  Passage One

Questions 26 to 28

(04:15) The city of Singapore has long been regarded as one of Asia's most livable cities. Despite its small size — it covers only about 720 square kilometers — Singapore has built a world-class public transportation system that moves millions of people every day.

**Question 26.** The government invested heavily in the Mass Rapid Transit, or MRT, system starting in the 1980s. Today the network spans over 200 kilometers and serves more than 130 stations.

**Question 27.** One key reason for its success is the integration of buses, trains, and cycling paths into a single ticketing system. Commuters can switch between modes of transport without buying a new ticket.

**Question 28.** Looking ahead, Singapore plans to expand the network by another 80 kilometers by 2030, with a focus on connecting suburban neighborhoods to the city center.

Answers: 26. C   27. A   28. B""",
}


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown(f'<div class="main-title">英语听力音频生成工具 <span style="font-size:1rem;font-weight:400;color:#888;">v{APP_VERSION}</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">❤️ Made by Duidui with love ❤️</div>',
            unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar — settings
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 设置", unsafe_allow_html=True)

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

    # DeepSeek API Key for script formatting
    _ds_key_from_env = _get_deepseek_key_from_env()
    if _ds_key_from_env:
        deepseek_key = _ds_key_from_env
        st.markdown("### 🤖 脚本优化（DeepSeek）")
        st.success("✅ DeepSeek API Key 已从环境变量加载")
    else:
        st.markdown("### 🤖 脚本优化（DeepSeek）")
        deepseek_key = st.text_input(
            "DeepSeek API Key",
            type="password",
            placeholder="sk-...",
            help="在 platform.deepseek.com 获取 API Key，用于自动优化脚本格式。",
        )

    st.markdown("---")
    st.caption("Love Zuozuo 🐱")


# ─────────────────────────────────────────────
# Right column renderer (defined before use)
# ─────────────────────────────────────────────
def _render_right_col(container, preview_text: str, formatted_text: str = None):
    from parser.script_parser import parse_script
    with container.container():
        st.markdown('<div class="sec-header">🔍 脚本预览</div>', unsafe_allow_html=True)
        if preview_text.strip():
            parsed = parse_script(preview_text)
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



# ─────────────────────────────────────────────
# Main content
# ─────────────────────────────────────────────
col_left, col_right = st.columns([3, 2], gap="large")

# Create col_right placeholder first so col_left's button handler can stream into it
with col_right:
    col_right_ph = st.empty()

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

    # ── Example selector ──────────────────────────────────────────────
    selected = st.selectbox("快速加载示例", list(EXAMPLES.keys()))
    if selected != "（选择示例快速体验）" and st.session_state.get("_last_example") != selected:
        st.session_state["script_input"] = EXAMPLES[selected]
        st.session_state["_last_example"] = selected

    # ── Script text area ──────────────────────────────────────────────
    script_text = st.text_area(
        "脚本输入区",
        height=340,
        placeholder="在这里粘贴听力原文…\n\nNumber 1.\n[Man]: Good morning!\n[Woman]: Hello there.",
        label_visibility="collapsed",
        key="script_input",
    )

    # ── Generate button (loading-state pattern) ───────────────────────
    can_gen = bool(script_text.strip()) and (provider != "openai" or openai_key)
    generating = st.session_state.get("_generating", False)

    if generating:
        # Show disabled button with loading label
        st.button("⏳ 正在生成中，请稍候…", type="primary", use_container_width=True,
                  key="gen_main_loading", disabled=True)
        status_ph = st.empty()
        progress_ph = st.empty()
        text_to_use = script_text

        # Step 1: DeepSeek formatting
        if deepseek_key and script_text.strip():
            status_ph.info("🤖 第一步：正在用 DeepSeek 优化脚本格式…")
            with col_right_ph.container():
                st.markdown('<div class="sec-header">🤖 DeepSeek 格式化中…</div>', unsafe_allow_html=True)
                stream_ph = st.empty()
            try:
                text_to_use = format_script_with_deepseek(script_text, deepseek_key, output_ph=stream_ph)
                st.session_state["script_input"] = text_to_use
                st.session_state["formatted_text"] = text_to_use
                print(f"[DeepSeek] ===== 格式化结果 =====\n{text_to_use}\n[DeepSeek] ===== 结果结束 =====", flush=True)
            except Exception as e:
                import traceback
                print(f"[DeepSeek] 异常: {e}\n{traceback.format_exc()}", flush=True)
                status_ph.warning(f"脚本格式化跳过（{e}），将直接合成原始文本。")

            # After DeepSeek: show parse preview + formatted text in right column
            _render_right_col(col_right_ph, text_to_use,
                              formatted_text=st.session_state.get("formatted_text"))

        # Step 2: TTS generation
        status_ph.info("🎙️ 第二步：正在合成音频，请稍候…")
        try:
            audio_bytes, slug = generate_audio_bytes(
                script_text=text_to_use,
                provider=provider, voice_a=voice_a, voice_b=voice_b,
                openai_key=openai_key, openai_model=openai_model, openai_speed=openai_speed,
                pause_between=pause_between, q_pause=q_pause,
                progress_ph=progress_ph,
            )
            st.session_state["audio_bytes"] = audio_bytes
            st.session_state["audio_slug"] = slug
            progress_ph.empty()
            status_ph.success("✅ 音频生成成功！")
        except Exception as e:
            progress_ph.empty()
            status_ph.error(f"音频生成失败：{e}")
            if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                st.info("请检查左侧面板中的 OpenAI API Key 是否正确。")

        st.session_state["_generating"] = False
        st.rerun()

    else:
        if st.button("🚀 一键生成音频", type="primary", use_container_width=True,
                     key="gen_main", disabled=not can_gen):
            st.session_state["_generating"] = True
            st.session_state["audio_bytes"] = None
            st.session_state["formatted_text"] = None
            st.rerun()

    # ── Persistent audio player ────────────────────────────────────────
    if st.session_state.get("audio_bytes"):
        st.audio(st.session_state["audio_bytes"], format="audio/mp3")
        st.download_button(
            label="⬇️ 下载 MP3",
            data=st.session_state["audio_bytes"],
            file_name=f"{st.session_state.get('audio_slug', 'audio')}.mp3",
            mime="audio/mpeg",
            use_container_width=True,
            type="primary",
        )

# Fill col_right (normal render pass, after col_left completes)
_render_right_col(
    col_right_ph,
    preview_text=st.session_state.get("formatted_text") or script_text,
    formatted_text=st.session_state.get("formatted_text"),
)

st.markdown("---")
st.markdown(
    '<div class="tip-box">💡 <b>新手建议</b>：先从上方「快速加载示例」选一个体验效果，'
    '再把听力原文按照 <code>[Man]: ...</code> / <code>[Woman]: ...</code> 格式粘贴进来即可。</div>',
    unsafe_allow_html=True,
)

