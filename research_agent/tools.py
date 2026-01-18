from .schema import ResearchInput, ResearchOutput, ComparisonInput, ComparisonOutput
from .utils import LLMClient, setup_logger
from typing import List
import json

logger = setup_logger("tools")

def execute_research(input_data: ResearchInput, llm_client: LLMClient = None) -> ResearchOutput:
    """
    Mock implementation of the research tool.
    Unless we have a search tool (Tavily/Source), we simulate results.
    We *could* use the LLM to hallucinate 'research' if we wanted a pure sim, 
    but for 'honesty', it's better to admit we have no external access if we don't.
    
    However, for the portfolio project sake, we will return a simulation.
    """
    topic = input_data.topic
    logger.info(f"Researching topic: {topic}")
    
    return ResearchOutput(
        topic=topic,
        summary=f"Research Summary for {topic} (Simulated Data)",
        key_points=[
            f"{topic} is a complex subject.",
            f"Recent studies (2024) show significant interest in {topic}."
        ],
        assumptions=["Results are simulated for demonstration"],
        confidence="medium",
        gaps=["Lack of live internet access in this environment"],
        sources=["SimulationDB"]
    )

def execute_compare(input_data: ComparisonInput, llm_client: LLMClient) -> ComparisonOutput:
    """
    Comparison tool using LLM to generate structured contrasts.
    """
    logger.info(f"Executing comparison on dimensions: {input_data.dimensions}")
    
    # Construct prompt
    items_text = ""
    for name, output in input_data.items.items():
        items_text += f"--- ITEM: {name} ---\nSummary: {output.summary}\nKey Points: {output.key_points}\n\n"
        
    prompt = f"""
    Compare the following items based on these dimensions: {input_data.dimensions}.
    
    ITEMS:
    {items_text}
    
    OUTPUT JSON FORMAT:
    {{
        "dimensions": {json.dumps(input_data.dimensions)},
        "contrasts": {{
            "dimension_name": {{
                "item_name": "contrast description"
            }}
        }},
        "tradeoffs": ["string", ...],
        "uncertainties": ["string", ...]
    }}
    """
    
    response = llm_client.generate(system_prompt="You are a precise comparison engine. Output JSON only.", user_prompt=prompt)
    
    try:
        # Simple cleanup
        clean_json = response.strip()
        if clean_json.startswith("```json"): clean_json = clean_json[7:]
        if clean_json.endswith("```"): clean_json = clean_json[:-3]
        
        data = json.loads(clean_json)
        return ComparisonOutput(**data)
    except Exception as e:
        logger.error(f"Comparison LLM failed: {e}")
        # Fallback
        return ComparisonOutput(
            dimensions=input_data.dimensions,
            contrasts={d: {k: "Error generating contrast" for k in input_data.items} for d in input_data.dimensions},
            tradeoffs=["Comparison generation failed"],
            uncertainties=["LLM Error"]
        )
