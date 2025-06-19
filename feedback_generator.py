import os
from agents import Runner
from agent import short_response_agent, long_response_agent
import json
class FeedbackGenerator:
    def __init__(self, tracking):
        self.tracking = tracking

    async def generate_feedback(self):
        feedback_results = {}
        for user_id, info in self.tracking.items():
            text_path = info["ocr_text_file"]
            try:
                with open(text_path, "r", encoding="utf-8") as f:
                    full_prompt = f.read().strip()
                    
                
                response_type = info.get("response_type").lower()
                
                if response_type == "short response":
                    result = await Runner.run(short_response_agent, full_prompt)
                elif response_type == "long response":
                    result = await Runner.run(long_response_agent, full_prompt)
                else:
                    raise ValueError(f"Unknown response type: {response_type}")
                
                try:
                    response = json.loads(result.final_output)
                except json.JSONDecodeError as e:
                    print(f"Raw response: {result.final_output}")
                    raise ValueError(f"Invalid JSON format in response for Student {user_id}")

                # Store comment and submission_id for later use
                feedback_results[user_id] = {
                    "submission_id": info["submission_id"],
                    "response_type": response["response_type"],
                    "subject": response["subject"],
                    "comment": response["feedback_html"],
                    "question": response["question"]
                }

            except Exception as e:
                print(f"Error generating feedback for Student {user_id}: {e}")

        return feedback_results
