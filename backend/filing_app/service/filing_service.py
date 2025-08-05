from filing_app.utils.helper_function import HelperFunction
from filing_app.utils.gemini_api import GeminiAPI
from filing_app.view.filling_view import FilingView
import fitz
from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter
import pytesseract
from pytesseract import Output
from io import BytesIO
from reportlab.pdfgen import canvas
from nltk.corpus import stopwords
import nltk
nltk.download('stopwords')

class FilingService:
    
    @staticmethod
    def getParticularsFromIndex(input_path,output_path):
        try:
            output_path = HelperFunction.ocrPDF(input_path,output_path,force_ocr=True,skip_text=False)
            doc = fitz.open(output_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text()

            words = GeminiAPI.extract_particulars(full_text)
            return FilingView.renderParticulars(words,doc)
        except Exception as error:
            return FilingView.renderError(error)

    @staticmethod
    def workOnFirstFile(temp_input_path, ocr_output_path, keyWords, court_type, isOrignal, temp_advo_sig_path=None, temp_clie_sig_path=None):
        try:
            ocr_output_path = HelperFunction.ocrPDF(temp_input_path,ocr_output_path,force_ocr=True,skip_text=False)
            addKeywords = set()
            flag = {}
            flag['isEnclosures'] = False
            flag['isVerification'] = False
            flag['isPrayer'] = False

            reader = PdfReader(ocr_output_path)
            writer = PdfWriter()
            images = convert_from_path(ocr_output_path)

            img_width, img_height = images[0].size
            bookMark = []
            signature = []

            for i, page in enumerate(reader.pages):
                text = pytesseract.image_to_string(images[i])

                if not isOrignal:
                    HelperFunction.getSignatureData(text,i,images[i],flag,court_type,signature)    
                HelperFunction.makeBookMarkData(keyWords,addKeywords,text,bookMark,i,flag)

            for i, page in enumerate(reader.pages):
                if not isOrignal:
                    HelperFunction.putSignatureAtplace(signature,i,page,img_width,img_height,temp_advo_sig_path,temp_clie_sig_path)
                writer.add_page(page)

            return FilingView.renderFileAlongWithJson(writer,bookMark,reader)
        except Exception as error:
            print(error)
            return FilingView.renderError(str(error))

    @staticmethod
    def workOnAnnexures(temp_input_path,ocr_output_path):
        try:
            ocr_output_path = HelperFunction.ocrPDF(temp_input_path,ocr_output_path,force_ocr=False,skip_text=True)
            reader = PdfReader(ocr_output_path)
            writer = PdfWriter()

            for _,page in enumerate(reader.pages):
                writer.add_page(page)

            return FilingView.renderPDFFile(writer=writer)
        except Exception as error:
            return FilingView.renderError(str(error))
        
    @staticmethod    
    def workonFinalFile(temp_input_path,ocr_output_path,isOrignal,court_type,temp_advo_sig_path=None,temp_clie_sig_path=None):
        try:
            ocr_output_path = HelperFunction.ocrPDF(temp_input_path,ocr_output_path,force_ocr=False,skip_text=True)
            reader = PdfReader(ocr_output_path)
            writer = PdfWriter()
            images = convert_from_path(ocr_output_path)

            img_width, img_height = images[0].size
            signature = []
            flag={}
            flag['isEnclosures'] = False
            flag['isVerification'] = False
            flag['isPrayer'] = False

            if not isOrignal:
                for i, page in enumerate(reader.pages):
                    text = pytesseract.image_to_string(images[i])
                    HelperFunction.getSignatureData(text,i,images[i],flag,court_type,signature)

            for i, page in enumerate(reader.pages):
                if not isOrignal:
                    HelperFunction.putSignatureAtplace(signature,i,page,img_width,img_height,temp_advo_sig_path,temp_clie_sig_path)
                writer.add_page(page)

            return FilingView.renderPDFFile(writer=writer)
        except Exception as error:
            return FilingView.renderError(str(error))
        
    @staticmethod    
    def addPageNoInIndex(temp_input_path,isOrignal,index_map,temp_advo_sig_path=None):
        try:
            reader = PdfReader(temp_input_path)
            writer = PdfWriter()
            images = convert_from_path(temp_input_path)
            doneTit = set()
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
                    x_pg_col = HelperFunction.get_x_of_page_label(data,scale_x)

                if x_pg_col is None:
                    return FilingView.renderError("Could not detect 'Pg. No.' column heading.")

                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=(pdf_width, pdf_height))
                can.setFont("Helvetica", 12)
                filter_data = {"top": data['top'],"text": data['text']}
                titles = index_map.keys()
                
                stop_words = set(stopwords.words('english'))
                topMap = HelperFunction.extractTopValueFromOCRData(filter_data,titles,doneTit, stop_words)
                HelperFunction.putPageNumberInIndex(topMap,doneTit,pdf_height,scale_y,index_map,x_pg_col,can)

                if not isOrignal and (i == len(reader.pages) -1 or i == len(reader.pages) - 2):
                    HelperFunction.getSigPositionAndPutThemInIndex(data,pdf_height,can,temp_advo_sig_path,scale_x,scale_y)

                can.save()
                packet.seek(0)
                overlay_pdf = PdfReader(packet)
                if overlay_pdf.pages:
                    page.merge_page(overlay_pdf.pages[0])
                writer.add_page(page)
            return FilingView.renderPDFFile(writer=writer)
        except Exception as error:
            print(error)
            return FilingView.renderError(str(error))

    @staticmethod        
    def addBookMarkToWholeFile(temp_input_path,bookmark):
        try:
            reader = PdfReader(temp_input_path)
            writer = PdfWriter()

            for page_number, page in enumerate(reader.pages):
                writer.add_page(page)

            for page_str, title in bookmark.items():
                try:
                    page_number = int(page_str)
                    writer.add_outline_item(title, page_number - 1)
                except ValueError:
                    continue
            return FilingView.renderPDFFile(writer=writer)
        except Exception as error:
            return FilingView.renderError(str(error))