from dotenv import load_dotenv
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
import ast
import base64
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
import fitz

load_dotenv()

app = Flask(__name__)
port = os.getenv("PORT")
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "https://your-frontend-domain.com"]}}, supports_credentials=True) 


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

def extractTopValueFromOCRData(filter_data, titles, done):
    topMap = {}

    data_text = filter_data['text']
    data_top = filter_data['top']
    visited = set()

    stop_words = {"is", "of", "the", "and", "a", "an", "in", "on", "at", "to", "for", "by", "with", "as", "from"}

    for title in titles:
        words = title.split(" ")
        topvalue = 0
        n = 0
        misMatch = 0

        if title in done:
            continue

        for word in words:
            if len(word) > 3 and word.lower() not in stop_words and word not in visited and word in data_text:
                try:
                    idx = data_text.index(word)
                    topvalue += data_top[idx]
                    n += 1
                    visited.add(word)
                except ValueError:
                    continue 
                if len(word) > 3 and word.lower() not in stop_words and word not in data_text:
                    misMatch += 1
            
        if n > 0 and n /(n + misMatch) > 0.4:
            topMap[title] = topvalue / n

    return topMap

@app.route("/handleIndex",methods=['POST'])
def handleIndex():
    index = request.files['index']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(index.read())
        temp_input_path = temp_input.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ocr:
        ocr_output_path = temp_ocr.name

    ocrmypdf.ocr(
        temp_input_path,
        ocr_output_path,
        force_ocr=True,
        oversample=600,
        optimize=3,
        deskew=True,
        rotate_pages=True,
        language='eng',
        skip_text=False
    )

    doc = fitz.open(ocr_output_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    words = GeminiAPI.extract_particulars(full_text)
    cleaned = words.strip("`python\n").strip("`")
    words = ast.literal_eval(cleaned)

    return jsonify({'text': words, 'len': len(doc)}), 200

@app.route("/handlefirst",methods=['POST'])
def handleFirstDocument():
    pdf_file = request.files['pdf']
    isOrignal = request.form['isOrignal'].lower() == "true"
    print("isorignal: ", isOrignal)
    if not isOrignal:
        advoSig = request.files['advocate-sig']
        clieSig = request.files['client-sig']
    keyWords_json = request.form['words']
    keyWords = json.loads(keyWords_json)
    addKeywords = set()
    isEnclosures = False
    isVerification = False

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ocr:
        ocr_output_path = temp_ocr.name

    if not isOrignal:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_advo_sig:
            temp_advo_sig.write(advoSig.read())
            temp_advo_sig_path = temp_advo_sig.name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_clie_sig:
            temp_clie_sig.write(clieSig.read())
            temp_clie_sig_path = temp_clie_sig.name

    try:
        ocrmypdf.ocr(
            temp_input_path,
            ocr_output_path,
            force_ocr=True,
            oversample=600,
            optimize=3,
            deskew=True,
            rotate_pages=True,
            language='eng',
            skip_text=False
        )

        reader = PdfReader(ocr_output_path)
        writer = PdfWriter()
        images = convert_from_path(ocr_output_path)

        img_width, img_height = images[0].size
        bookMark = []
        signature = []

        for i, page in enumerate(reader.pages):
            text = pytesseract.image_to_string(images[i])
            if not isOrignal:
                if not isEnclosures and 'ENCLOSURES' in text:
                    isEnclosures = True
                
                if not isVerification and 'VERIFICATION' in text:
                    isVerification = True

                if "FILED THROUGH" in text or 'APPLICANT' in text:
                    print(f"enter in if with enclosure: {isEnclosures}, verficiation: {isVerification}")
                    data = pytesseract.image_to_data(images[i], output_type=Output.DICT)
                    for j in range(len(data['text'])-1,0,-1):
                        if data['text'][j-1] == 'FILED' and data['text'][j] == 'THROUGH':
                            signature.append({
                                'x': data['left'][j - 1] - 5,
                                'y': data['top'][j],
                                'h': data['height'][j],
                                'w': data['width'][j] + data['width'][j-1] + 10,
                                'page': i + 1,
                                'type': "advocate"
                            })
                    
                        elif (data['text'][j] == 'APPLICANT'):
                            print(f"Appilcant signature findout with enclosure: {isEnclosures}, verficiation: {isVerification}")
                            if isVerification or isEnclosures:
                                signature.append({
                                    'x': data['left'][j] - 5,
                                    'y': data['top'][j],
                                    'h': data['height'][j],
                                    'w': data['width'][j] + 10, 
                                    'page': i + 1,
                                    'type': "client"
                                })

            for keyWord in keyWords:
                if keyWord in addKeywords:
                    continue
                
                if is_this_page(text,keyWord):
                    bookMark.append({
                        "page": i+1,
                        "title": keyWord
                    })
                    isVerification = False
                    isEnclosures = False
                    addKeywords.add(keyWord)

        for i, page in enumerate(reader.pages):
            if not isOrignal:
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
        if not isOrignal:
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
    isOrignal = request.form['isOrignal']
    if not isOrignal:
        advoSig = request.files['advocate-sig']
        clieSig = request.files['client-sig']

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ocr:
        ocr_output_path = temp_ocr.name

    if not isOrignal:
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
        images = convert_from_path(ocr_output_path)

        img_width, img_height = images[0].size
        signature = []

        if not isOrignal:
            for i, page in enumerate(reader.pages):
                text = pytesseract.image_to_string(images[i])
                data = pytesseract.image_to_data(images[i], output_type=Output.DICT)
            
                if "FILED THROUGH" in text or text.count("PETITIONER") > 1 or 'DEPONENT' in text:
                    for j in range(len(data['text'])-1, 0, -1):
                        if data['text'][j-1] == 'FILED' and data['text'][j] == 'THROUGH':
                            signature.append({
                                'x': data['left'][j - 1] - 5,
                                'y': data['top'][j],
                                'h': data['height'][j],
                                'w': data['width'][j] + data['width'][j - 1] + 10,
                                'page': i + 1,
                                'type': "advocate"
                            })
                        elif (data['text'][j] == 'PETITIONER' or data['text'][j] == 'DEPONENT') and data['text'][j] != '...PETITIONER':
                            signature.append({
                                'x': data['left'][j] - 5,
                                'y': data['top'][j],
                                'h': data['height'][j],
                                'w': data['width'][j] + 10,
                                'page': i + 1,
                                'type': "client"
                            })

        for i, page in enumerate(reader.pages):
            if not isOrignal:
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
        if not isOrignal:
            os.remove(temp_advo_sig_path)
            os.remove(temp_clie_sig_path)


@app.route("/handleFinalIndexPDF", methods=["POST"])
def handleFinalIndexPDF():
    pdf_file = request.files["pdf"]
    isOrignal = request.form['isOrignal'].lower() == "true"
    index_map = json.loads(request.form["index_map"])
    if not isOrignal:
        advoSig = request.files['advocate-sig']
    doneTit = set()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name
    
    if not isOrignal:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_advo_sig:
            temp_advo_sig.write(advoSig.read())
            temp_advo_sig_path = temp_advo_sig.name

    try:
        reader = PdfReader(temp_input_path)
        writer = PdfWriter()
        images = convert_from_path(temp_input_path)
        x_pg_col = None

        for i, page in enumerate(reader.pages):
            img = images[i]
            data = pytesseract.image_to_data(img, output_type=Output.DICT)
            pdf_width = float(page.mediabox.width)
            pdf_height = float(page.mediabox.height)
            img_width, img_height = img.size
            scale_x = pdf_width / img_width
            scale_y = pdf_height / img_height

            if i == 0:
                for j in range(len(data["text"])):
                    if data["text"][j].strip().lower() in ["pg", "pg.", "pg no", "pg. no", "pg. no.", "pg no.", "pg.no", "pgno","page", "page no", "page no.", "page number", "pageno", "page.no"]:
                        x_pg_col = data["left"][j] * scale_x
                        break

            if x_pg_col is None:
                return jsonify({"error": "Could not detect 'Pg. No.' column heading."}), 400

            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=(pdf_width, pdf_height))
            can.setFont("Helvetica", 12)
            filter_data = {"top": data['top'],"text": data['text']}
            titles = index_map.keys()
            
            topMap = extractTopValueFromOCRData(filter_data,titles,doneTit)
            
            for key in topMap:
                if key not in doneTit:
                    y_pos = pdf_height - (float(topMap.get(key)) * scale_y)
                    can.drawString(x_pg_col, y_pos, str(index_map[key]))
                    doneTit.add(key)

            if not isOrignal and (i == len(reader.pages) -1 or i == len(reader.pages) - 2):
                if 'FILED' in data['text'] and 'THROUGH' in data['text']:
                    idx = data['text'].index('FILED')
                    x_sig = float((data['left'][idx] - 5) * scale_x)
                    y_sig = pdf_height - float(data['top'][idx]*scale_y) - 2*float(data['height'][idx]*scale_y) - float(100*scale_y)
                    w_sig = data['width'][idx] + data['width'][idx + 1] + 10 
                    can.drawImage(temp_advo_sig_path,x_sig,y_sig,w_sig*scale_x,height=40,mask='auto')

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
        if not isOrignal:
            os.remove(temp_advo_sig_path)


@app.route("/addBookMarks", methods=['POST'])
def addBookMarks():
    pdf_file = request.files["pdf"]
    bookmark = json.loads(request.form["bookmark"])

    # Save the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name

    reader = PdfReader(temp_input_path)
    writer = PdfWriter()

    for page_number, page in enumerate(reader.pages):
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

    return send_file(output_path, as_attachment=True, download_name="bookmarked_signed.pdf")

@app.route("/",methods=['GET'])
def helloRoute():
    return jsonify({"Name":"suzain"})

if __name__ == '__main__':
    app.run(debug=True)
