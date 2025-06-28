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
import subprocess
import os

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

def isTitleMatched(line,title):
    words = line.split(" ")
    error = 0
    for i in range(len(words)):
        if words[i] not in title:
            error += 1
    return error/len(words) <= 0.2


def extractTopValueFromOCRData(filter_data, titles):
    topMap = {}

    data_text = filter_data['text']
    data_top = filter_data['top']

    # Common short words to ignore
    stop_words = {"is", "of", "the", "and", "a", "an", "in", "on", "at", "to", "for", "by", "with", "as", "from"}

    for title in titles:
        words = title.split(" ")
        topvalue = 0
        n = 0

        for word in words:
            if len(word) > 3 and word.lower() not in stop_words and word in data_text:
                idx = data_text.index(word)
                if idx != -1:
                    topvalue += data_top[idx]
                    n += 1

        valid_words = [w for w in words if len(w) > 3 and w.lower() not in stop_words]
        if n > 0 and len(valid_words) > 0 and n / len(valid_words) > 0.8:
            topMap[title] = topvalue / n

    return topMap


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

def repair_pdf(input_path, output_path):
    """Try multiple PDF repair methods in order of preference"""
    
    # Method 1: Try qpdf with different options
    try:
        subprocess.run(['qpdf', '--linearize', '--replace-input', input_path, output_path], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Method 2: Try qpdf with object-streams disabled
    try:
        subprocess.run(['qpdf', '--object-streams=disable', '--linearize', input_path, output_path], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Method 3: Try qpdf with compression disabled
    try:
        subprocess.run(['qpdf', '--compress-streams=n', '--linearize', input_path, output_path], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Method 4: Use pypdf to rebuild the PDF
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        # Copy all pages
        for page in reader.pages:
            writer.add_page(page)
        
        # Write to output
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        return True
    except Exception as e:
        print(f"pypdf repair failed: {e}")
    
    # Method 5: Try to extract and rebuild with pikepdf (if available)
    try:
        import pikepdf
        with pikepdf.open(input_path) as pdf:
            pdf.save(output_path)
        return True
    except (ImportError, Exception) as e:
        print(f"pikepdf repair failed: {e}")
    
    # Method 6: Use ocrmypdf as a repair tool (it can handle some corruptions)
    try:
        ocrmypdf.ocr(input_path, output_path, skip_text=True, force_ocr=False, skip_big=True)
        return True
    except Exception as e:
        print(f"ocrmypdf repair failed: {e}")
    
    # Method 7: Last resort - try to copy the file directly
    try:
        import shutil
        shutil.copy2(input_path, output_path)
        return True
    except Exception as e:
        print(f"File copy failed: {e}")
    
    return False

def repair_pdf_advanced(input_path, output_path):
    """Advanced PDF repair with multiple fallback strategies"""
    
    # Strategy 1: Try to fix with qpdf using various options
    qpdf_options = [
        ['qpdf', '--linearize', '--replace-input', input_path, output_path],
        ['qpdf', '--object-streams=disable', '--linearize', input_path, output_path],
        ['qpdf', '--compress-streams=n', '--linearize', input_path, output_path],
        ['qpdf', '--deterministic-id', '--linearize', input_path, output_path],
        ['qpdf', '--preserve-encryption', '--linearize', input_path, output_path],
        ['qpdf', '--qdf', '--object-streams=disable', input_path, output_path]
    ]
    
    for option in qpdf_options:
        try:
            subprocess.run(option, check=True, capture_output=True, timeout=30)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    # Strategy 2: Try to extract pages individually and rebuild
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        for i, page in enumerate(reader.pages):
            try:
                # Try to extract each page individually
                page_writer = PdfWriter()
                page_writer.add_page(page)
                
                # Create temporary file for this page
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_page:
                    page_writer.write(temp_page)
                    temp_page_path = temp_page.name
                
                # Try to repair this individual page
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_repaired_page:
                    if repair_pdf(temp_page_path, temp_repaired_page.name):
                        # Read the repaired page and add to main writer
                        repaired_reader = PdfReader(temp_repaired_page.name)
                        if repaired_reader.pages:
                            writer.add_page(repaired_reader.pages[0])
                    else:
                        # If repair fails, try to add the original page
                        writer.add_page(page)
                
                # Clean up temporary files
                os.unlink(temp_page_path)
                os.unlink(temp_repaired_page.name)
                
            except Exception as e:
                print(f"Failed to process page {i}: {e}")
                # Try to add the original page anyway
                try:
                    writer.add_page(page)
                except:
                    pass
        
        # Write the repaired PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        return True
        
    except Exception as e:
        print(f"Advanced repair failed: {e}")
        return False

@app.route("/handleIndex",methods=['POST'])
def handleIndex():
    index = request.files['index']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(index.read())
        temp_input_path = temp_input.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_repaired:
        temp_repaired_path = temp_repaired.name
    
    # Try to repair the PDF with multiple methods
    repair_success = repair_pdf(temp_input_path, temp_repaired_path)
    
    if not repair_success:
        # If basic repair fails, try advanced repair
        repair_success = repair_pdf_advanced(temp_input_path, temp_repaired_path)
    
    if not repair_success:
        # If all repair methods fail, use the original file
        print("Warning: PDF repair failed, using original file")
        temp_repaired_path = temp_input_path

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ocr:
        ocr_output_path = temp_ocr.name

    try:
        ocrmypdf.ocr(temp_repaired_path, ocr_output_path, deskew=True, force_ocr=True)
    except Exception as e:
        print(f"OCR failed: {e}")
        # If OCR fails, try with different options
        try:
            ocrmypdf.ocr(temp_repaired_path, ocr_output_path, deskew=True, force_ocr=True, skip_big=True)
        except Exception as e2:
            print(f"OCR with skip_big also failed: {e2}")
            return jsonify({'error': 'Failed to process PDF'}), 500

    images = convert_from_path(ocr_output_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    
    words = GeminiAPI.extract_particulars(text)
    cleaned = words.strip("`python\n").strip("`")
    words = ast.literal_eval(cleaned)
    
    # Clean up temporary files
    try:
        os.remove(temp_input_path)
        if temp_repaired_path != temp_input_path:
            os.remove(temp_repaired_path)
        os.remove(ocr_output_path)
    except:
        pass
    
    return jsonify({'text': words,'len': len(images)}), 200

@app.route("/handlefirst",methods=['POST'])
def handleFirstDocument():
    pdf_file = request.files['pdf']
    advoSig = request.files['advocate-sig']
    clieSig = request.files['client-sig']
    keyWords_json = request.form['words']
    keyWords = json.loads(keyWords_json)
    addKeywords = set()
    isPrayerFound = False

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
        images = convert_from_path(ocr_output_path)

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

                if not isPrayerFound and 'PRAYER' in text:
                    isPrayerFound = True

                if is_this_page(text,keyWord):
                    bookMark.append({
                        "page": i+1,
                        "title": keyWord
                    })
                    isPrayerFound = False
                    addKeywords.add(keyWord)
            

            if "FILED THROUGH" in text or 'DEPONENT' in text or 'APPLICANT' in text or 'PETITIONER' in text:
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
                    
                    elif j > len(data['text'])//2 and isPrayerFound and  data['text'][j] == 'PETITIONER' or data['text'][j] == 'DEPONENT':
                        signature.append({
                            'x': data['left'][j] - 5,
                            'y': data['top'][j],
                            'h': data['height'][j],
                            'w': data['width'][j] + 10, 
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
        images = convert_from_path(ocr_output_path)

        img_width, img_height = images[0].size
        signature = []

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
    advoSig = request.files['advocate-sig']

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name
    
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
                    if data["text"][j].strip().lower() in ["pg. no.", "pg.", "page no.", "page"]:
                        x_pg_col = data["left"][j] * scale_x
                        break

            if x_pg_col is None:
                return jsonify({"error": "Could not detect 'Pg. No.' column heading."}), 400

            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=(pdf_width, pdf_height))
            can.setFont("Helvetica", 12)
            filter_data = {"top": data['top'],"text": data['text']}
            titles = index_map.keys()
        
            topMap = extractTopValueFromOCRData(filter_data,titles)
            doneTit = set()
            for key in topMap:
                if key not in doneTit:
                    y_pos = pdf_height - (float(topMap.get(key)) * scale_y)
                    can.drawString(x_pg_col, y_pos, str(index_map[key]))
                    doneTit.add(key)

            if i == len(reader.pages) -1:
                if 'FILE' in data['text'] and 'THROUGH' in data['text']:
                    idx = data['text'].index('FILE')
                    x_sig = float(data['left'][idx] * scale_x) - 5
                    y_sig = pdf_height - float(data['top'][idx]*scale_y) - 2*float(data['height'][idx]*scale_y) - float(100*scale_y)
                    w_sig = data['width'][idx] + data['width'] + 10 
                    can.drawImage(temp_advo_sig_path,x_sig*scale_x,y_sig,w_sig*scale_x,height=40,mask='auto')

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

@app.route("/",methods=['GET'])
def helloRoute():
    return jsonify({"Name":"suzain"})

@app.route("/repair-pdf-diagnostic", methods=['POST'])
def repair_pdf_diagnostic():
    """Diagnostic endpoint to test different PDF repair methods"""
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400
    
    pdf_file = request.files['pdf']
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name
    
    # First, validate the PDF
    validation = validate_pdf(temp_input_path)
    
    diagnostic_results = {
        'validation': validation,
        'original_file_size': os.path.getsize(temp_input_path),
        'repair_methods_tested': [],
        'successful_methods': [],
        'errors': []
    }
    
    # If PDF is already valid, no need to repair
    if validation['is_valid']:
        diagnostic_results['message'] = 'PDF is already valid, no repair needed'
        try:
            os.remove(temp_input_path)
        except:
            pass
        return jsonify(diagnostic_results), 200
    
    # Test different repair methods
    repair_methods = [
        {
            'name': 'qpdf_linearize',
            'function': lambda: subprocess.run(['qpdf', '--linearize', temp_input_path, 'temp_output.pdf'], check=True, capture_output=True)
        },
        {
            'name': 'qpdf_object_streams_disable',
            'function': lambda: subprocess.run(['qpdf', '--object-streams=disable', '--linearize', temp_input_path, 'temp_output.pdf'], check=True, capture_output=True)
        },
        {
            'name': 'qpdf_compress_disable',
            'function': lambda: subprocess.run(['qpdf', '--compress-streams=n', '--linearize', temp_input_path, 'temp_output.pdf'], check=True, capture_output=True)
        },
        {
            'name': 'pypdf_rebuild',
            'function': lambda: rebuild_with_pypdf(temp_input_path, 'temp_output.pdf')
        },
        {
            'name': 'ocrmypdf_repair',
            'function': lambda: ocrmypdf.ocr(temp_input_path, 'temp_output.pdf', skip_text=True, force_ocr=False, skip_big=True)
        }
    ]
    
    for method in repair_methods:
        diagnostic_results['repair_methods_tested'].append(method['name'])
        
        try:
            method['function']()
            
            # Check if output file was created and is valid
            if os.path.exists('temp_output.pdf'):
                try:
                    test_reader = PdfReader('temp_output.pdf')
                    if len(test_reader.pages) > 0:
                        # Validate the repaired PDF
                        repaired_validation = validate_pdf('temp_output.pdf')
                        diagnostic_results['successful_methods'].append({
                            'method': method['name'],
                            'output_size': os.path.getsize('temp_output.pdf'),
                            'pages': len(test_reader.pages),
                            'validation': repaired_validation
                        })
                    os.remove('temp_output.pdf')
                except Exception as e:
                    diagnostic_results['errors'].append(f"{method['name']}: Output file created but invalid - {str(e)}")
                    if os.path.exists('temp_output.pdf'):
                        os.remove('temp_output.pdf')
            else:
                diagnostic_results['errors'].append(f"{method['name']}: No output file created")
                
        except Exception as e:
            diagnostic_results['errors'].append(f"{method['name']}: {str(e)}")
    
    # Clean up
    try:
        os.remove(temp_input_path)
    except:
        pass
    
    return jsonify(diagnostic_results), 200

def rebuild_with_pypdf(input_path, output_path):
    """Helper function to rebuild PDF with pypdf"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    for page in reader.pages:
        writer.add_page(page)
    
    with open(output_path, 'wb') as output_file:
        writer.write(output_file)

def validate_pdf(pdf_path):
    """Validate PDF and identify common issues"""
    validation_result = {
        'is_valid': False,
        'file_size': 0,
        'issues': [],
        'page_count': 0,
        'can_read': False,
        'can_extract_pages': False
    }
    
    try:
        validation_result['file_size'] = os.path.getsize(pdf_path)
        
        # Check if file is too small (likely corrupted)
        if validation_result['file_size'] < 100:
            validation_result['issues'].append('File too small - likely corrupted')
            return validation_result
        
        # Try to read with pypdf
        try:
            reader = PdfReader(pdf_path)
            validation_result['can_read'] = True
            validation_result['page_count'] = len(reader.pages)
            
            if validation_result['page_count'] == 0:
                validation_result['issues'].append('PDF has no pages')
            else:
                validation_result['is_valid'] = True
                
            # Try to extract first page
            try:
                if validation_result['page_count'] > 0:
                    first_page = reader.pages[0]
                    validation_result['can_extract_pages'] = True
            except Exception as e:
                validation_result['issues'].append(f'Cannot extract pages: {str(e)}')
                
        except Exception as e:
            validation_result['issues'].append(f'Cannot read PDF: {str(e)}')
        
        # Check file header
        try:
            with open(pdf_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF'):
                    validation_result['issues'].append('Invalid PDF header')
        except Exception as e:
            validation_result['issues'].append(f'Cannot read file header: {str(e)}')
        
        # Check for EOF marker
        try:
            with open(pdf_path, 'rb') as f:
                f.seek(-1024, 2)  # Go to last 1KB
                end_content = f.read()
                if b'%%EOF' not in end_content:
                    validation_result['issues'].append('Missing EOF marker')
        except Exception as e:
            validation_result['issues'].append(f'Cannot check EOF: {str(e)}')
            
    except Exception as e:
        validation_result['issues'].append(f'General validation error: {str(e)}')
    
    return validation_result

@app.route("/repair-pdf-only", methods=['POST'])
def repair_pdf_only():
    """Simple endpoint to just repair PDF without OCR"""
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400
    
    pdf_file = request.files['pdf']
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
        temp_input.write(pdf_file.read())
        temp_input_path = temp_input.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_repaired:
        temp_repaired_path = temp_repaired.name
    
    # Try to repair the PDF
    repair_success = repair_pdf(temp_input_path, temp_repaired_path)
    
    if not repair_success:
        # If basic repair fails, try advanced repair
        repair_success = repair_pdf_advanced(temp_input_path, temp_repaired_path)
    
    if not repair_success:
        # If all repair methods fail, return error
        try:
            os.remove(temp_input_path)
        except:
            pass
        return jsonify({'error': 'Failed to repair PDF with all available methods'}), 500
    
    # Read the repaired PDF and return as base64
    try:
        with open(temp_repaired_path, 'rb') as f:
            pdf_data = f.read()
        
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        # Clean up
        os.remove(temp_input_path)
        os.remove(temp_repaired_path)
        
        return jsonify({
            'success': True,
            'pdf': pdf_base64,
            'message': 'PDF repaired successfully'
        }), 200
        
    except Exception as e:
        # Clean up
        try:
            os.remove(temp_input_path)
            os.remove(temp_repaired_path)
        except:
            pass
        return jsonify({'error': f'Failed to encode repaired PDF: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(port) if port else 5000)
