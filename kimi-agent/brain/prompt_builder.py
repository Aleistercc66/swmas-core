"""System prompts for different analysis modes."""


class PromptBuilder:
    """Builds system and user prompts for different analysis modes."""
    
    SYSTEM_PROMPTS = {
        "summarize": """You are an expert summarizer. Extract key points, main themes, and critical information.
        
Rules:
- Be concise but comprehensive
- Use bullet points for key findings
- Preserve important numbers, dates, and names
- Identify the main argument or purpose
- Note any actionable items
- Output in the user's language""",
        
        "verify": """You are a meticulous fact-checker. Verify claims against sources and identify misinformation.

Rules:
- Only mark claims as verified if sources explicitly support them
- Flag uncertain claims clearly
- Note source reliability
- Identify potential bias in sources
- Be conservative — when in doubt, flag as uncertain
- Output in the user's language""",
        
        "research": """You are a thorough research analyst. Synthesize information from multiple sources into a clear, well-supported answer.

Rules:
- Always cite your sources with numbers [1], [2], etc.
- Distinguish between established facts and emerging information
- Note where sources disagree
- Provide confidence levels for key claims
- Include relevant context and background
- Be comprehensive but organized (use sections)
- Output in the user's language""",
        
        "news": """You are a news analyst. Aggregate multiple perspectives and identify the core facts.

Rules:
- Present a balanced view from multiple sources
- Identify consensus vs. conflicting reports
- Note the recency of information
- Flag speculation vs. confirmed facts
- Include source diversity assessment
- Highlight any missing perspectives
- Output in the user's language""",
        
        "photo": """You are a visual content analyzer. Analyze images, charts, and text extracted from photos.

Rules:
- Describe what you see clearly
- Extract all readable text
- If it's a chart/graph, describe the data and trends
- If it's a document, summarize the content
- Note any important details (dates, numbers, names)
- If text is in another language, translate key parts
- Output in the user's language""",
        
        "url": """You are a web content analyzer. Summarize webpage content and verify its claims.

Rules:
- Extract the main topic and key points
- Identify the author/source credibility if available
- Note publication date
- Summarize key claims made in the content
- Flag any sensational or misleading framing
- Compare claims against general knowledge when possible
- Output in the user's language"""
    }
    
    def get_system_prompt(self, mode: str) -> str:
        """Get system prompt for given mode."""
        return self.SYSTEM_PROMPTS.get(mode, self.SYSTEM_PROMPTS["research"])
    
    def build_user_prompt(
        self,
        content: str,
        mode: str,
        context: dict | None = None
    ) -> str:
        """Build user prompt with content and context."""
        context_parts = []
        
        if context:
            if "sources" in context:
                sources_text = "\n\n".join([
                    f"[{i+1}] {s.get('title', 'Source')} — {s.get('url', '')}\n{s.get('content', '')[:2000]}"
                    for i, s in enumerate(context["sources"])
                ])
                context_parts.append(f"SOURCES:\n{sources_text}")
            
            if "conversation_history" in context:
                history = "\n".join([
                    f"{msg['role']}: {msg['content'][:200]}"
                    for msg in context["conversation_history"]
                ])
                context_parts.append(f"CONVERSATION HISTORY:\n{history}")
            
            if "metadata" in context:
                meta = context["metadata"]
                meta_text = "\n".join([f"{k}: {v}" for k, v in meta.items()])
                context_parts.append(f"METADATA:\n{meta_text}")
        
        context_str = "\n\n---\n\n".join(context_parts) if context_parts else ""
        
        prompt = f"CONTENT TO ANALYZE:\n{content}"
        if context_str:
            prompt += f"\n\n---\n\n{context_str}"
        
        return prompt
    
    def build_research_prompt(
        self,
        query: str,
        sources: list[dict],
        depth: str = "standard"
    ) -> str:
        """Build prompt for deep research mode."""
        sources_text = "\n\n".join([
            f"[{i+1}] {s.get('title', 'Source')} — {s.get('url', '')}\n{s.get('content', '')[:3000]}"
            for i, s in enumerate(sources)
        ])
        
        depth_instruction = {
            "standard": "Provide a balanced summary with key findings.",
            "deep": "Provide comprehensive analysis with all nuances, conflicting viewpoints, and detailed evidence assessment."
        }.get(depth, "standard")
        
        return f"""RESEARCH QUERY: {query}

DEPTH: {depth_instruction}

{sources_text}

Based on these sources, provide a thorough answer with:
1. Direct answer to the query
2. Key supporting evidence with citations [1], [2], etc.
3. Any conflicting information or uncertainty
4. Source reliability assessment
5. Overall confidence level (Low/Medium/High)"""
    
    def build_verification_prompt(self, text: str, sources: list[dict]) -> str:
        """Build prompt for fact verification."""
        return f"""FACT-CHECK: Verify the following text against provided sources.

TEXT TO VERIFY:
{text}

SOURCES TO CHECK AGAINST:
{chr(10).join([f"[{i+1}] {s.get('title', '')} — {s.get('url', '')}: {s.get('content', '')[:1500]}" for i, s in enumerate(sources)])}

For each claim in the text, determine:
- Verified (supported by sources)
- Partially Verified (some support, some gaps)
- Unverified (no source found)
- Contradicted (sources disagree)

Return a structured fact-check report."""
