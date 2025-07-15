import google.generativeai as genai
import os

class GeminiAPI:
    @staticmethod
    def extract_particulars(text):
        genai.configure(api_key=os.getenv("AI_API_KEY"))
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")

        response = model.generate_content(
            f"""{text}\n\n\n  **Give me all 'Particulars' titles from the provided text (extracted from a PDF) as a Python list. Give only the list, nothing else.** 
                Note: Particulars are also in the block like `particular_name:\ndescribtion of particular. i want both in single string with line end charator`
            """
        )

        try:
            return response.text.strip()
        except Exception as e:
            print("Error parsing Gemini response:", e)
            return []

    @staticmethod
    def checkIsPageWithTitle(title,fullText):
        genai.configure(api_key=os.getenv("AI_API_KEY"))
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        
        response = model.generate_content([
            f"""You are an intelligent assistant that analyzes scanned or OCR-processed PDF page text.

            Your task is to determine whether the given page content likely contains a heading, title, or reference related to the target keyword.

            ### Target keyword:
            "{title}"

            ### Page content:
            \"\"\"
            {fullText}
            \"\"\"

            Respond with just "Yes" if the keyword (or a close match) is present, or "No" if it is not.
            """ 
        ])

        try:
            return response.text.strip()
        except Exception as err:
            print("Error parsing Gemini response:", err)
            return ""