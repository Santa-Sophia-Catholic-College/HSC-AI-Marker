import os
import time
import requests

class HandwritingOCRClient:
    def __init__(self, api_token, poll_interval=10):
        """
        Initializes the OCR client.

        :param api_token: API token string for authentication.
        :param poll_interval: Time in seconds between status polls.
        """
        self.api_token = api_token
        self.poll_interval = poll_interval
        self.base_url = "https://www.handwritingocr.com/api/v3"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }

    def upload_document(self, file_path, action="transcribe", delete_after=604800):
        """
        Uploads a document to the OCR service.

        :param file_path: Path to the PDF file.
        :param action: 'transcribe', 'tables', or 'extractor'.
        :param delete_after: Time in seconds until auto-deletion (default 7 days).
        :return: Document ID from the OCR service.
        """
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, "application/pdf")
            }
            data = {
                "action": action,
                "delete_after": delete_after
            }
            response = requests.post(f"{self.base_url}/documents", headers=self.headers, files=files, data=data)
            response.raise_for_status()
            return response.json()["id"]

    def wait_until_processed(self, document_id):
        """
        Polls the OCR service until the document status is 'processed'.

        :param document_id: The document ID returned from upload.
        :return: JSON data containing processing result metadata.
        """
        url = f"{self.base_url}/documents/{document_id}"
        while True:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "processed":
                    return data
                print(f"Status: {data.get('status')}, waiting...")
            elif response.status_code == 202:
                print("Still processing...")
            else:
                response.raise_for_status()
            time.sleep(self.poll_interval)

    def download_result(self, document_id, output_path, fmt="txt"):
        """
        Downloads the OCR-processed document result.

        :param document_id: Document ID to fetch the result for.
        :param output_path: Path to save the output.
        :param fmt: Output format: 'txt', 'docx', 'json', etc.
        """
        url = f"{self.base_url}/documents/{document_id}.{fmt}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"OCR result saved to: {output_path}")
