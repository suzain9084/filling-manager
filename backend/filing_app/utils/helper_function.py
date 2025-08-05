import tempfile
import ocrmypdf
import pytesseract
from reportlab.pdfgen import canvas
from pytesseract import Output
from pypdf import PdfReader
from io import BytesIO
from filing_app.view.filling_view import FilingView

class HelperFunction:
    @staticmethod
    def makeTempFile(pdfs = [], images = []):
        print(pdfs,images)
        paths = []
        for pdf in pdfs:
            with tempfile.NamedTemporaryFile(delete=False,suffix='.pdf') as temp_input:
                temp_input.write(pdf.read())
                paths.append(temp_input.name)
    
        for img in images:
            with tempfile.NamedTemporaryFile(delete=False,suffix='.png') as temp_input:
                temp_input.write(img.read())
                paths.append(temp_input.name)

        with tempfile.NamedTemporaryFile(delete=False,suffix='.pdf') as ocr_file:
            paths.append(ocr_file.name)

        return paths
    
    @staticmethod
    def ocrPDF(input_path,output_path,force_ocr,skip_text):
        try:
            ocrmypdf.ocr(
                input_path,
                output_path,
                force_ocr=force_ocr,
                oversample=600,
                optimize=3,
                deskew=True,
                rotate_pages=True,
                language='eng',
                skip_text=skip_text
            )
            return output_path
        except:
            return input_path
    
    @staticmethod
    def getSignatureData(text,i,image,flag,court_type,signature):
        if not flag['isEnclosures'] and 'ENCLOSURES' in text:
            flag['isEnclosures'] = True
                    
        if not flag['isVerification'] and 'VERIFICATION' in text:
            flag['isVerification'] = True
        
        if not flag['isPrayer'] and 'PRAYER' in text:
            flag['isPrayer'] = True

        isHighCourt = court_type == "high_court"
        isNGT = court_type == "ngt"
        isCAT = court_type == "cat"

        if ("FILED THROUGH" in text) or ('APPLICANT' in text and (isNGT or isCAT)) or ('PETITIONER' in text and isHighCourt):
            data = pytesseract.image_to_data(image, output_type=Output.DICT)
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
                        
                elif (data['text'][j] == 'APPLICANT' or data['text'][j] == 'PETITIONER'):
                    if (isNGT or isCAT) and (flag['isVerification'] or flag['isEnclosures']) or(isHighCourt and flag['isPrayer']):
                        signature.append({
                            'x': data['left'][j] - 5,
                            'y': data['top'][j],
                            'h': data['height'][j],
                            'w': data['width'][j] + 10,
                            'page': i + 1,
                            'type': "client"
                        })

    @staticmethod
    def is_this_page(text, keyword):
        words = keyword.upper().split(" ")
        text = HelperFunction.get_top_lines(text,30)
        n = 0
        mismatch = 0
        length = len(words)
        for i, word in enumerate(words):
            if i + 1 < length and (words[i] == 'ALONG' and words[i + 1] == 'WITH'):
                break
            if word.upper() not in text:
                mismatch += 1
            n += 1
        return mismatch / n <= 0.4
    
    @staticmethod
    def get_top_lines(text, num_lines=5):
        lines = text.split('\n')
        return "\n".join(lines[:num_lines])
    
    @staticmethod
    def putSignatureAtplace(signature,i,page,img_width,img_height,temp_advo_sig_path,temp_clie_sig_path):
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

    @staticmethod
    def get_x_of_page_label(data, scale_x):
        page_keywords = [
            "pg", "pg.", "pg no", "pg. no", "pg. no.", "pg no.", "pg.no",
            "pgno", "page", "page no", "page no.", "page number", "pageno", "page.no"
        ]
        
        for j in range(len(data["text"])):
            word = data["text"][j].strip().lower()
            if word in page_keywords:
                return data["left"][j] * scale_x
        
        return None
    
    @staticmethod
    def extractTopValueFromOCRData(filter_data, titles, done, stop_words):
        topMap = {}

        data_text = filter_data['text']
        data_top = filter_data['top']
        visited = set()

        for title in titles:
            words = title.split(" ")
            topvalue = 0
            n = 0
            misMatch = 0

            if title in done:
                continue

            for word in words:
                if word.lower() not in stop_words and word not in visited and word in data_text:
                    try:
                        idx = data_text.index(word)
                        topvalue += data_top[idx]
                        n += 1
                        visited.add(word)
                    except ValueError:
                        continue 
                if word.lower() not in stop_words and word not in visited and word not in data_text:
                    misMatch += 1
                
            if n > 0 and n /(n + misMatch) > 0.4:
                topMap[title] = topvalue / n

        return topMap
    @staticmethod
    def putPageNumberInIndex(topMap,doneTit,pdf_height,scale_y,index_map,x_pg_col,can):
        for key in topMap:
            if key not in doneTit:
                y_pos = pdf_height - (float(topMap.get(key)) * scale_y)
                can.drawString(x_pg_col, y_pos, str(index_map[key]))
                doneTit.add(key)
    @staticmethod
    def getSigPositionAndPutThemInIndex(data,pdf_height,can,temp_advo_sig_path,scale_x,scale_y):
        if 'FILED' in data['text'] and 'THROUGH' in data['text']:
            idx = data['text'].index('FILED')
            x_sig = float((data['left'][idx] - 5) * scale_x)
            y_sig = pdf_height - float(data['top'][idx]*scale_y) - 2*float(data['height'][idx]*scale_y) - float(100*scale_y)
            w_sig = data['width'][idx] + data['width'][idx + 1] + 10 
            can.drawImage(temp_advo_sig_path,x_sig,y_sig,w_sig*scale_x,height=40,mask='auto')

    @staticmethod
    def makeBookMarkData(keyWords,addKeywords,text,bookMark,i,flag):
        for keyWord in keyWords:
            if keyWord in addKeywords:
                continue
                    
            if HelperFunction.is_this_page(text,keyWord):
                bookMark.append({
                    "page": i+1,
                    "title": keyWord
                })
                flag['isVerification'] = False
                flag['isEnclosures'] = False
                flag['isPrayer'] = False
                addKeywords.add(keyWord)