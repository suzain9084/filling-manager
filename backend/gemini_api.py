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

    def extract_top_value_of_particulars(data,title):
        try:
            genai.configure(api_key="AIzaSyBUJ92pSMaT_gc-ukOFf4QKTOxWCcwHbOE")
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")

            prompt = f"""
                You are given OCR data in the form of two lists:

                    - 'text': a list of corresponding text strings (same length as 'top')
                    - 'top': a list of vertical positions (integers) for each word

                Your task is to reconstruct the lines of text from this OCR data. Words that have the same or very close 'top' values (within ±5 pixels) should be grouped into the same line.

                Return only the final result as a JSON dictionary where:
                    - each value is the reconstructed line (a space-separated string made from corresponding words)
                    - each key is the top value of first word in this line
                    title: top ....

                ### Input:
                text = {data['text']}
                top = {data['top']}

                After reconstructing the lines, match and append one additional line to each title from the provided list by identifying the best match. While doing so, remove any leading prefixes such as numbering (e.g., "1.", "2.", etc.) from the matched lines and do not add line which is not in title.
                ### title list:
                title = {title}

                Return only the result dictionary. Do not include any explanation or code.
                """

            print(prompt)
            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            print("Error during Gemini API call or response parsing:", e)
            return {}
        