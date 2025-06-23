import os

from utils import parse_iso
from handwriting_ocr_client import HandwritingOCRClient
from canvas_manager import CanvasManager

class UnsupportedFileTypeError(Exception):
    """Custom exception for unsupported file types."""
    pass


class OCRProcessor:
    def __init__(self, token, download_dir):
        self.ocr_client = HandwritingOCRClient(api_token=token)
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self.tracking = {}

    def perform_ocr(self, file_path):
        # get the file type
        if not file_path.lower().endswith('.pdf'):
            raise UnsupportedFileTypeError("Only PDF files are supported for OCR.")
    
        ocr_txt_path = file_path.replace(".pdf", "_ocr.txt")
        if os.path.exists(ocr_txt_path):
            print(f"OCR file exists: {ocr_txt_path}")
        else:
            # upload the file to the OCR service
            doc_id = self.ocr_client.upload_document(file_path)
            print(f"Uploaded document ID: {doc_id}")
            # wait until the document is processed
            processed_data = self.ocr_client.wait_until_processed(doc_id)
            print(f"Document processed: {processed_data}")
            # download the result
            self.ocr_client.download_result(doc_id, ocr_txt_path)
            print(f"OCR result downloaded to: {ocr_txt_path}")
            
        # open the ocr text file and return the content
        with open(ocr_txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content



        # for attachment in latest.get("attachments", []):
        #     if attachment.get("content-type") == "application/pdf":
        #         pdf_path = self.download_pdf(attachment, user_id)
        #         ocr_txt_path = pdf_path.replace(".pdf", "_ocr.txt")

        #         if os.path.exists(ocr_txt_path):
        #             print(f"OCR already exists: {ocr_txt_path}")
        #         else:
        #             doc_id = self.ocr_client.upload_document(pdf_path)
        #             self.ocr_client.wait_until_processed(doc_id)
        #             self.ocr_client.download_result(doc_id, ocr_txt_path)


        #         # 👉 Detect response type here
        #         response_type = self.detect_response_type(ocr_txt_path)
        #         print(f"Detected response type: {response_type}")

        #         # 👉 Store response_type in tracking
        #         self.tracking[user_id] = {
        #             "submission_id": submission.id,
        #             "ocr_text_file": ocr_txt_path,
        #             "response_type": response_type,
        #             "canvas_submission": submission
        #         }

