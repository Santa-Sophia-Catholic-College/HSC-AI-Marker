import os
import asyncio
import gspread
import datetime
from canvas_manager import CanvasManager
from ocr_processor import OCRProcessor
from feedback_generator import FeedbackGenerator
from config import API_URL, COURSE_ID, ASSIGNMENT_ID, DOWNLOAD_DIR


def load_token(token_path):
    with open(os.path.expanduser(token_path), "r") as f:
        return f.read().strip()


def main():
    print("Loading tokens...")
    canvas_token = os.getenv('CANVAS_API_TOKEN')
    ocr_token = os.getenv('HANDWRITING_OCR_TOKEN')

    if not canvas_token:
        raise ValueError("CANVAS_API_TOKEN environment variable is not set")
    if not ocr_token:
        raise ValueError("HANDWRITING_OCR_TOKEN environment variable is not set")

    print("Initializing components...")
    
    gc = gspread.service_account(filename='service_account.json')
    worksheet = gc.open_by_key('1qxvkMRUbK0fQ8Kdp4Z7lwP36G8qzXMT7Ul6eRI-BAzU').worksheet('Data')

    canvas_mgr = CanvasManager(
        api_url=API_URL,
        token=canvas_token,
        course_id=COURSE_ID,
        assignment_id=ASSIGNMENT_ID
    )

    ocr_processor = OCRProcessor(
        token=ocr_token,
        download_dir=DOWNLOAD_DIR
    )

    print("Checking for unmarked or resubmitted submissions...")
    submissions = canvas_mgr.get_submissions()
    for submission in submissions:
        #print(f"Processing submission for Student {submission.user_id}...")
        ocr_processor.process_submission(submission)

    print("OCR processing complete. Generating feedback...\n")
    feedback_gen = FeedbackGenerator(ocr_processor.tracking)
    
    # Generate feedback and capture results
    feedback_results = asyncio.run(feedback_gen.generate_feedback())

    # Submit grade and comment via Canvas
    for user_id, feedback in feedback_results.items():
        try:
            canvas_mgr.submit_grade_and_comment(
                user_id=user_id,
                comment_text=feedback["comment"]
            )
            
            user_profile = canvas_mgr.get_user_profile(user_id)
            sis_user_id = user_profile.get("sis_user_id", "Unknown")
            name = user_profile.get("name", "Unknown")

            worksheet.append_row([
                datetime.datetime.now().isoformat(),
                sis_user_id,
                name,
                feedback["subject"],
                feedback["response_type"],
                feedback["question"],
            ])
        except Exception as e:
            print(f"Error submitting grade for Student {user_id}: {e}")



if __name__ == "__main__":
    main()
