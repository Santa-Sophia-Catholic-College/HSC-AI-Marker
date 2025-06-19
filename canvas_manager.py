from canvasapi import Canvas
from utils import parse_iso


class CanvasManager:
    def __init__(self, api_url, token, course_id, assignment_id):
        self.canvas = Canvas(api_url, token)
        self.course = self.canvas.get_course(course_id)
        self.assignment = self.course.get_assignment(assignment_id)

    def get_submissions(self):
        return self.assignment.get_submissions(include=["submission_history"])

    @staticmethod
    def get_latest_submission(history):
        return max(history, key=lambda s: s.get("submitted_at") or "")

    def submit_grade_and_comment(self, user_id, comment_text):
        try:
            submission = self.assignment.get_submission(user_id)
            submission_edit_data = {
                "posted_grade": "complete"
            }
            comment_edit_data = {
                "text_comment": comment_text,
            }

            submission.edit(submission=submission_edit_data, comment=comment_edit_data)
            print(f"✓ Comment and grade posted for user {user_id}")
        except Exception as e:
            print(f"✗ Failed to submit feedback for user {user_id}: {e}")
