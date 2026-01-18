from .schema import VerificationOutput, ResearchPlan, SynthesisOutput
from .executor import ExecutionLog
from .utils import LLMClient, setup_logger
import json

logger = setup_logger("verifier")

class Verifier:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def verify(self, plan: ResearchPlan, execution_log: ExecutionLog, synthesis: SynthesisOutput) -> VerificationOutput:
        logger.info("Running verification...")
        
        # 1. Coverage Check (Rule-based)
        coverage = {}
        executed_ids = set(log['step_id'] for log in execution_log.log if log['status'] == 'success')
        for step in plan.steps:
            coverage[step.id] = step.id in executed_ids
            
        all_covered = all(coverage.values())
        
        # 2. Epistemic Check (LLM-based)
        prompt = f"""
        VERIFY RESEARCH INTEGRITY
        
        GOAL: {plan.research_goal}
        
        SYNTHESIS:
        {synthesis.directional_summary}
        
        Are there unsupported claims? Is the confidence level appropriate?
        
        OUTPUT JSON:
        {{
            "overclaim_detected": bool,
            "missing_assumptions": ["str"],
            "required_disclaimers": ["str"],
            "confidence_adjustment": "none" | "downgrade"
        }}
        """
        
        response = self.llm.generate(system_prompt="You are a strict Research Auditor. Output JSON only.", user_prompt=prompt)
        
        try:
            clean_json = response.strip()
            if clean_json.startswith("```json"): clean_json = clean_json[7:]
            if clean_json.endswith("```"): clean_json = clean_json[:-3]
            
            data = json.loads(clean_json)
            
            status = "pass"
            if data.get("overclaim_detected") or not all_covered or data.get("confidence_adjustment") == "downgrade":
                status = "warn"
            if not executed_ids: # Total failure
                status = "fail"
                
            return VerificationOutput(
                status=status,
                coverage_check=coverage,
                overclaim_detected=data.get("overclaim_detected", False),
                missing_assumptions=data.get("missing_assumptions", []),
                required_disclaimers=data.get("required_disclaimers", []),
                confidence_adjustment=data.get("confidence_adjustment", "none")
            )
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return VerificationOutput(
                status="fail",
                coverage_check=coverage,
                overclaim_detected=True,
                missing_assumptions=["Verification process failed"],
                required_disclaimers=["System integrity check failed"],
                confidence_adjustment="downgrade"
            )
