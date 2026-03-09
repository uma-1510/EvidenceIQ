"""
EvidenceIQ — Three-Model Nova Pipeline
The core intelligence engine: Lite 2 → Pro → Premier → Chat

Pass 1 (Nova Lite 2):  Fast temporal scan → event timeline JSON
Pass 2 (Nova Pro):     Deep causal analysis per critical event
Pass 3 (Nova Premier): Full synthesis → evidence report
Chat   (Nova Lite 2):  Q&A using pre-built report as context
"""

import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.getenv("AWS_REGION", "us-east-1")

NOVA_LITE    = os.getenv("NOVA_LITE_MODEL",    "us.amazon.nova-lite-v1:0")
NOVA_PRO     = os.getenv("NOVA_PRO_MODEL",     "us.amazon.nova-pro-v1:0")
NOVA_PREMIER = os.getenv("NOVA_PREMIER_MODEL", "us.amazon.nova-premier-v1:0")


def _get_bedrock():
    return boto3.client(
        "bedrock-runtime",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def _invoke(model_id: str, system_prompt: str, user_content: list, max_tokens: int = 4096) -> str:
    """
    Unified invoke wrapper using Nova's native messages schema.
    user_content: list of content blocks (text, video, image, etc.)
    """
    bedrock = _get_bedrock()
    body = json.dumps({
        "schemaVersion": "messages-v1",
        "system": [{"text": system_prompt}],
        "messages": [
            {"role": "user", "content": user_content}
        ],
        "inferenceConfig": {
            "max_new_tokens": max_tokens,
            "temperature": 0.2,   # Low temperature = consistent, structured output
            "top_p": 0.9,
        },
    })

    response = bedrock.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["output"]["message"]["content"][0]["text"]


def _parse_json_response(raw: str) -> dict:
    """
    Safely parse JSON from model response.
    Nova sometimes wraps output in markdown fences — strip them.
    """
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```", 2)[1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.rsplit("```", 1)[0].strip()
    return json.loads(clean)


# ─────────────────────────────────────────────────────────────────
# PASS 1 — Nova Lite 2: Fast Temporal Scanner
# ─────────────────────────────────────────────────────────────────
def pass1_temporal_scan(s3_uri: str, video_format: str) -> dict:
    """
    Nova Lite 2 watches the full video and returns a structured
    event timeline with timestamps and severity ratings.
    Fast (~4–8 seconds). Cheap.
    """
    system = (
        "You are a forensic video analyst. Your job is to watch incident footage "
        "and produce a precise, structured timeline of ALL significant events. "
        "You must respond with ONLY valid JSON — no preamble, no explanation, no markdown."
    )

    user_content = [
        {
            "video": {
                "format": video_format,
                "source": {"s3Location": {"uri": s3_uri}},
            }
        },
        {
            "text": """Watch this entire video carefully.

Return ONLY this JSON structure — nothing else:
{
  "duration_seconds": <total video duration as integer>,
  "scene_context": "<one sentence describing the overall scene/setting>",
  "events": [
    {
      "id": 1,
      "timestamp": "<MM:SS format>",
      "timestamp_seconds": <integer seconds from start>,
      "description": "<precise description of what happens>",
      "severity": "<none|low|medium|high|critical>",
      "category": "<movement|collision|hazard|person|vehicle|property|audio|other>",
      "involves": ["<entity 1>", "<entity 2>"]
    }
  ],
  "critical_events": [<list of event IDs with severity high or critical>],
  "summary": "<2-3 sentence overview of the entire incident>"
}

Severity guide:
- critical: collision, injury, direct threat
- high: near-miss, dangerous situation, clear violation
- medium: suspicious behavior, minor hazard, rule violation
- low: noteworthy but non-threatening
- none: ambient/background activity"""
        }
    ]

    raw = _invoke(NOVA_LITE, system, user_content, max_tokens=3000)
    return _parse_json_response(raw)


# ─────────────────────────────────────────────────────────────────
# PASS 2 — Nova Pro: Deep Causal Reasoner
# ─────────────────────────────────────────────────────────────────
def pass2_causal_analysis(s3_uri: str, video_format: str, timeline: dict) -> dict:
    """
    Nova Pro watches the full video again with the timeline as context.
    It performs deep causal analysis on each critical/high event.
    Asks WHY — not just what.
    """
    system = (
        "You are a forensic incident reconstruction expert with 20 years of experience "
        "in accident analysis, liability assessment, and evidence documentation. "
        "You analyze video evidence to establish causal chains — not just describe events, "
        "but explain WHY they occurred and what chain of events led to them. "
        "Respond ONLY with valid JSON."
    )

    critical_events = [
        e for e in timeline.get("events", [])
        if e.get("severity") in ("critical", "high")
    ]

    if not critical_events:
        # Fall back to all events if none are critical/high
        critical_events = timeline.get("events", [])

    user_content = [
        {
            "video": {
                "format": video_format,
                "source": {"s3Location": {"uri": s3_uri}},
            }
        },
        {
            "text": f"""You have already seen a preliminary timeline of this video:

PRELIMINARY TIMELINE:
{json.dumps(timeline, indent=2)}

Now perform DEEP CAUSAL ANALYSIS on the following critical events: {[e['id'] for e in critical_events]}

For each event, analyze the 10–15 seconds BEFORE and AFTER it.

Return ONLY this JSON structure:
{{
  "causal_analyses": [
    {{
      "event_id": <id>,
      "timestamp": "<MM:SS>",
      "what_happened": "<precise description>",
      "preconditions": ["<factor that existed before the event>"],
      "trigger": "<the specific action or moment that caused this event>",
      "contributing_factors": ["<environmental, behavioral, or mechanical factor>"],
      "consequences": ["<what resulted from this event>"],
      "could_have_been_prevented": <true|false>,
      "prevention_factors": ["<what could have prevented this>"],
      "responsible_entities": [
        {{
          "entity": "<person/vehicle/system>",
          "responsibility_level": "<primary|secondary|none>",
          "reason": "<why>"
        }}
      ],
      "evidence_strength": "<strong|moderate|weak>",
      "key_timestamp_citations": ["<MM:SS - what is visible>"]
    }}
  ],
  "overall_causal_chain": "<narrative description of how events led to the main incident>",
  "primary_fault_assessment": {{
    "entity": "<who/what is primarily responsible>",
    "confidence": "<high|medium|low>",
    "reasoning": "<explanation>"
  }}
}}"""
        }
    ]

    raw = _invoke(NOVA_PRO, system, user_content, max_tokens=6000)
    return _parse_json_response(raw)


# ─────────────────────────────────────────────────────────────────
# PASS 3 — Nova Premier: Evidence Synthesizer
# ─────────────────────────────────────────────────────────────────
def pass3_synthesis(s3_uri: str, video_format: str, timeline: dict, causal: dict) -> dict:
    """
    Nova Premier takes the full video + both prior analyses
    and produces the final, court-ready evidence report.
    Most expensive call — used only once per analysis.
    """
    system = (
        "You are a senior forensic evidence analyst and legal documentation specialist. "
        "You synthesize video evidence, event timelines, and causal analyses into "
        "comprehensive, structured evidence reports suitable for insurance claims, "
        "legal proceedings, HR investigations, and regulatory compliance filings. "
        "Your reports are precise, objective, and cite specific timestamps as evidence. "
        "Respond ONLY with valid JSON."
    )

    user_content = [
        {
            "video": {
                "format": video_format,
                "source": {"s3Location": {"uri": s3_uri}},
            }
        },
        {
            "text": f"""You have the following analyses from prior review of this video:

TEMPORAL TIMELINE:
{json.dumps(timeline, indent=2)}

CAUSAL ANALYSIS:
{json.dumps(causal, indent=2)}

Using these analyses AND your own observation of the full video, produce the FINAL EVIDENCE REPORT.

Return ONLY this JSON structure:
{{
  "report_metadata": {{
    "report_type": "<traffic_incident|workplace_safety|property_damage|security|other>",
    "severity_classification": "<minor|moderate|serious|critical>",
    "video_duration": "<MM:SS>",
    "total_events_detected": <integer>
  }},
  "executive_summary": "<3-4 sentence plain-English summary of what happened>",
  "chronological_narrative": "<Full narrative of the incident in chronological order, citing specific timestamps>",
  "key_evidence": [
    {{
      "timestamp": "<MM:SS>",
      "description": "<what is visible>",
      "evidentiary_value": "<why this moment matters legally/factually>"
    }}
  ],
  "fault_liability_assessment": {{
    "primary_responsible_party": "<entity>",
    "liability_distribution": [
      {{"entity": "<name>", "percentage": <0-100>, "basis": "<reason>"}}
    ],
    "confidence_level": "<high|medium|low>",
    "caveats": ["<limitation or caveat on this assessment>"]
  }},
  "contributing_factors": [
    {{"factor": "<description>", "type": "<environmental|behavioral|mechanical|procedural>"}}
  ],
  "applicable_frameworks": [
    {{"framework": "<law/regulation/policy name>", "relevance": "<why it applies>"}}
  ],
  "recommended_next_steps": [
    {{"priority": "<immediate|within_24h|within_week>", "action": "<what to do>", "reason": "<why>"}}
  ],
  "documentation_checklist": [
    "<item that should be documented or preserved>"
  ]
}}"""
        }
    ]

    raw = _invoke(NOVA_PREMIER, system, user_content, max_tokens=8000)
    return _parse_json_response(raw)


# ─────────────────────────────────────────────────────────────────
# CHAT — Nova Lite 2: Q&A from pre-built context
# ─────────────────────────────────────────────────────────────────
def chat_with_evidence(
    question: str,
    timeline: dict,
    causal: dict,
    report: dict,
    chat_history: list,
) -> str:
    """
    Nova Lite 2 answers follow-up questions using the pre-built
    analysis as context. Fast, cheap, no re-analysis needed.

    chat_history: list of {"role": "user"|"assistant", "content": "..."}
    """
    system = (
        "You are EvidenceIQ, an expert forensic video analysis assistant. "
        "You have already analyzed an incident video and have access to: "
        "a detailed event timeline, a causal analysis report, and a full evidence report. "
        "Answer questions precisely, cite specific timestamps when relevant, "
        "and always distinguish between what is visually confirmed vs. inferred. "
        "Be concise but thorough. Never make up information not in the analysis."
        f"\n\nEVIDENCE CONTEXT:\n"
        f"TIMELINE: {json.dumps(timeline)}\n\n"
        f"CAUSAL ANALYSIS: {json.dumps(causal)}\n\n"
        f"EVIDENCE REPORT: {json.dumps(report)}"
    )

    # Build conversation history for multi-turn context
    messages = []
    for turn in chat_history[-6:]:  # Last 6 turns to stay within context
        messages.append({
            "role": turn["role"],
            "content": [{"text": turn["content"]}]
        })

    # Add current question
    messages.append({
        "role": "user",
        "content": [{"text": question}]
    })

    bedrock = _get_bedrock()
    body = json.dumps({
        "schemaVersion": "messages-v1",
        "system": [{"text": system}],
        "messages": messages,
        "inferenceConfig": {
            "max_new_tokens": 1000,
            "temperature": 0.3,
        },
    })

    response = bedrock.invoke_model(
        modelId=NOVA_LITE,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["output"]["message"]["content"][0]["text"]


# ─────────────────────────────────────────────────────────────────
# ORCHESTRATOR — Run all three passes sequentially
# ─────────────────────────────────────────────────────────────────
def run_full_pipeline(s3_uri: str, video_format: str) -> dict:
    """
    Orchestrates all three Nova passes and returns the complete analysis.
    Yields progress updates via a generator for streaming to the frontend.
    """
    print(f"[Pipeline] Starting analysis for: {s3_uri}")

    print("[Pipeline] Pass 1/3 — Nova Lite 2: Temporal scan...")
    timeline = pass1_temporal_scan(s3_uri, video_format)
    print(f"[Pipeline] Pass 1 complete — {len(timeline.get('events', []))} events detected")

    print("[Pipeline] Pass 2/3 — Nova Pro: Causal analysis...")
    causal = pass2_causal_analysis(s3_uri, video_format, timeline)
    print("[Pipeline] Pass 2 complete — Causal chains established")

    print("[Pipeline] Pass 3/3 — Nova Premier: Evidence synthesis...")
    report = pass3_synthesis(s3_uri, video_format, timeline, causal)
    print("[Pipeline] Pass 3 complete — Evidence report generated")

    return {
        "timeline": timeline,
        "causal":   causal,
        "report":   report,
    }