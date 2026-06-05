"""LLM interface for Kimi Telegram Agent."""
import json
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)


class LLMInterface:
    """Interface to OpenAI-compatible LLM API."""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL.rstrip("/")
        self.model = settings.OPENAI_MODEL
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_api(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4000,
        response_format: dict | None = None
    ) -> str:
        """Make API call to LLM."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_format:
            payload["response_format"] = response_format
            
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    async def analyze(
        self,
        content: str,
        mode: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """Send content to LLM for analysis.
        
        Args:
            content: The content to analyze
            mode: Analysis mode - 'summarize', 'verify', 'research', 'news'
            context: Additional context (sources, claims, etc.)
        """
        from brain.prompt_builder import PromptBuilder
        
        prompt_builder = PromptBuilder()
        system_prompt = prompt_builder.get_system_prompt(mode)
        user_prompt = prompt_builder.build_user_prompt(content, mode, context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        logger.info(f"LLM analyze mode={mode}")
        return await self._call_api(messages, temperature=0.3)
    
    async def verify_claims(
        self,
        claims: list[str],
        evidence: list[dict]
    ) -> list[dict[str, Any]]:
        """Verify claims against evidence sources.
        
        Returns:
            List of {claim, status, confidence, sources} dicts
        """
        evidence_text = "\n\n".join([
            f"Source {i+1} ({e.get('url', 'unknown')}):\n{e.get('content', '')[:2000]}"
            for i, e in enumerate(evidence)
        ])
        
        claims_text = "\n".join([f"{i+1}. {claim}" for i, claim in enumerate(claims)])
        
        prompt = f"""You are a fact-checking expert. Verify each claim against the provided evidence.

CLAIMS TO VERIFY:
{claims_text}

EVIDENCE SOURCES:
{evidence_text}

For each claim, determine:
1. verified: true/false/null (if evidence is insufficient)
2. confidence: 0-100 score
3. supporting_sources: list of source indices that support
4. contradicting_sources: list of source indices that contradict
5. explanation: brief reasoning

Respond in JSON format:
{{
  "verifications": [
    {{
      "claim": "claim text",
      "verified": true/false/null,
      "confidence": 85,
      "supporting_sources": [1, 2],
      "contradicting_sources": [],
      "explanation": "reasoning"
    }}
  ]
}}"""

        messages = [
            {"role": "system", "content": "You are a precise fact-checking assistant. Respond only in valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._call_api(
                messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            data = json.loads(response)
            return data.get("verifications", [])
        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.error(f"Claim verification failed: {e}")
            return [
                {
                    "claim": claim,
                    "verified": None,
                    "confidence": 0,
                    "supporting_sources": [],
                    "contradicting_sources": [],
                    "explanation": f"Verification error: {str(e)}"
                }
                for claim in claims
            ]
    
    async def extract_claims(self, text: str) -> list[str]:
        """Extract verifiable claims from text."""
        prompt = f"""Extract all factual claims from the following text that could be verified.
A claim is a statement of fact (not opinion) that could be checked against sources.

TEXT:
{text}

Return ONLY a JSON array of strings:
{{"claims": ["claim 1", "claim 2", ...]}}"""

        messages = [
            {"role": "system", "content": "You extract factual claims. Respond only in valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._call_api(
                messages,
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            data = json.loads(response)
            return data.get("claims", [])
        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            return []
    
    async def synthesize_research(
        self,
        query: str,
        sources: list[dict],
        claims_verification: list[dict] | None = None
    ) -> dict[str, Any]:
        """Synthesize research findings into structured report."""
        sources_text = "\n\n".join([
            f"Source {i+1}: {s.get('title', 'Unknown')}\nURL: {s.get('url', '')}\nContent: {s.get('content', '')[:3000]}"
            for i, s in enumerate(sources)
        ])
        
        verification_text = ""
        if claims_verification:
            verification_text = "\n\nCLAIM VERIFICATION:\n" + json.dumps(claims_verification, indent=2)
        
        prompt = f"""You are a research analyst. Synthesize the following sources into a comprehensive, well-structured answer.

USER QUERY: {query}

SOURCES:
{sources_text}
{verification_text}

Produce a response in this exact JSON format:
{{
  "summary": "Executive summary (2-3 sentences)",
  "detailed_answer": "Comprehensive answer with all key points",
  "key_claims": [
    {{"claim": "claim text", "confidence": 85, "sources": [1, 3]}}
  ],
  "consensus_areas": "Areas where sources agree",
  "controversial_areas": "Areas where sources disagree (or null if none)",
  "source_diversity_score": 75,
  "overall_confidence": 80,
  "caveats": "Limitations or biases in sources"
}}"""

        messages = [
            {"role": "system", "content": "You are an expert research synthesizer. Respond only in valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._call_api(
                messages,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Research synthesis failed: {e}")
            return {
                "summary": "Error synthesizing research.",
                "detailed_answer": f"An error occurred: {str(e)}",
                "key_claims": [],
                "consensus_areas": None,
                "controversial_areas": None,
                "source_diversity_score": 0,
                "overall_confidence": 0,
                "caveats": "Synthesis failed"
            }


llm = LLMInterface()
