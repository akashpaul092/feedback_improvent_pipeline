"""Streamlit UI for AI Agent Evaluation Pipeline."""
import os
import streamlit as st
import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8726")


def main():
    st.set_page_config(
        page_title="AI Agent Evaluation Pipeline",
        page_icon="🤖",
        layout="wide",
    )
    st.title("🤖 AI Agent Evaluation Pipeline")
    st.markdown("Ingest conversations, run evaluations, and view improvement suggestions.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Ingest Conversation",
        "Run Evaluation",
        "View Results",
        "Improvement Suggestions",
        "Self-Healing (Calibration)",
    ])

    with tab1:
        st.subheader("Ingest a Conversation")
        with st.form("ingest_form"):
            conv_id = st.text_input("Conversation ID", value="conv_demo_001")
            agent_ver = st.text_input("Agent Version", value="v1.0.0")
            turns_json = st.text_area(
                "Turns (JSON)",
                value='''[
  {"turn_id": 1, "role": "user", "content": "Track my order ORD123", "timestamp": "2024-01-15T10:30:00Z"},
  {"turn_id": 2, "role": "assistant", "content": "Let me check...", "tool_calls": [{"tool_name": "track_order", "parameters": {"order_id": "ORD123"}, "result": {"status": "success", "status_text": "Out for delivery"}, "latency_ms": 320}], "timestamp": "2024-01-15T10:30:02Z"}
]''',
                height=200,
            )
            submitted = st.form_submit_button("Ingest")
            if submitted:
                try:
                    import json
                    turns = json.loads(turns_json)
                    with httpx.Client() as client:
                        r = client.post(
                            f"{API_URL}/conversations/ingest",
                            json={
                                "conversation_id": conv_id,
                                "agent_version": agent_ver,
                                "turns": turns,
                                "feedback": {"user_rating": 4},
                                "metadata": {"total_latency_ms": 1200, "mission_completed": True},
                            },
                            timeout=10,
                        )
                    if r.status_code == 200:
                        st.success(f"✅ Ingested! Status: {r.json().get('status', 'queued')}")
                    else:
                        st.error(f"Error: {r.text}")
                except Exception as e:
                    st.error(str(e))

    with tab2:
        st.subheader("Run Evaluation")
        conv_id_eval = st.text_input("Conversation ID to evaluate", value="conv_demo_001", key="eval_conv")
        if st.button("Run Evaluation"):
            try:
                with httpx.Client() as client:
                    r = client.post(
                        f"{API_URL}/evaluations/run/{conv_id_eval}",
                        timeout=30,
                    )
                if r.status_code == 200:
                    data = r.json()
                    st.json(data)
                else:
                    st.error(r.text)
            except Exception as e:
                st.error(str(e))

    with tab3:
        st.subheader("Evaluation Results")
        conv_filter = st.text_input("Filter by Conversation ID", key="filter_conv")
        agent_filter = st.text_input("Filter by Agent Version", key="filter_agent")
        if st.button("Fetch"):
            try:
                params = {}
                if conv_filter:
                    params["conversation_id"] = conv_filter
                if agent_filter:
                    params["agent_version"] = agent_filter
                with httpx.Client() as client:
                    r = client.get(f"{API_URL}/evaluations", params=params, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    st.metric("Total Evaluations", data["total"])
                    for ev in data["evaluations"][:10]:
                        with st.expander(f"📊 {ev['conversation_id']} - Overall: {ev['scores']['overall']}"):
                            st.json(ev)
                else:
                    st.error(r.text)
            except Exception as e:
                st.error(str(e))

    with tab4:
        st.subheader("Improvement Suggestions")
        if st.button("Load Suggestions"):
            try:
                with httpx.Client() as client:
                    r = client.get(f"{API_URL}/evaluations/suggestions", timeout=10)
                if r.status_code == 200:
                    for s in r.json().get("suggestions", []):
                        st.markdown(f"**{s.get('type', 'prompt').upper()}**: {s.get('suggestion')}")
                        st.caption(f"Rationale: {s.get('rationale')} | Confidence: {s.get('confidence', 0):.2f}")
                        st.divider()
                else:
                    st.error(r.text)
            except Exception as e:
                st.error(str(e))

    with tab5:
        st.subheader("Self-Healing: Calibrate Evaluators")
        st.markdown("Compare evaluator scores with human annotations. Update calibration when they diverge.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Run Calibration"):
                try:
                    with httpx.Client() as client:
                        r = client.post(f"{API_URL}/evaluations/calibrate", timeout=30)
                    if r.status_code == 200:
                        data = r.json()
                        st.success("Calibration complete!")
                        st.json(data.get("calibration", {}))
                        if data.get("blind_spots"):
                            st.warning("Blind spots detected (human said bad, evaluator said good):")
                            for b in data["blind_spots"][:5]:
                                st.json(b)
                    else:
                        st.error(r.text)
                except Exception as e:
                    st.error(str(e))
        with col2:
            if st.button("📊 View Current Calibration"):
                try:
                    with httpx.Client() as client:
                        r = client.get(f"{API_URL}/evaluations/calibration", timeout=10)
                    if r.status_code == 200:
                        st.json(r.json().get("calibration", {}))
                    else:
                        st.error(r.text)
                except Exception as e:
                    st.error(str(e))
        st.caption("Add human annotations via POST /feedback/annotations/{conversation_id} with type (tool_accuracy, response_quality, coherence) and label (correct/incorrect, good/bad).")


if __name__ == "__main__":
    main()
