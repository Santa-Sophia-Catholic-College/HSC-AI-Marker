import os
from agents import Runner
from agent import short_response_agent, long_response_agent
import json
from enum import Enum

class UnknownResponseTypeError(Exception):
    """Custom exception for unknown response types."""
    pass

class ResponseTypes(Enum):
    LONG_RESPONSE = "long_response"
    SHORT_RESPONSE = "short_response"

class FeedbackGenerator:
    def __init__(self):
        pass
    
    def detect_response_type(self, content):
        content = content.lower()
        if "long response" in content:
            return ResponseTypes.LONG_RESPONSE
        elif "short response" in content:
            return ResponseTypes.SHORT_RESPONSE
        else:
            return "No response type detected"
        
    async def generate_feedback(self, response_text):           
        response_type = self.detect_response_type(response_text)

        if response_type == ResponseTypes.SHORT_RESPONSE:
            result = await Runner.run(short_response_agent, response_text)
        elif response_type == ResponseTypes.LONG_RESPONSE:
            result = await Runner.run(long_response_agent, response_text)
        else:
            raise ValueError(f"Unsupported response type: {response_type}")
        
        response = json.loads(result.final_output)

        return response
