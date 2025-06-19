import os
from urllib.request import urlretrieve
from utils import parse_iso
from handwriting_ocr_client import HandwritingOCRClient
from canvas_manager import CanvasManager


class OCRProcessor:
    def __init__(self, token, download_dir):
        self.ocr_client = HandwritingOCRClient(api_token=token)
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self.tracking = {}

    def download_pdf(self, attachment, student_id):
        filename = f"{student_id}_{attachment['filename']}"
        filepath = os.path.join(self.download_dir, filename)
        print(f"Downloading: {filename}")
        urlretrieve(attachment["url"], filepath)
        return filepath
    
    def detect_response_type(self, ocr_txt_path):
        try:
            with open(ocr_txt_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()  # Case-insensitive search
            if "long response" in content:
                return "Long Response"
            elif "short response" in content:
                return "Short Response"
            else:
                return "Unknown"
        except Exception as e:
            print(f"Failed to read OCR text: {e}")
            return "Error"
        
    def process_submission(self, submission):
        user_id = str(submission.user_id)
        history = submission.submission_history or []
        
        # if user_id == '126839':
        #     breakpoint()

        if not history:
            return

        latest = CanvasManager.get_latest_submission(history)
        submitted_at_str = latest.get("submitted_at")
        grade_str = latest.get("grade")
        graded_at_str = submission.graded_at

        if not submitted_at_str:
            return
        
        if grade_str == 'complete':
            return

        # submitted_at = parse_iso(submitted_at_str)
        # graded_at = parse_iso(graded_at_str)

        # if graded_at and submitted_at <= graded_at:
        #     return

        for attachment in latest.get("attachments", []):
            if attachment.get("content-type") == "application/pdf":
                pdf_path = self.download_pdf(attachment, user_id)
                ocr_txt_path = pdf_path.replace(".pdf", "_ocr.txt")

                if os.path.exists(ocr_txt_path):
                    print(f"OCR already exists: {ocr_txt_path}")
                else:
                    try:
                        doc_id = self.ocr_client.upload_document(pdf_path)
                        self.ocr_client.wait_until_processed(doc_id)
                        self.ocr_client.download_result(doc_id, ocr_txt_path)
                    except Exception as e:
                        print(f"Error processing {pdf_path}: {e}")
                        continue

                # 👉 Detect response type here
                response_type = self.detect_response_type(ocr_txt_path)
                print(f"Detected response type: {response_type}")

                # 👉 Store response_type in tracking
                self.tracking[user_id] = {
                    "submission_id": submission.id,
                    "ocr_text_file": ocr_txt_path,
                    "response_type": response_type,
                    "canvas_submission": submission
                }

