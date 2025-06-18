from flask import Flask, request, send_file
from io import BytesIO
from pypdf import PdfReader, PdfWriter
import json
import tempfile
import ocrmypdf
from flask_cors import CORS
from pdf2image import convert_from_path
import pytesseract
import os
from pytesseract import Output
from flask import jsonify
from gemini_api import GeminiAPI
import ast
from reportlab.pdfgen import canvas
import base64


app = Flask(__name__)
CORS(app) 


def is_this_page(text, keyword):
    words = keyword.upper().split(" ")
    n = 0
    mismatch = 0
    length = len(words)
    for i, word in enumerate(words):
        if i + 1 < length and (words[i] == 'ALONG' and words[i + 1] == 'WITH'):
            break
        if word not in text.upper():
            mismatch += 1
        n += 1
    return mismatch / n <= 0.2

# @app.route('/process-pdf', methods=['POST'])
# def process_pdf():
#     if 'pdf' not in request.files or 'bookMark' not in request.form:
#         return "Missing fields", 400
    
#     try:
#         pdf_file = request.files['pdf']
#         bookmarks = json.loads(request.form['bookMark'])

#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
#             temp_input.write(pdf_file.read())
#             input_path = temp_input.name

#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ocr:
#             ocr_output_path = temp_ocr.name

#         ocrmypdf.ocr(input_path, ocr_output_path, deskew=True, force_ocr=True)

#         reader = PdfReader(ocr_output_path)
#         writer = PdfWriter()

#         for i, page in enumerate(reader.pages):
#             writer.add_page(page)
#             for bm in bookmarks:
#                 if bm["pageNo"] == i + 1:
#                     writer.add_outline_item(bm["title"], i)

#         output_stream = BytesIO()
#         writer.write(output_stream)
#         output_stream.seek(0)

#         return send_file(output_stream, as_attachment=True, download_name="processed.pdf", mimetype="application/pdf"),200
#     except Exception as err:
#         return str(err), 500
    

@app.route("/handleIndex",methods=['POST'])
def handleIndex():
    index = request.files['index']

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(index.read())
        temp_input_path = temp_input.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ocr:
        ocr_output_path = temp_ocr.name

    ocrmypdf.ocr(temp_input_path, ocr_output_path, deskew=True, force_ocr=True)

    images = convert_from_path(ocr_output_path,poppler_path="C:\\Program Files\\poppler-24.08.0\\Library\\bin")
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    
    words = GeminiAPI.extract_particulars(text)
    cleaned = words.strip("`python\n").strip("`")
    words = ast.literal_eval(cleaned)
    
    return jsonify({'text': words,'len': len(images)}), 200

@app.route("/handlefirst",methods=['POST'])
def handleFirstDocument():
    pdf_file = request.files['pdf']
    advoSig = request.files['advocate-sig']
    clieSig = request.files['client-sig']
    keyWords_json = request.form['words']
    keyWords = json.loads(keyWords_json)
    addKeywords = set()

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ocr:
        ocr_output_path = temp_ocr.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_advo_sig:
        temp_advo_sig.write(advoSig.read())
        temp_advo_sig_path = temp_advo_sig.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_clie_sig:
        temp_clie_sig.write(clieSig.read())
        temp_clie_sig_path = temp_clie_sig.name

    try:
        ocrmypdf.ocr(temp_input_path, ocr_output_path, deskew=True, force_ocr=True)

        reader = PdfReader(ocr_output_path)
        writer = PdfWriter()
        images = convert_from_path(ocr_output_path,poppler_path="C:\\Program Files\\poppler-24.08.0\\Library\\bin")

        img_width, img_height = images[0].size
        bookMark = []
        signature = []
        for i, page in enumerate(reader.pages):
            text = pytesseract.image_to_string(images[i])

            for keyWord in keyWords:
                if "ANNEXURE" in keyWord.upper():
                    break
            
                if keyWord in addKeywords:
                    continue

                if is_this_page(text,keyWord):
                    bookMark.append({
                        "page": i+1,
                        "title": keyWord
                    })
                    addKeywords.add(keyWord)

            if "FILED THROUGH" in text or text.count("PETITIONER") > 1 or 'DEPONENT' in text:
                data = pytesseract.image_to_data(images[i], output_type=Output.DICT)
                for j in range(len(data['text'])-1,0,-1):
                    if data['text'][j-1] == 'FILED' and data['text'][j] == 'THROUGH':
                        signature.append({
                            'x': data['left'][j - 1],
                            'y': data['top'][j],
                            'h': data['height'][j],
                            'w': data['width'][j] + data['width'][j-1],
                            'page': i + 1,
                            'type': "advocate"
                        })
                    
                    elif (data['text'][j] == 'PETITIONER' or data['text'][j] == 'DEPONENT'):
                        signature.append({
                            'x': data['left'][j],
                            'y': data['top'][j],
                            'h': data['height'][j],
                            'w': data['width'][j],
                            'page': i + 1,
                            'type': "client"
                        })

        for i, page in enumerate(reader.pages):
            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))

            pdf_width = float(page.mediabox.width)
            pdf_height = float(page.mediabox.height)
            scale_x = pdf_width / img_width
            scale_y = pdf_height / img_height
            
            for sig in signature:
                if sig['page'] == i + 1:
                    if sig['type'] == 'advocate':
                        sig_file = temp_advo_sig_path
                        x_pdf = float(sig['x']) * scale_x
                        y_pdf = pdf_height - (float(sig['y']) * scale_y) - (float(sig['h']) * scale_y) - float(sig['h']* scale_y) - float(100 * scale_y)
                        can.drawImage(sig_file, x_pdf, y_pdf,height=40,width=sig['w']*scale_x ,mask='auto')
                    else:
                        sig_file = temp_clie_sig_path
                        x_pdf = float(sig['x']) * scale_x
                        y_pdf = pdf_height - (float(sig['y']) * scale_y)
                        can.drawImage(sig_file, x_pdf, y_pdf,height=40,width=sig['w']*scale_x ,mask='auto')

            can.save()
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            if overlay_pdf.pages:
                page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)

        output_stream = BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        bookMark.append({
            "page": len(reader.pages),
            "title": "last"
        })

        pdf_base64 = base64.b64encode(output_stream.getvalue()).decode('utf-8')

        return jsonify({
            "pdf": pdf_base64,
            "bookmarks": bookMark
        }), 200
    
    finally:
        os.remove(temp_input_path)
        os.remove(ocr_output_path)
        os.remove(temp_advo_sig_path)
        os.remove(temp_clie_sig_path)


@app.route("/handleAnnexure",methods=['POST'])
def handleAnnexure():
    pdf_file = request.files['pdf']

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ocr:
        ocr_output_path = temp_ocr.name

    ocrmypdf.ocr(temp_input_path, ocr_output_path, deskew=True, force_ocr=True)
    reader = PdfReader(ocr_output_path)
    writer = PdfWriter()

    for i,page in enumerate(reader.pages):
        writer.add_page(page)

    output_stream = BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)

    return send_file(output_stream,mimetype="application/pdf",download_name="process_pdf.pdf",as_attachment=True), 200


@app.route("/handleFinal", methods=['POST'])
def handleFinalDocument():
    pdf_file = request.files['pdf']
    advoSig = request.files['advocate-sig']
    clieSig = request.files['client-sig']

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ocr:
        ocr_output_path = temp_ocr.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_advo_sig:
        temp_advo_sig.write(advoSig.read())
        temp_advo_sig_path = temp_advo_sig.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_clie_sig:
        temp_clie_sig.write(clieSig.read())
        temp_clie_sig_path = temp_clie_sig.name

    try:
        ocrmypdf.ocr(temp_input_path, ocr_output_path, deskew=True, force_ocr=True)

        reader = PdfReader(ocr_output_path)
        writer = PdfWriter()
        images = convert_from_path(ocr_output_path, poppler_path="C:\\Program Files\\poppler-24.08.0\\Library\\bin")

        img_width, img_height = images[0].size
        signature = []

        for i, page in enumerate(reader.pages):
            text = pytesseract.image_to_string(images[i])
            data = pytesseract.image_to_data(images[i], output_type=Output.DICT)
            
            if "FILED THROUGH" in text or text.count("PETITIONER") > 1 or 'DEPONENT' in text:
                for j in range(len(data['text'])-1, 0, -1):
                    if data['text'][j-1] == 'FILED' and data['text'][j] == 'THROUGH':
                        signature.append({
                            'x': data['left'][j - 1],
                            'y': data['top'][j],
                            'h': data['height'][j],
                            'w': data['width'][j] + data['width'][j - 1],
                            'page': i + 1,
                            'type': "advocate"
                        })
                    elif (data['text'][j] == 'PETITIONER' or data['text'][j] == 'DEPONENT') and data['text'][j] != '...PETITIONER':
                        signature.append({
                            'x': data['left'][j],
                            'y': data['top'][j],
                            'h': data['height'][j],
                            'w': data['width'][j],
                            'page': i + 1,
                            'type': "client"
                        })

        for i, page in enumerate(reader.pages):
            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))

            pdf_width = float(page.mediabox.width)
            pdf_height = float(page.mediabox.height)
            scale_x = pdf_width / img_width
            scale_y = pdf_height / img_height   

            for sig in signature:
                if sig['page'] == i + 1:
                    if sig['type'] == 'advocate':
                        sig_file = temp_advo_sig_path
                        x_pdf = float(sig['x']) * scale_x
                        y_pdf = pdf_height - (float(sig['y']) * scale_y) - (float(sig['h']) * scale_y) - float(sig['h']* scale_y) - float(100 * scale_y)
                        can.drawImage(sig_file, x_pdf, y_pdf, height=40, width=sig['w']*scale_x, mask='auto')
                    else:
                        sig_file = temp_clie_sig_path
                        x_pdf = float(sig['x']) * scale_x
                        y_pdf = pdf_height - (float(sig['y']) * scale_y)
                        can.drawImage(sig_file, x_pdf, y_pdf, height=40, width=sig['w']*scale_x, mask='auto')

            can.save()
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            if overlay_pdf.pages:
                page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)

        output_stream = BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)

        return send_file(output_stream,mimetype="application/pdf",download_name="process_pdf.pdf",as_attachment=True), 200

    finally:
        os.remove(temp_input_path)
        os.remove(ocr_output_path)
        os.remove(temp_advo_sig_path)
        os.remove(temp_clie_sig_path)


@app.route("/handleFinalIndexPDF", methods=["POST"])
def handleFinalIndexPDF():
    pdf_file = request.files["pdf"]
    index_map = json.loads(request.form["index_map"])

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name

    try:
        reader = PdfReader(temp_input_path)
        writer = PdfWriter()
        images = convert_from_path(temp_input_path, poppler_path="C:\\Program Files\\poppler-24.08.0\\Library\\bin")

        x_pg_col = None
        for i, page in enumerate(reader.pages):
            img = images[i]
            data = pytesseract.image_to_data(img, output_type=Output.DICT)
            print(data["line_num"])
            pdf_width = float(page.mediabox.width)
            pdf_height = float(page.mediabox.height)
            img_width, img_height = img.size
            scale_x = pdf_width / img_width
            scale_y = pdf_height / img_height

            if i == 0:
                for j in range(len(data["text"])):
                    if data["text"][j].strip().lower() in ["pg. no.", "pg.", "page no.", "page"]:
                        x_pg_col = data["left"][j] * scale_x
                        break

            if x_pg_col is None:
                return jsonify({"error": "Could not detect 'Pg. No.' column heading."}), 400

            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=(pdf_width, pdf_height))
            can.setFont("Helvetica", 10)

            used_lines = set()
            for idx in range(len(data["text"])):
                if data["line_num"][idx] in used_lines:
                    continue

                line_num = data["line_num"][idx]
                line_texts = []
                top = None

                for j in range(len(data["text"])):
                    if data["line_num"][j] == line_num:
                        if top is None:
                            top = data["top"][j]
                        line_texts.append(data["text"][j])

                full_line = " ".join(line_texts).strip()

                for title in index_map:
                    # print({"full line": full_line,"title":title})
                    if full_line.lower() != "" and str(title.strip().lower()) in full_line.lower():
                        y_pos = pdf_height - (top * scale_y)
                        can.drawString(x_pg_col, y_pos, str(index_map[title]))
                        used_lines.add(line_num)
                        break

            can.save()
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            if overlay_pdf.pages:
                page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)

        output_stream = BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)

        return send_file(output_stream,mimetype="application/pdf",download_name="process_pdf.pdf",as_attachment=True), 200

    finally:
        os.remove(temp_input_path)

@app.route("/addBookMarks", methods=['POST'])
def addBookMarks():
    pdf_file = request.files["pdf"]
    bookmark = json.loads(request.form["bookmark"]) 

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name

    reader = PdfReader(temp_input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    for page_str, title in bookmark.items():
        try:
            page_number = int(page_str)
            if 0 <= page_number < len(reader.pages):
                writer.add_outline_item(title, page_number - 1)
        except ValueError:
            continue

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_output:
        writer.write(temp_output)
        output_path = temp_output.name

    return send_file(output_path, as_attachment=True, download_name="bookmarked.pdf")

if __name__ == '__main__':
    app.run(debug=True)