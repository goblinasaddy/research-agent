import streamlit as st
import sys
import os
import json
import time

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from research_agent.utils import LLMClient, setup_logger
from research_agent.planner import Planner
from research_agent.executor import Executor
from research_agent.synthesizer import Synthesizer
from research_agent.verifier import Verifier
from research_agent.schema import ResearchPlan

st.set_page_config(page_title="Agentic Research Assistant", layout="wide")

# Custom CSS for "Architecture" feel
st.markdown("""
<style>
    .stExpander { border: 1px solid #ddd; border-radius: 5px; }
    .step-box { padding: 10px; margin: 5px 0; border-left: 4px solid #4CAF50; background-color: #f9f9f9; color: black; }
    .warning-box { padding: 10px; background-color: #fff3cd; border-left: 4px solid #ffc107; color: black; }
    .failure-box { padding: 10px; background-color: #f8d7da; border-left: 4px solid #dc3545; color: black; }
</style>
""", unsafe_allow_html=True)

st.title("Research Agent")
st.markdown("**System Status**: `Online` | **Mode**: `Planner-Executor`")

# Sidebar controls
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("API Key (Google/OpenAI)", type="password", help="Leave empty to try auto-detect or mock")
    provider = st.selectbox("LLM Provider", ["auto", "google", "openai", "mock"])
    
    if st.button("Reset Agent"):
        st.session_state.clear()
        st.experimental_rerun()

    with st.expander("Help & Documentation"):
        st.markdown("""
        ### Verification Status
        - **PASS**: High confidence, all steps completed.
        - **WARN**: Partial data, missing steps, or potential overclaim.
        - **FAIL**: System error or complete inability to answer.
        
        ### Dictionary
        - **Hypotheses**: Provisional conclusions based on evidence.
        - **Open Questions**: Identified knowledge gaps (to prevent hallucination).
        - **Directional Summary**: The final, non-authoritative answer.
        
        ### Definitions
        - **Coverage**: Did the agent actually do every step it planned?
        - **Overclaim**: Did the agent say something the evidence doesn't support?
        """)

# Initialize session state
if "execution_log" not in st.session_state:
    st.session_state.execution_log = None
if "plan" not in st.session_state:
    st.session_state.plan = None
if "synthesis" not in st.session_state:
    st.session_state.synthesis = None
if "verification" not in st.session_state:
    st.session_state.verification = None

# Main Input
query = st.text_area("Research Query", height=100, placeholder="e.g., Compare the economic impact of remote work vs office work in 2024")

if st.button("Start Research"):
    with st.spinner("Initializing Components..."):
        # Init components
        client = LLMClient(provider=provider, api_key=api_key if api_key else None)
        planner = Planner(client)
        executor = Executor(client)
        synthesizer = Synthesizer(client)
        verifier = Verifier(client)
        
    # 1. PLAN
    with st.status("Planning...", expanded=True) as status:
        st.write("Decomposing query into research steps...")
        plan = planner.plan(query)
        if plan:
            st.session_state.plan = plan
            st.write("Plan generated.")
            status.update(label="Planning Complete", state="complete")
        else:
            status.update(label="Planning Failed", state="error")
            st.stop()
            
    # Display Plan
    with st.expander("Research Plan", expanded=True):
        st.json(plan.json())

    # 2. EXECUTE
    st.subheader("Execution Timeline")
    execution_container = st.container()
    
    with st.status("Running Execution Loop...", expanded=True) as exec_status:
        execution_log = executor.execution_log
        
        # We manually iterate to show progress in UI
        if not executor.validate_plan(plan):
            st.error("Plan Validation Failed")
            st.stop()
            
        progress_bar = st.progress(0)
        total_steps = len(plan.steps)
        
        for i, step in enumerate(plan.steps):
            st.write(f"**Step {step.id}**: {step.type} - _{step.description}_")
            success = executor.execute_step(step)
            
            # Update artifacts display in real-time
            if success:
                 entry = executor.execution_log.log[-1]
                 with execution_container:
                     st.markdown(f"<div class='step-box'><b>Step {step.id} Completed</b><br/>Output: {str(entry['output'])[:200]}...</div>", unsafe_allow_html=True)
            else:
                 st.error(f"Step {step.id} Failed")
                 exec_status.update(state="error")
                 break
            
            progress_bar.progress((i + 1) / total_steps)
            time.sleep(0.5) # UX pause
            
        st.session_state.execution_log = executor.execution_log
        exec_status.update(label="Execution Complete", state="complete")

    # 3. SYNTHESIZE
    if st.session_state.execution_log:
        with st.status("Synthesizing...", expanded=True) as synth_status:
            synthesis = synthesizer.synthesize(executor.execution_log, query)
            st.session_state.synthesis = synthesis
            synth_status.update(label="Synthesis Complete", state="complete")
        
        st.subheader("Directional Synthesis")
        st.info(synthesis.directional_summary)
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Hypotheses:**")
            for h in synthesis.hypotheses:
                st.markdown(f"- {h}")
        with c2:
            st.write("**Open Questions:**")
            for q in synthesis.open_questions:
                st.markdown(f"- {q}")

    # 4. VERIFY
    if st.session_state.synthesis:
        with st.spinner("Verifying..."):
            verification = verifier.verify(plan, executor.execution_log, synthesis)
            st.session_state.verification = verification
            
        st.subheader("Verification Report")
        if verification.status == "pass":
            st.success(f"Status: PASS | Confidence Adjustment: {verification.confidence_adjustment}")
        elif verification.status == "warn":
            st.warning(f"Status: WARN | Confidence Adjustment: {verification.confidence_adjustment}")
        else:
            st.error("Status: FAIL")
            
        with st.expander("Verification Details"):
            st.write("Coverage:", verification.coverage_check)
            st.write("Overclaims:", verification.overclaim_detected)
            st.write("Missing Assumptions:", verification.missing_assumptions)
            
st.markdown("---")
st.caption("Multi-Step Research Agent | Built with Python & Streamlit | by Aditya Kumar Singh")
