"""TrustGuard - AI answer verification dashboard."""

import os
import html
import streamlit as st

from config.settings import get_settings
from core.meta_client import MetaClient, MetaAPIError
from core.document_processor import load_document, chunk_document
from core.retrieval import TfidfRetriever
from core.pipeline import (
    run_pipeline,
    revise_and_reverify,
    verify_provided_answer,
    needs_revision,
)


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

SAMPLE_DIR = os.path.join(
    os.path.dirname(__file__),
    "sample_docs",
)

COLORS = {
    "ALLOW": "#15803d",
    "FLAG": "#c2410c",
    "BLOCK": "#b91c1c",
    "REVISE": "#1d4ed8",
}

STATUS_TITLES = {
    "ALLOW": "Answer verified",
    "FLAG": "Review recommended",
    "BLOCK": "Answer withheld",
    "REVISE": "Answer needs correction",
}

ICONS = {
    "SUPPORTED": "✅",
    "CONTRADICTED": "❌",
    "UNVERIFIED": "❔",
    "CURRENT": "🟢",
    "POTENTIALLY OUTDATED": "🟠",
    "UNKNOWN": "⚪",
}

MEANING = {
    "ALLOW": "Every claim is supported by the retrieved evidence.",
    "FLAG": (
        "Review recommended: some claims are unverified "
        "or the evidence may be outdated."
    ),
    "BLOCK": (
        "The answer has been withheld because it is not reliable."
    ),
    "REVISE": (
        "Some claims conflict with the evidence and need correction."
    ),
}


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="TrustGuard | AI Answer Verification",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------

st.markdown(
    """
    <style>

    /* Overall application */
    .stApp {
        background-color: #0b1120;
        color: #e2e8f0;
    }

    /* Main content */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #263244;
    }

    section[data-testid="stSidebar"] h2 {
        font-size: 1.05rem;
        color: #f8fafc;
    }

    /* Headings */
    h1, h2, h3 {
        color: #f8fafc !important;
    }

    /* Captions */
    .stCaption {
        color: #94a3b8 !important;
    }

    /* Input fields */
    .stTextInput input,
    .stTextArea textarea {
        background-color: #172033;
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 10px;
    }

    /* Buttons */
    .stButton button {
        border-radius: 9px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    /* Primary button */
    .stButton button[kind="primary"] {
        background-color: #6366f1;
        color: white;
        border: none;
    }

    /* Button hover */
    .stButton button:hover {
        border-color: #818cf8;
        color: #ffffff;
    }

    /* Verification banner */
    .tg-banner {
        padding: 16px 20px;
        border-radius: 14px;
        color: #ffffff;
        margin: 16px 0 22px 0;
        border: 1px solid rgba(255,255,255,0.12);
    }

    .tg-banner h2 {
        margin: 0;
        color: #ffffff;
        font-size: 1.35rem;
    }

    .tg-banner p {
        margin: 8px 0 0 0;
        opacity: 0.95;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* Answer card */
    .tg-answer {
        background: #172033;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        font-size: 1.1rem;
        color: #f8fafc;
        line-height: 1.6;
        margin: 10px 0 20px 0;
    }

    /* Tables */
    [data-testid="stDataFrame"] {
        border: 1px solid #263244;
        border-radius: 10px;
        overflow: hidden;
    }

    /* Alerts */
    div[data-testid="stAlert"] {
        border-radius: 10px;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        font-weight: 600;
    }

    /* File uploader */
    div[data-testid="stFileUploader"] {
        border-radius: 10px;
    }

    /* Horizontal separators */
    hr {
        border-color: #263244;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.title("🛡️ TrustGuard")

st.markdown(
    """
    <div style="
        font-size:1.1rem;
        color:#a5b4fc;
        font-weight:600;
        margin-bottom:8px;
    ">
        AI answers. Verified against evidence.
    </div>
    """,
    unsafe_allow_html=True,
)

st.write(
    "TrustGuard checks AI-generated answers against your documents "
    "before presenting them as reliable."
)


# ---------------------------------------------------------
# VERIFICATION BANNER
# ---------------------------------------------------------

def banner(d, prefix=""):
    """Display a clear verification result banner."""

    title = STATUS_TITLES.get(
        d.label,
        d.label,
    )

    color = COLORS.get(
        d.label,
        "#334155",
    )

    st.markdown(
        f"""
        <div class="tg-banner" style="background:{color}">
            <h2>{prefix}{title}</h2>
            <p>{d.headline or MEANING.get(d.label, "")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Intentionally do not repeat d.reasons here.
    # Detailed claim-level explanations are shown below.


# ---------------------------------------------------------
# ANSWER CARD
# ---------------------------------------------------------

def answer_card(answer):
    """Display an answer in a prominent styled card."""

    safe_answer = html.escape(
        str(answer or "")
    )

    st.markdown(
        f"""
        <div class="tg-answer">
            {safe_answer}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# CLAIM VERIFICATION TABLE
# ---------------------------------------------------------

def claims_table(results):
    """Display extracted claims and verification results."""

    if not results:
        st.write(
            "No individual factual claims were extracted "
            "from this answer."
        )
        return

    st.dataframe(
        [
            {
                "": ICONS.get(x.label, ""),
                "Claim": x.claim,
                "Verdict": x.label,
                "Source": x.source or "—",
                "Why": x.explanation,
            }
            for x in results
        ],
        hide_index=True,
        use_container_width=True,
    )

    for i, x in enumerate(results, 1):

        if x.evidence_text:

            with st.expander(
                f"{ICONS.get(x.label, '')} Claim {i} evidence · {x.source}"
            ):

                st.markdown(
                    f"**Claim:** {x.claim}"
                )

                st.markdown(
                    f"**Matching text:** _{x.quote}_"
                )

                st.caption(
                    "Supporting passage:"
                )

                st.write(
                    x.evidence_text
                )


# ---------------------------------------------------------
# DEMO PRESETS
# ---------------------------------------------------------

PRESETS = {
    "✅ Correct answer": (
        "How many days do I have to request a refund?",
        (
            "You can request a refund within 30 days of purchase "
            "by emailing support@examplestore.com."
        ),
    ),

    "❌ Wrong answer": (
        "How many days do I have to request a refund?",
        (
            "You can request a refund within 60 days of purchase "
            "by calling our phone support line."
        ),
    ),

    "❔ Made-up details": (
        "How does the warranty work?",
        (
            "The warranty lasts 1 year, and a replacement is "
            "shipped free of charge within 48 hours."
        ),
    ),
}


def set_preset(q, a):
    """Populate demo question and answer fields."""

    st.session_state["demo_q"] = q
    st.session_state["demo_a"] = a


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

settings = get_settings()


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:

    st.header("📚 Your documents")

    st.caption(
        "Upload policies, reports, and other documents "
        "for TrustGuard to use as evidence."
    )

    uploads = st.file_uploader(
        "Upload PDF, TXT or Markdown",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
    )

    use_samples = st.checkbox(
        "Use sample documents",
        value=not uploads,
    )

    docs = []

    # Load sample documents
    if use_samples and os.path.isdir(SAMPLE_DIR):

        for fn in sorted(os.listdir(SAMPLE_DIR)):

            if fn.lower().endswith(
                (".md", ".txt", ".pdf")
            ):

                with open(
                    os.path.join(SAMPLE_DIR, fn),
                    "rb",
                ) as fh:

                    docs.append(
                        load_document(
                            fn,
                            fh.read(),
                        )
                    )

    # Load uploaded documents
    for up in uploads or []:

        docs.append(
            load_document(
                up.name,
                up.getvalue(),
            )
        )

    # Create document chunks
    chunks = [
        c
        for d in docs
        if d.ok
        for c in chunk_document(d)
    ]

    # Build retriever
    retriever = TfidfRetriever(chunks)

    # Display document list
    for d in docs:

        if d.ok:

            st.success(
                f"📄 {d.name} · Updated "
                f"{d.last_updated or 'unknown'}"
            )

        else:

            st.error(
                f"❌ {d.name}: {d.error}"
            )

    st.caption(
        f"{sum(d.ok for d in docs)} document(s) · "
        f"{len(chunks)} passages indexed"
    )

    st.divider()

    # Verification settings
    st.header("🛡️ Answer protection")

    verify = st.toggle(
        "Verify answers with TrustGuard",
        value=True,
    )

    st.caption(
        "Turn off to compare the original AI answer "
        "without verification."
    )

    st.divider()

    # Model connection status
    if settings.api_key:

        st.caption(
            "🟢 AI model connected"
        )

    else:

        st.caption(
            "🔴 AI model not configured"
        )


# ---------------------------------------------------------
# MAIN QUESTION INPUT
# ---------------------------------------------------------

st.subheader("Ask your documents")

st.caption(
    "Get an answer based on your uploaded policies, "
    "reports, and other documents."
)

question = st.text_input(
    "Your question",
    placeholder=(
        "e.g. How many days do I have "
        "to request a refund?"
    ),
    label_visibility="collapsed",
)

if st.button(
    "🔍 Verify answer",
    type="primary",
    use_container_width=True,
):

    if not question.strip():

        st.warning(
            "Please enter a question."
        )

    elif not chunks:

        st.warning(
            "No documents loaded. Upload a file "
            "or enable sample documents in the sidebar."
        )

    else:

        try:

            with st.spinner(
                "Checking your documents and verifying the answer..."
            ):

                st.session_state["result"] = run_pipeline(
                    MetaClient(settings),
                    retriever,
                    question,
                    verify,
                )

        except MetaAPIError as e:

            st.session_state.pop(
                "result",
                None,
            )

            st.error(
                f"Meta API error: {e}"
            )


# ---------------------------------------------------------
# DEMO MODE
# ---------------------------------------------------------

with st.expander(
    "🧪 Try an example: verify an existing answer"
):

    st.caption(
        "Test TrustGuard with correct, incorrect, or made-up answers. "
        "This demonstrates how it checks answers against your documents."
    )

    cols = st.columns(
        len(PRESETS)
    )

    for col, (name, (pq, pa)) in zip(
        cols,
        PRESETS.items(),
    ):

        col.button(
            name,
            on_click=set_preset,
            args=(pq, pa),
            key=f"preset_{name}",
        )

    demo_q = st.text_input(
        "Question",
        key="demo_q",
    )

    demo_a = st.text_area(
        "Answer to check",
        key="demo_a",
        height=100,
    )

    if st.button(
        "Verify this answer",
        use_container_width=True,
    ):

        if not demo_q.strip() or not demo_a.strip():

            st.warning(
                "Enter both a question and an answer."
            )

        elif not chunks:

            st.warning(
                "No documents loaded."
            )

        else:

            try:

                with st.spinner(
                    "Verifying the provided answer..."
                ):

                    st.session_state["result"] = (
                        verify_provided_answer(
                            MetaClient(settings),
                            retriever,
                            demo_q,
                            demo_a,
                        )
                    )

            except MetaAPIError as e:

                st.error(
                    f"Meta API error: {e}"
                )


# ---------------------------------------------------------
# DISPLAY RESULTS
# ---------------------------------------------------------

r = st.session_state.get("result")

if r:

    # No evidence found
    if not r.evidence:

        st.warning(
            "⚠️ No relevant evidence was found in the documents. "
            "TrustGuard will not present an answer as verified "
            "without evidence, so no answer was generated."
        )

    else:

        # Decision banner
        if r.decision:

            banner(
                r.decision
            )

        # Answer heading
        if r.answer_source == "provided":

            st.subheader(
                "💬 Answer under test"
            )

            st.caption(
                "This answer was provided in demo mode. "
                "It was not generated by the model."
            )

        else:

            st.subheader(
                "💬 Answer"
            )

        # Blocked answer
        if (
            r.decision
            and r.decision.label == "BLOCK"
        ):

            st.error(
                "TrustGuard has withheld this answer "
                "because it is not reliable."
            )

            with st.expander(
                "Show the blocked answer anyway"
            ):

                answer_card(
                    r.answer
                )

        # Normal answer
        elif r.verified:

            answer_card(
                r.answer
            )

        else:

            answer_card(
                r.answer
            )

            st.caption(
                "Verification is off. "
                "This answer has NOT been checked."
            )

        # -------------------------------------------------
        # VERIFICATION DETAILS
        # -------------------------------------------------

        if r.verified:

            st.subheader(
                "🛡️ Verification details"
            )

            claims_table(
                r.results
            )

            st.caption(
                f"Claims extracted by: {r.extraction_method} · "
                f"verified by: {r.verification_method}"
                + (
                    " ⚠️ The AI judge was unavailable, so a simpler "
                    "word-matching check was used. It cannot detect "
                    "contradictions."
                    if r.verification_method == "lexical-fallback"
                    else ""
                )
            )

            # -------------------------------------------------
            # ANSWER REVISION
            # -------------------------------------------------

            if (
                r.revision is None
                and r.decision.label != "ALLOW"
            ):

                if needs_revision(r):

                    st.info(
                        "Some claims are incorrect or unverified. "
                        "TrustGuard can rewrite the answer using "
                        "only what the evidence supports, then "
                        "check the revised answer again."
                    )

                    if st.button(
                        "✨ Revise answer with TrustGuard",
                        type="primary",
                        use_container_width=True,
                    ):

                        try:

                            with st.spinner(
                                "Revising and re-verifying..."
                            ):

                                r.revision = (
                                    revise_and_reverify(
                                        MetaClient(settings),
                                        r,
                                    )
                                )

                        except MetaAPIError as e:

                            st.error(
                                "Revision failed. "
                                "The original answer is unchanged: "
                                f"{e}"
                            )

                else:

                    st.info(
                        "Revision would not help here. "
                        "The claims match the evidence, but the "
                        "source itself may be outdated or undated. "
                        "The document should be updated or confirmed."
                    )

            # -------------------------------------------------
            # REVISED ANSWER
            # -------------------------------------------------

            if r.revision:

                rv = r.revision

                st.subheader(
                    "✨ Revised answer"
                )

                left, right = st.columns(
                    2
                )

                with left:

                    st.markdown(
                        "**Original answer**"
                    )

                    if r.decision.label == "BLOCK":

                        st.write(
                            "_Withheld by TrustGuard_"
                        )

                    else:

                        answer_card(
                            r.answer
                        )

                    st.caption(
                        f"Original status: {r.decision.label}"
                    )

                with right:

                    st.markdown(
                        "**Revised answer**"
                    )

                    answer_card(
                        rv.answer
                    )

                    st.caption(
                        "The revised answer was verified again "
                        "against the same evidence."
                        + (
                            " No changes were needed."
                            if rv.answer.strip()
                            == (r.answer or "").strip()
                            else ""
                        )
                    )

                banner(
                    rv.decision,
                    prefix="Final status after revision: ",
                )

                st.markdown(
                    "**Verification of the revised answer**"
                )

                claims_table(
                    rv.results
                )

        # -------------------------------------------------
        # DOCUMENT FRESHNESS
        # -------------------------------------------------

        st.subheader(
            "📅 Document freshness"
        )

        st.dataframe(
            [
                {
                    "": ICONS.get(f.status, ""),
                    "Source": f.source,
                    "Last updated": f.last_updated or "Unknown",
                    "Age (days)": (
                        f.age_days
                        if f.age_days is not None
                        else "—"
                    ),
                    "Status": f.status,
                }
                for f in r.freshness
            ],
            hide_index=True,
            use_container_width=True,
        )

        st.caption(
            "Dates come only from the documents themselves. "
            "Missing dates are shown as unknown, never guessed. "
            "'Potentially outdated' means older than 365 days."
        )

        # -------------------------------------------------
        # SOURCES USED
        # -------------------------------------------------

        st.subheader(
            "📖 Sources used"
        )

        for i, e in enumerate(
            r.evidence,
            1,
        ):

            with st.expander(
                f"[{i}] {e.source} · "
                f"Relevance {e.score:.2f} · "
                f"Updated {e.last_updated or 'unknown'}"
            ):

                st.write(
                    e.text
                )

    # -----------------------------------------------------
    # DISCLAIMER
    # -----------------------------------------------------

    st.caption(
        "TrustGuard's checks are probabilistic and limited "
        "to the uploaded documents. ALLOW means 'supported "
        "by the evidence found', not 'guaranteed true'."
    )