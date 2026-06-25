#!/usr/bin/env python3
"""
Streamlit Web Dashboard for the TikTok Video Library.

Museum-aesthetic UI inspired by microsoft.ai design language:
  - Split-text word reveals on scroll
  - Blur-focus entrance animations
  - Warm cream palette (#fef9ed) with brown-grey text (#5d524b)
  - Bradford LL serif headings, Red Hat Mono body
  - Noise texture overlay
  - Luxurious easing curves

Run:
    streamlit run src/app.py
"""
import os
import sys
from pathlib import Path

import streamlit as st

# Allow imports from the src directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai import store  # noqa: E402

DB_PATH = os.environ.get("VIDEO_INDEX_DB", "video_index.db")

# ── Page config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="Video Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────
# Adapted from microsoft.ai's design system (Bradford LL + Red Hat Mono,
# warm cream background, split-text reveals, blur-focus transitions,
# slide-up entrances, noise overlay, tag pills).

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Red+Hat+Mono:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600&display=swap');

/* ── CSS Custom Properties (from tokens.json) ────────────────────── */
:root {
    --text-color: #5d524b;
    --background-color: #fef9ed;
    --surface-pastel: #fbd3be;
    --cta-background: #f7ecd9;
    --tag-background: #f5eee0;
    --easeOut: cubic-bezier(.43, .195, .02, 1);
    --easeOutQuint: cubic-bezier(.23, 1, .32, 1);
    --easeOutSlow: cubic-bezier(.43, .195, .02, 1);
    --easeOutCubic: cubic-bezier(.215, .61, .355, 1);
}

/* ── Base Reset ──────────────────────────────────────────────────── */
html, body, [class*="st-"] {
    font-family: "Red Hat Mono", ui-monospace, SFMono-Regular, monospace;
    -webkit-font-smoothing: antialiased;
    color: var(--text-color);
}

::selection {
    color: #5d524b;
    text-shadow: none;
    background-color: #f5eee0;
}

/* ── Typography ──────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    font-family: "Playfair Display", "Bradford LL", "Times New Roman", Times, serif !important;
    color: var(--text-color) !important;
    font-weight: 400 !important;
    letter-spacing: -0.03em !important;
    line-height: 1 !important;
}

p, span, div {
    color: var(--text-color);
}

/* ── Keyframe Animations (from microsoft.ai) ─────────────────────── */

/* slide-up: translateY(20%) -> 0 with 1.8s easeOutSlow */
@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(20%) translateZ(0);
    }
    to {
        opacity: 1;
        transform: translateY(0) translateZ(0);
    }
}

/* blur-focus: blur(20px) + translateY(10%) -> clear */
@keyframes blurFocus {
    from {
        opacity: 0;
        filter: blur(20px);
        transform: translateY(10%);
    }
    to {
        opacity: 1;
        filter: blur(0);
        transform: translateY(0%);
    }
}

/* scale-out: scale(1.2) -> 1 with 2.3s easeOut */
@keyframes scaleOut {
    from {
        transform: scale(1.15) translateZ(0);
    }
    to {
        transform: scale(1) translateZ(0);
    }
}

/* fade-in: opacity 0 -> 1 with 1.8s easeOut */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* split-text word reveal: translateY(100%) -> 0 per word */
@keyframes wordReveal {
    from {
        opacity: 0;
        transform: translateY(100%) translateZ(0);
    }
    to {
        opacity: 1;
        transform: translateY(0%) translateZ(0);
    }
}

/* slide-left: translateX(100px) -> 0 */
@keyframes slideLeft {
    from {
        opacity: 0;
        transform: translateX(60px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* ── Result Card ─────────────────────────────────────────────────── */
.result-card {
    background: transparent;
    border: 1px solid var(--text-color);
    border-radius: 0;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: background-color 0.6s var(--easeOutCubic),
                color 0.6s var(--easeOutCubic);
    animation: slideUp 1.8s var(--easeOutSlow) both;
}
.result-card:hover {
    background: var(--surface-pastel);
}

/* Stagger entrance for result cards */
.result-card:nth-child(1) { animation-delay: 0s; }
.result-card:nth-child(2) { animation-delay: 0.07s; }
.result-card:nth-child(3) { animation-delay: 0.14s; }
.result-card:nth-child(4) { animation-delay: 0.21s; }
.result-card:nth-child(5) { animation-delay: 0.28s; }
.result-card:nth-child(6) { animation-delay: 0.35s; }
.result-card:nth-child(7) { animation-delay: 0.42s; }
.result-card:nth-child(8) { animation-delay: 0.49s; }
.result-card:nth-child(9) { animation-delay: 0.56s; }
.result-card:nth-child(10) { animation-delay: 0.63s; }

/* ── Tag / Pill (from microsoft.ai .tag class) ───────────────────── */
.tag-pill {
    display: inline-block;
    background-color: var(--tag-background);
    color: var(--text-color);
    text-transform: uppercase;
    font-family: "Red Hat Mono", monospace;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    padding: 0.25rem 0.75rem;
    border-radius: 3px;
    margin: 0.15rem;
    transition: background-color 0.6s var(--easeOutCubic);
}
.tag-pill:hover {
    background-color: var(--surface-pastel);
}

/* ── Score Badge ──────────────────────────────────────────────────── */
.score-badge {
    display: inline-block;
    background: transparent;
    color: var(--text-color);
    padding: 0.15rem 0.5rem;
    border-radius: 0;
    font-size: 0.75rem;
    font-weight: 500;
    border: 1px solid var(--text-color);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* ── Metric Card ─────────────────────────────────────────────────── */
.metric-card {
    background: transparent;
    border: 1px solid var(--text-color);
    border-radius: 0;
    padding: 2rem 1.5rem;
    text-align: left;
    animation: blurFocus 1.8s var(--easeOut) both;
}
.metric-card:nth-child(1) { animation-delay: 0.1s; }
.metric-card:nth-child(2) { animation-delay: 0.2s; }
.metric-card:nth-child(3) { animation-delay: 0.3s; }
.metric-card:nth-child(4) { animation-delay: 0.4s; }

.metric-card h2 {
    font-size: 3.5rem !important;
    font-weight: 400 !important;
    color: var(--text-color) !important;
    margin: 0;
    letter-spacing: -0.04em !important;
    line-height: 0.97 !important;
}
.metric-card p {
    color: var(--text-color);
    font-size: 0.7rem;
    font-weight: 500;
    margin: 0.75rem 0 0 0;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* ── Page Title (split-text style word reveal) ────────────────────── */
.page-title {
    font-family: "Playfair Display", "Bradford LL", "Times New Roman", serif;
    font-size: 3.5rem;
    font-weight: 400;
    letter-spacing: -0.04em;
    line-height: 1;
    color: var(--text-color);
    overflow: hidden;
}

.page-title .word {
    display: inline-block;
    animation: wordReveal 1.3s var(--easeOut) both;
}
.page-title .word:nth-child(1) { animation-delay: 0s; }
.page-title .word:nth-child(2) { animation-delay: 0.05s; }
.page-title .word:nth-child(3) { animation-delay: 0.1s; }
.page-title .word:nth-child(4) { animation-delay: 0.15s; }
.page-title .word:nth-child(5) { animation-delay: 0.2s; }

/* ── Subtitle ────────────────────────────────────────────────────── */
.page-subtitle {
    color: var(--text-color);
    font-size: 0.85rem;
    font-weight: 400;
    letter-spacing: -0.01em;
    line-height: 1.6;
    margin-top: 0.5rem;
    animation: fadeIn 1.8s 0.3s var(--easeOut) both;
}

/* ── Sidebar ─────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: var(--background-color);
    border-right: 1px solid var(--text-color);
}

/* ── Section Heading (like microsoft.ai .text-headline) ──────────── */
.section-heading {
    font-family: "Red Hat Mono", monospace;
    font-size: 0.7rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-color);
    margin-top: 2rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--text-color);
    animation: slideLeft 1.8s var(--easeOutSlow) both;
}

/* ── Transcript Quote ────────────────────────────────────────────── */
.transcript-quote {
    border-left: 1px solid var(--text-color);
    padding-left: 1rem;
    color: var(--text-color);
    font-family: "Playfair Display", "Bradford LL", serif;
    font-style: italic;
    font-size: 0.95rem;
    line-height: 1.25;
    margin-top: 0.75rem;
}

/* ── Timestamp Badge ─────────────────────────────────────────────── */
.ts-badge {
    display: inline-block;
    background: var(--tag-background);
    border: none;
    color: var(--text-color);
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── Noise Texture Overlay ───────────────────────────────────────── */
.noise-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 9999;
    mix-blend-mode: soft-light;
    opacity: 0.08;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 256px;
}

/* ── Streamlit Overrides ─────────────────────────────────────────── */
.stTextInput input {
    border-radius: 0 !important;
    border: 1px solid var(--text-color) !important;
    padding: 0.75rem 1rem !important;
    box-shadow: none !important;
    background: transparent !important;
    color: var(--text-color) !important;
    font-family: "Red Hat Mono", monospace !important;
    font-size: 0.85rem !important;
    transition: border-color 0.6s var(--easeOutCubic) !important;
}
.stTextInput input:focus {
    border-color: var(--text-color) !important;
    box-shadow: none !important;
    outline: 1px solid var(--text-color) !important;
    outline-offset: 2px !important;
}
.stTextInput input::placeholder {
    color: #a89f96 !important;
    font-style: italic !important;
}

/* Expander animation */
[data-testid="stExpander"] {
    animation: slideUp 1.8s var(--easeOutSlow) both;
    border-color: var(--text-color) !important;
    border-radius: 0 !important;
}
[data-testid="stExpander"]:nth-child(1) { animation-delay: 0.05s; }
[data-testid="stExpander"]:nth-child(2) { animation-delay: 0.1s; }
[data-testid="stExpander"]:nth-child(3) { animation-delay: 0.15s; }
[data-testid="stExpander"]:nth-child(4) { animation-delay: 0.2s; }
[data-testid="stExpander"]:nth-child(5) { animation-delay: 0.25s; }

/* Button pill style (from microsoft.ai .button--primary) */
.stButton > button {
    background-color: var(--cta-background) !important;
    color: var(--text-color) !important;
    border: none !important;
    border-radius: 2em !important;
    font-family: "Red Hat Mono", monospace !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    padding: 0.75em 2em !important;
    transition: color 0.6s var(--easeOutCubic),
                background-color 0.6s var(--easeOutCubic) !important;
}
.stButton > button:hover {
    background-color: var(--text-color) !important;
    color: var(--background-color) !important;
}

/* Radio buttons */
[data-testid="stRadio"] label {
    font-family: "Red Hat Mono", monospace !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* Dataframe / table */
[data-testid="stDataFrame"] {
    animation: fadeIn 1.8s 0.2s var(--easeOut) both;
    border-radius: 0 !important;
}

/* Spinner */
.stSpinner {
    animation: fadeIn 0.5s var(--easeOut) both;
}

/* Divider */
[data-testid="stHorizontalRule"] {
    border-color: var(--text-color) !important;
    opacity: 0.3;
}
</style>
""", unsafe_allow_html=True)

# ── Noise overlay (like microsoft.ai) ────────────────────────────────
st.markdown('<div class="noise-overlay"></div>', unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────


def _fmt_ts(seconds):
    if seconds is None:
        return "--:--"
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _split_text(text):
    """Wrap each word in a span for staggered word-reveal animation."""
    words = text.split()
    spans = " ".join(
        f'<span class="word">{w}</span>' for w in words
    )
    return spans


def _render_metric(label, value):
    st.markdown(f"""
    <div class="metric-card">
        <h2>{value}</h2>
        <p>{label}</p>
    </div>
    """, unsafe_allow_html=True)


def _render_result(hit, rank):
    ts = _fmt_ts(hit.get("start"))
    score = hit.get("score", 0)
    text = hit.get("text", "")
    video_id = hit.get("video_id", "")
    path = hit.get("path", "")

    st.markdown(f"""
    <div class="result-card">
        <div style="display: flex; justify-content: space-between;
                    align-items: center; margin-bottom: 0.75rem;">
            <span style="font-size: 0.85rem; font-weight: 500;
                         letter-spacing: 0.05em; text-transform: uppercase;">
                NO. {rank} &mdash; {video_id}
            </span>
            <span>
                <span class="score-badge">{score:.3f}</span>
                &nbsp;
                <span class="ts-badge">{ts}</span>
            </span>
        </div>
        <div class="transcript-quote">{text}</div>
        <div style="margin-top: 0.75rem; font-size: 0.7rem;
                    letter-spacing: 0.1em; text-transform: uppercase;">
            {path}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Show inline video player if the file exists.
    video_path = Path(path)
    if video_path.exists():
        start_sec = int(hit.get("start") or 0)
        with st.expander(f"PLAY {video_id} AT {ts}", expanded=False):
            st.video(str(video_path), start_time=start_sec)


# ── Sidebar navigation ──────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="page-title" style="font-size: 1.5rem; '
        'margin-bottom: 0.25rem;">'
        f'{_split_text("Video Intelligence")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size: 0.7rem; letter-spacing: 0.1em; '
        'text-transform: uppercase; margin-top: 0;">AI-Powered Library</p>',
        unsafe_allow_html=True,
    )
    st.divider()
    page = st.radio(
        "Navigate",
        ["Search", "Library", "Topics"],
        label_visibility="collapsed",
    )
    st.divider()

    # Quick stats in sidebar
    s = store.stats(DB_PATH)
    st.markdown(f"""
    <div style="font-size: 0.75rem; line-height: 2.2;
                text-transform: uppercase; letter-spacing: 0.1em;">
        <strong>{s['videos']}</strong> Videos<br>
        <strong>{s['segments']}</strong> Segments<br>
        <strong>{s['frames']}</strong> Frames<br>
        <strong>{s['clusters']}</strong> Clusters
    </div>
    """, unsafe_allow_html=True)


# ── Page: Search ─────────────────────────────────────────────────────

if page == "Search":
    st.markdown(
        '<div class="page-title">'
        f'{_split_text("Semantic Video Search")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="page-subtitle">'
        'Describe what you are looking for in plain English. '
        'The system searches by meaning, not keywords.</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        query = st.text_input(
            "Search query",
            placeholder="someone demoing the product outdoors...",
            label_visibility="collapsed",
        )
    with col2:
        top_k = st.number_input("Results", min_value=1, max_value=50,
                                value=5, label_visibility="collapsed")
    with col3:
        search_mode = st.selectbox(
            "Mode",
            ["Text", "Visual"],
            label_visibility="collapsed",
        )

    if query:
        with st.spinner("Searching ..."):
            if search_mode == "Visual":
                results = store.search_visual(DB_PATH, query,
                                              top_k=int(top_k))
                mode_label = "visual"
            else:
                results = store.search(DB_PATH, query,
                                       top_k=int(top_k))
                mode_label = "transcript"

        if results:
            st.markdown(
                f'<div class="section-heading">'
                f'{len(results)} {mode_label} results for '
                f'&ldquo;{query}&rdquo;</div>',
                unsafe_allow_html=True,
            )
            for rank, hit in enumerate(results, 1):
                _render_result(hit, rank)
        else:
            st.markdown(
                '<p class="page-subtitle" style="margin-top: 2rem;">'
                'No matches found. Try a different query '
                'or enrich more videos.</p>',
                unsafe_allow_html=True,
            )

# ── Page: Library ────────────────────────────────────────────────────

elif page == "Library":
    st.markdown(
        '<div class="page-title">'
        f'{_split_text("Video Library")}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Metric cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _render_metric("Videos Indexed", s["videos"])
    with col2:
        _render_metric("Text Segments", s["segments"])
    with col3:
        _render_metric("Visual Frames", s["frames"])
    with col4:
        _render_metric("Topic Clusters", s["clusters"])

    # Video list from DB
    if s["videos"] > 0:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        try:
            rows = conn.execute(
                "SELECT video_id, path, language, duration, enriched_at "
                "FROM videos ORDER BY enriched_at DESC"
            ).fetchall()
        finally:
            conn.close()

        if rows:
            st.markdown(
                '<div class="section-heading">Indexed Videos</div>',
                unsafe_allow_html=True,
            )
            import pandas as pd
            df = pd.DataFrame(rows, columns=[
                "Video ID", "Path", "Language", "Duration (s)",
                "Enriched At"
            ])
            df["Duration (s)"] = df["Duration (s)"].round(1)
            st.dataframe(
                df, use_container_width=True, hide_index=True,
                height=400,
            )

            # Language breakdown
            if df["Language"].notna().any():
                st.markdown(
                    '<div class="section-heading">Languages</div>',
                    unsafe_allow_html=True,
                )
                lang_counts = (
                    df["Language"].value_counts().reset_index()
                )
                lang_counts.columns = ["Language", "Count"]
                st.bar_chart(lang_counts.set_index("Language"))

            # Duration histogram
            valid_dur = df[df["Duration (s)"] > 0]["Duration (s)"]
            if not valid_dur.empty:
                st.markdown(
                    '<div class="section-heading">'
                    'Duration Distribution</div>',
                    unsafe_allow_html=True,
                )
                st.bar_chart(valid_dur.value_counts(bins=20).sort_index())
    else:
        st.markdown(
            '<p class="page-subtitle" style="margin-top: 2rem;">'
            'No videos indexed yet. Run enrich_videos.py to begin.</p>',
            unsafe_allow_html=True,
        )


# ── Page: Topics ─────────────────────────────────────────────────────

elif page == "Topics":
    st.markdown(
        '<div class="page-title">'
        f'{_split_text("Topic Clusters")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="page-subtitle">'
        'Auto-discovered topic groups from your video library. '
        'Clustering by HDBSCAN, labels by TF-IDF.</p>',
        unsafe_allow_html=True,
    )

    clusters = store.get_clusters(DB_PATH)
    if not clusters:
        st.markdown(
            '<p class="page-subtitle" style="margin-top: 2rem;">'
            'No clusters yet. Run cluster_videos.py to '
            'auto-tag your library.</p>',
            unsafe_allow_html=True,
        )
    else:
        for c in clusters:
            cid = c["cluster_id"]
            label = c["label"]
            vids = c["video_ids"]
            count = len(vids)

            if cid == -1:
                header = f"Unclustered ({count} videos)"
            else:
                header = f"Cluster {cid} \u2014 \"{label}\" ({count} videos)"

            with st.expander(header, expanded=(cid != -1)):
                # Show cluster tags as pills
                tags_html = "".join(
                    f'<span class="tag-pill">{t.strip()}</span>'
                    for t in label.split(",")
                )
                st.markdown(
                    f'<div style="margin-bottom: 0.75rem;">'
                    f'{tags_html}</div>',
                    unsafe_allow_html=True,
                )

                # List videos in this cluster
                for vid in vids[:50]:  # cap display at 50
                    st.markdown(
                        f'<div style="padding: 0.25rem 0;'
                        f' font-size: 0.8rem; letter-spacing: 0.05em;'
                        f' text-transform: uppercase;">{vid}</div>',
                        unsafe_allow_html=True,
                    )
                if len(vids) > 50:
                    st.caption(f"... and {len(vids) - 50} more")
