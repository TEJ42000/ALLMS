"""Anthropic API Client Service for the LLS Study Portal."""

import logging
from typing import Dict, List, Optional

from anthropic import AsyncAnthropic

from app.services.gcp_service import get_anthropic_api_key

logger = logging.getLogger(__name__)

# Initialize Anthropic client using ADC-based secret retrieval (with .env fallback)
client = AsyncAnthropic(api_key=get_anthropic_api_key())

# System prompts for different contexts
TUTOR_SYSTEM_PROMPT = """You are an expert Law & Legal Skills tutor for the \
University of Groningen's LLS course.

COURSE COVERAGE:
- Constitutional Law (Dutch Constitution, separation of powers, judicial review Art. 120)
- Administrative Law (GALA: orders, interested parties, appeals, Arts. 1:1-8:72)
- Criminal Law (trial procedure, decision model Arts. 348-350 CCP, defences)
- Private Law/Contract (DCC: 4 requirements, damages Art. 6:74, breach remedies)
- International Law (ICJ, ECHR, treaties, customary law, usus + opinio iuris)

EXAM: October 28, 2025 | 200 points total | Pass: 110 points

VISUAL FORMATTING - USE EXTENSIVELY:
Use these visual elements liberally:
- ## Main Section Header (blue underline)
- ### Important Point (green box with 💡)
- ⚠️ Warning or caution (yellow box)
- ✅ Correct approach (green checkmark box)
- ❌ Common mistake (red error box)
- ❓ Question to consider (purple question box)
- STEP 1:, STEP 2: for sequential steps (purple numbered circle)
- 1. 2. 3. for numbered lists (blue boxes)
- • for bullet points (yellow arrow boxes)
- **bold** for key terms (highlighted in yellow)
- *italic* for emphasis (colored blue)
- `code` for article references
- Always write Art. 6:74 DCC format (gets blue badge)

TEACHING APPROACH:
- Start with ## header for main sections
- Use ### for key takeaways
- Number complex processes (1. 2. 3.)
- Use ✅ for correct methods, ❌ for wrong ones
- Use ⚠️ for important warnings
- ALWAYS cite articles: Art. 6:74 DCC
- Break complex topics into STEP 1:, STEP 2:, etc.
- Keep responses 300-600 words
- Be visual, colorful, and engaging

Respond immediately with substantive, VISUALLY FORMATTED legal information."""

ASSESSMENT_SYSTEM_PROMPT = """You are an expert Law & Legal Skills assessor grading \
student answers for the University of Groningen LLS course.

YOUR TASK - Provide detailed, VISUALLY FORMATTED assessment:

## GRADE: X/10 (use ## for this header)

Use these visual elements throughout:

### Strengths (green box)
✅ What the student did well (each on its own line)

### Weaknesses (yellow warning)
⚠️ What needs improvement (each on its own line)

### Corrections (red error boxes)
❌ Error with explanation and correct Art. X DCC citation

### Improvement Steps (purple steps)
STEP 1: First improvement suggestion
STEP 2: Second improvement suggestion

### Key Takeaways (green tip boxes)
💡 Main lesson from this assessment

GRADING RUBRIC:
- **9-10**: Excellent - Complete, accurate, well-structured, cites articles correctly
- **7-8**: Good - Mostly correct, minor errors, could be more detailed
- **5-6**: Satisfactory - Basic understanding but missing key elements
- **3-4**: Poor - Significant errors or missing crucial information
- **0-2**: Fail - Fundamental misunderstanding

Be constructive, specific, visual, and educational!"""


async def get_ai_tutor_response(
    message: str,
    context: str = "Law & Legal Skills",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    materials_content: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Get AI tutor response for a user message.

    Args:
        message: User's question or prompt
        context: Subject area context
        conversation_history: Previous conversation messages
        materials_content: Optional list of dicts with 'title' and 'text' keys
                          containing course material content to include

    Returns:
        AI-generated response text
    """
    try:
        # Build conversation history
        messages = []

        if conversation_history:
            # Add previous messages (limit to last 10)
            messages.extend(conversation_history[-10:])

        # Build user message content
        user_content = ""

        # If materials provided, include them as context
        if materials_content:
            user_content += "Use the following course materials to inform your response:\n\n"
            for mat in materials_content[:5]:  # Limit to 5 materials
                user_content += f"=== DOCUMENT: {mat['title']} ===\n"
                # Truncate text to avoid token limits, ensuring we don't cut mid-word
                text = mat['text']
                if len(text) > 8000:
                    text = text[:8000].rsplit(' ', 1)[0] + '...'
                user_content += f"{text}\n"
                user_content += f"=== END OF {mat['title']} ===\n\n"
            user_content += "---\n\n"
            user_content += f"Student Question: {message}"
        else:
            user_content = message

        # Add current message
        messages.append({
            "role": "user",
            "content": user_content
        })

        # Add context to system prompt
        system_prompt = TUTOR_SYSTEM_PROMPT + "\n\nCurrent topic context: " + context
        if materials_content:
            system_prompt += "\n\nIMPORTANT: Use the provided course materials to answer. "
            system_prompt += "Cite specific documents when relevant."

        # Call Anthropic API
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Extract text from response
        response_text = response.content[0].text

        materials_count = len(materials_content) if materials_content else 0
        logger.info(
            "AI Tutor response generated for context: %s (with %d materials)",
            context, materials_count
        )

        return response_text

    except Exception as e:
        logger.error("Error getting AI tutor response: %s", str(e))
        raise


async def get_assessment_response(
    topic: str,
    question: Optional[str],
    answer: str
) -> str:
    """
    Get AI assessment and grading for a student answer.

    Args:
        topic: Subject area (e.g., "Private Law", "Criminal Law")
        question: Optional question/prompt
        answer: Student's answer text

    Returns:
        AI-generated assessment with grade and feedback
    """
    try:
        # Build assessment prompt
        system_prompt = ASSESSMENT_SYSTEM_PROMPT.replace("${topic}", topic)

        # Build user message
        if question:
            user_message = "Question/Prompt: %s\n\nMy Answer:\n%s" % (question, answer)
        else:
            user_message = "Please assess this answer:\n\n%s" % answer

        # Call Anthropic API
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": user_message
            }]
        )

        # Extract text from response
        response_text = response.content[0].text

        logger.info("AI Assessment generated for topic: %s", topic)

        return response_text

    except Exception as e:
        logger.error("Error getting assessment response: %s", str(e))
        raise


async def get_simple_response(
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 1.0
) -> str:
    """
    Get a simple AI response without special formatting.

    Args:
        prompt: User prompt
        max_tokens: Maximum tokens in response
        temperature: Response creativity (0.0 - 1.0)

    Returns:
        AI-generated response text
    """
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        return response.content[0].text

    except Exception as e:
        logger.error("Error getting simple response: %s", str(e))
        raise


# Example usage:
if __name__ == "__main__":
    import asyncio

    async def test():
        """Test the AI tutor and assessment functions."""
        # Test tutor response
        tutor_response = await get_ai_tutor_response(
            message="Explain Art. 6:74 DCC",
            context="Private Law"
        )
        print("Tutor Response:")
        print(tutor_response)
        print("\n" + "=" * 80 + "\n")

        # Test assessment
        assessment = await get_assessment_response(
            topic="Private Law",
            question="What are the requirements for a valid contract?",
            answer="A contract needs agreement between parties."
        )
        print("Assessment:")
        print(assessment)

    asyncio.run(test())
