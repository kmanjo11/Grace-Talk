"""
Message Processor for OpenInterpreter
Handles message consistency, filtering, and response formatting
"""

import re
import streamlit as st
from typing import Dict, Any, List


class MessageProcessor:
    """Processes and filters messages for consistent user experience"""
    
    def __init__(self):
        self.verbose_patterns = [
            r"I see you(?:'re| are) (?:asking|trying|looking|wanting)",
            r"It looks like you(?:'re| are) (?:asking|trying|looking|wanting)",
            r"Based on your (?:request|message|question)",
            r"Let me (?:help you|assist you|understand)",
            r"I understand (?:that )?you(?:'re| are)",
            r"From what I can see",
            r"Looking at your (?:request|message|question)",
            r"I can help you with (?:that|this)",
            r"Here's what I (?:can do|understand|think)",
            r"Let me break this down",
            r"To summarize",
            r"In summary",
            r"I apologize for",
            r"Sorry for the",
            r"I'm sorry",
        ]
        
        self.thought_patterns = [
            r"Let me think about this",
            r"I need to consider",
            r"First, I'll",
            r"My approach will be",
            r"I'll start by",
            r"The process involves",
            r"Step by step",
            r"Here's my plan",
            r"I'm going to",
            r"Let me analyze",
        ]
        
        self.meta_patterns = [
            r"```(?:python|bash|shell|code)\n.*?```",
            r"Execution output:",
            r"Running command:",
            r"Console output:",
            r"Terminal output:",
        ]

    def should_show_code_output(self) -> bool:
        """Check if code/terminal output should be shown"""
        return st.session_state.get('show_exec_output', False)

    def is_concise_mode(self) -> bool:
        """Check if concise mode is enabled"""
        return st.session_state.get('concise_mode', True)

    def filter_verbose_language(self, text: str) -> str:
        """Remove verbose language patterns from text"""
        if not self.is_concise_mode():
            return text
            
        # Remove verbose patterns
        for pattern in self.verbose_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove thought process patterns
        for pattern in self.thought_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up extra whitespace and newlines
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
        
        return text.strip()

    def filter_code_output(self, text: str) -> str:
        """Filter code output based on user preferences"""
        if self.should_show_code_output():
            return text
        
        # Remove code blocks and execution output
        for pattern in self.meta_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        
        return text

    def process_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual response chunks"""
        chunk_type = chunk.get('type', '')
        
        # Hide code execution chunks if not requested
        if not self.should_show_code_output():
            if chunk_type in ['code', 'console', 'confirmation']:
                return {'type': 'hidden', 'content': ''}
        
        # Process message content
        if chunk_type == 'message':
            content = chunk.get('content', '')
            if content:
                content = self.filter_verbose_language(content)
                chunk['content'] = content
        
        return chunk

    def format_final_response(self, response: str) -> str:
        """Format the final response for consistency"""
        if not response:
            return response
        
        # Apply all filters
        response = self.filter_verbose_language(response)
        response = self.filter_code_output(response)
        
        # Ensure concise responses
        if self.is_concise_mode():
            # Split into sentences and limit if too verbose
            sentences = re.split(r'[.!?]+', response)
            if len(sentences) > 4:
                # Keep first 3 sentences and add ellipsis if needed
                response = '. '.join(sentences[:3]) + '.'
        
        return response.strip()

    def is_simple_greeting(self, prompt: str) -> bool:
        """Check if the prompt is a simple greeting"""
        if not prompt:
            return False
        
        p_lower = prompt.strip().lower()
        if len(p_lower) <= 12:
            greeting_pattern = r"^(hi|hey|hello|yo|sup|howdy|hola|hi there|hello there)[.!?]*$"
            return bool(re.match(greeting_pattern, p_lower))
        
        return False

    def get_greeting_response(self) -> str:
        """Get a simple greeting response"""
        return "Hi! How can I help?"

    def should_use_augmentation(self, prompt: str) -> bool:
        """Determine if context augmentation should be used"""
        # Skip augmentation for simple greetings
        if self.is_simple_greeting(prompt):
            return False
        
        # Skip if in schedule focus mode and not schedule-related
        if st.session_state.get('schedule_focus_mode', False):
            schedule_keywords = ['schedule', 'p6', 'project', 'timeline', 'milestone', 'task']
            if not any(keyword in prompt.lower() for keyword in schedule_keywords):
                return False
        
        return True

    def build_system_prompt(self) -> str:
        """Build system prompt with style guidelines"""
        guidelines = [
            "- Respond naturally and conversationally",
            "- Do NOT restate or recap the user's message",
            "- Do NOT use templates or rigid structures",
            "- Keep responses concise and on-topic",
            "- Do NOT apologize unless specifically asked",
            "- Do NOT include filler phrases or meta commentary",
        ]
        
        if self.is_concise_mode():
            guidelines.extend([
                "- Limit responses to 1-4 sentences unless technical details are requested",
                "- Do NOT include code unless explicitly asked",
                "- Focus on direct, actionable answers",
            ])
        
        if st.session_state.get('schedule_focus_mode', False):
            guidelines.extend([
                "- Focus on P6 schedules, PDFs, and Knowledge Base content",
                "- Avoid proposing code execution unless specifically requested",
                "- Cite schedule findings succinctly",
            ])
        
        return "\n[Response Guidelines]\n" + "\n".join(guidelines) + "\n\n"


# Global instance
message_processor = MessageProcessor()

