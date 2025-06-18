import google.generativeai as genai

class GeminiAPI:
    @staticmethod
    def extract_particulars(text):
        genai.configure(api_key="AIzaSyBUJ92pSMaT_gc-ukOFf4QKTOxWCcwHbOE")

        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        response = model.generate_content(
            f"{text}\n\n\n  **Give me all 'Particulars' titles from the provided text (extracted from a PDF) as a Python list. Give only the list, nothing else.**"
        )

        try:
            return response.text.strip()
        except Exception as e:
            print("Error parsing Gemini response:", e)
            return []



