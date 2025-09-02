import os
import asyncio
import gspread
import datetime

from requests import HTTPError
from canvas_manager import CanvasManager
from ocr_processor import OCRProcessor
from feedback_generator import FeedbackGenerator, UnknownResponseTypeError
from config import API_URL, COURSE_ID, ASSIGNMENT_ID, DOWNLOAD_DIR
from urllib.request import urlretrieve
import logging
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

def load_token(token_path):
    with open(os.path.expanduser(token_path), "r") as f:
        return f.read().strip()

def check_submission(submission):
    user_id = str(submission.user_id)
    history = submission.submission_history or []
    
    # if user_id == '35378':
    #     breakpoint()

    if not history:
        return False

    latest = CanvasManager.get_latest_submission(history)
    submission_workflow_state = latest.get("workflow_state")
    submission_grade = latest.get("grade")
    
    # skip unsubmitted
    if submission_workflow_state == "unsubmitted":
        logging.info(f"Skipping Student {user_id} - Submission state: {submission_workflow_state}")
        return False
    
    # skip graded and submissions.
    if submission_workflow_state == "graded" and submission_grade in ["complete", "incomplete", "excused"]:
        logging.info(f"Skipping Student {user_id} - Submission state: {submission_workflow_state} or Grade: {submission_grade}")
        return False

    return True

def download_pdf(attachment, student_id):
    # Create a unique filename using md5 hash of url + original filename
    url = attachment["url"]
    original_filename = attachment['filename']
    hash_input = (url + original_filename).encode('utf-8')
    md5_hash = hashlib.md5(hash_input).hexdigest()
    ext = os.path.splitext(original_filename)[1]
    filename = f"{md5_hash}{ext}"
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    logging.info(f"Downloading: {filename}")
    urlretrieve(url, filepath)
    return filepath


def main():
    logging.info("Initializing components...")
    canvas_token = os.getenv('CANVAS_API_TOKEN')
    ocr_token = os.getenv('HANDWRITING_OCR_TOKEN')

    if not canvas_token:
        raise ValueError("CANVAS_API_TOKEN environment variable is not set")
    if not ocr_token:
        raise ValueError("HANDWRITING_OCR_TOKEN environment variable is not set")

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
    
    feedback_gen = FeedbackGenerator()

    logging.info("Checking for unmarked or resubmitted submissions...")
    submissions = canvas_mgr.get_submissions()
    unmarked_submissions = [s for s in submissions if check_submission(s)]

    # Submit grade and comment via Canvas, and process OCR per user_id
    for submission in unmarked_submissions:
        # if not submission.user_id == 32280:
        #     logging.info(f"Skipping Student {submission.user_id} - Not the target student.")
        #     continue
        
        try:
            canvas_user_id = str(submission.user_id)
            submissions_history = submission.submission_history or []
            latest_submission = CanvasManager.get_latest_submission(submissions_history)
            latest_attachment = latest_submission.get("attachments", [{}])[0]
            
            if not latest_attachment or latest_attachment.get("content-type") != "application/pdf":
                logging.warning(f"Skipping Student {canvas_user_id} - No valid PDF attachment found.")
                try:
                    canvas_mgr.submit_grade_and_comment(
                        user_id=canvas_user_id,
                        comment_text="We were unable to find a valid PDF attachment in your submission. Please ensure you have uploaded a PDF file. If you are unsure, please ask your teacher. Once you have done this, please resubmit your response.",
                        grade="incomplete"
                    )
                    logging.info(f"Submitted incomplete grade for Student {canvas_user_id} due to missing PDF.")
                except Exception as e:
                    logging.error(f"Error submitting incomplete grade for Student {canvas_user_id}: {e}")
                continue
            
            # downloading the PDF file
            pdf_path = download_pdf(latest_attachment, canvas_user_id)
            logging.info(f"Downloaded PDF for Student {canvas_user_id}: {pdf_path}")
            
            # Perform OCR on the downloaded PDF
            ocr_txt = ocr_processor.perform_ocr(pdf_path)
            logging.info(f"OCR processed for Student {canvas_user_id}.")
            
            # submit to feedback generator
            logging.info(f"Generating feedback for Student {canvas_user_id}.")
            feedback_response = asyncio.run(feedback_gen.generate_feedback(ocr_txt))
            
            # submit the feedback to canvas and mark the submission
            canvas_mgr.submit_grade_and_comment(
                user_id=canvas_user_id,
                comment_text=feedback_response["feedback_html"],
            )
            print(f"Submitted grade and comment for Student {canvas_user_id}.")

            try:
                user_profile = canvas_mgr.get_user_profile(canvas_user_id)
                sis_user_id = user_profile.get("sis_user_id", "Unknown")
                name = user_profile.get("name", "Unknown")

                worksheet.append_row([
                    datetime.datetime.now().isoformat(),
                    sis_user_id,
                    name,
                    feedback_response["subject"],
                    feedback_response["response_type"],
                    feedback_response["question"],
                    feedback_response["teacher_email"],
                ])
            except Exception as e:
                logging.warning(f"Error logging feedback for Student {canvas_user_id}: {e}")
        except Exception as e:
            if isinstance(e, UnknownResponseTypeError):
                try:
                    canvas_mgr.submit_grade_and_comment(
                        user_id=canvas_user_id,
                        comment_text="We were unable to determine if this response was a short or long response. Please ensure that you have used the template for your response. If you are unsure, please ask your teacher. Once you have done this, please resubmit your response.",
                        grade="incomplete"
                    )
                    logging.info(f"Submitted incomplete grade for Student {canvas_user_id} with unknown response type.")
                except Exception as e:
                    logging.error(f"Error submitting incomplete grade for Student {canvas_user_id}: {e}")

                logging.warning(f"Unknown response type for Student {canvas_user_id}. Skipping...")
            elif isinstance(e, HTTPError):
                # check if error is 422
                if e.response.status_code == 422:
                    try:
                        canvas_mgr.submit_grade_and_comment(
                            user_id=canvas_user_id,
                            comment_text="There was an issue processing your submission. Please check if your submission file size is less than 20MB. If it is larger, please reduce the file size and resubmit.",
                            grade="incomplete"
                        )
                        logging.info(f"Submitted incomplete grade for Student {canvas_user_id} due to HTTP error.")
                    except Exception as e:
                        logging.error(f"Error submitting incomplete grade for Student {canvas_user_id}: {e}")
                elif e.response.status_code == 500:
                    try:
                        canvas_mgr.submit_grade_and_comment(
                            user_id=canvas_user_id,
                            comment_text=f"There was an internal server error while processing your submission. Please try again later. Error: {e.response.text}",
                            grade="incomplete"
                        )
                        logging.info(f"Submitted incomplete grade for Student {canvas_user_id} due to server error.")
                    except Exception as e:
                        logging.error(f"Error submitting incomplete grade for Student {canvas_user_id}: {e.response.text}")
                else:
                    logging.error(f"HTTP error for Student {canvas_user_id}: {e}")
            else:
                try:
                    canvas_mgr.submit_grade_and_comment(
                        user_id=canvas_user_id,
                        comment_text="We encountered an error while processing your submission. Please see IT for assistance. <br> Error: " + str(e),
                        grade="incomplete"
                    )
                    logging.info(f"Submitted incomplete grade for Student {canvas_user_id} with unknown response type.")
                except Exception as e:
                    logging.error(f"Error submitting incomplete grade for Student {canvas_user_id}: {e}")

                logging.error(f"Error submitting grade for Student {canvas_user_id}: {e}")



if __name__ == "__main__":
    main()
