from filing_app.utils.helper_function import HelperFunction
from filing_app.view.filling_view import FilingView
from filing_app.service.filing_service import FilingService

class FilingController:
    @staticmethod
    def getParticularsFromIndex(pdf):
        try:
            temp_input_path, ocr_output_path = HelperFunction.makeTempFile(pdf)
            return FilingService.getParticularsFromIndex(input_path=temp_input_path,output_path=ocr_output_path)
        except Exception as error:
            return FilingView.renderError(error)
        
    @staticmethod
    def workOnFirstFile(pdf_file,isOrignal,keyWords,court_type,advoSig=None, clieSig=None):
        try:
            print("hello i am in controller")
            if not isOrignal:
                imgs = [advoSig, clieSig]
                print("hii i am geeting signature")
                temp_input_path,temp_advo_sig_path, temp_clie_sig_path, ocr_output_path = HelperFunction.makeTempFile(pdfs=pdf_file,images=imgs)
                return FilingService.workOnFirstFile(temp_input_path, ocr_output_path, keyWords, court_type, isOrignal, temp_advo_sig_path, temp_clie_sig_path)
            
            temp_input_path, ocr_output_path = HelperFunction.makeTempFile(pdfs=pdf_file)
            print("hii, i am going to service")
            return FilingService.workOnFirstFile(temp_input_path, ocr_output_path, keyWords, court_type, isOrignal)
        except Exception as error:
            return FilingView.renderError(str(error))

    @staticmethod    
    def workOnAnnexures(pdf):
        try:
            temp_input_path, ocr_output_path = HelperFunction.makeTempFile(pdfs=[pdf])
            return FilingService.workOnAnnexures(temp_input_path,ocr_output_path)
        except Exception as error:
            return FilingView.renderError(str(error))
        
    @staticmethod    
    def workOnFinalFile(pdf_file,isOrignal,court_type,advoSig=None,clieSig=None):
        try:
            print("hello i am in controller")
            if not isOrignal:
                print("hello i am not orignal")
                imgs = [advoSig, clieSig]
                temp_input_path,temp_advo_sig_path, temp_clie_sig_path, ocr_output_path = HelperFunction.makeTempFile(pdfs=pdf_file,images=imgs)
                return FilingService.workonFinalFile(temp_input_path,ocr_output_path,isOrignal,court_type,temp_advo_sig_path,temp_clie_sig_path)
            print("hello i am orignal")
            temp_input_path, ocr_output_path = HelperFunction.makeTempFile(pdfs=pdf_file)
            return FilingService.workonFinalFile(temp_input_path,ocr_output_path,isOrignal,court_type)
        except Exception as error:
            print(error)
            return FilingView.renderError(str(error))
        
    @staticmethod    
    def addPageNoInIndex(pdf,isOrignal,index_map,advoSig=None):
        try:
            if not isOrignal:
                imgs = [advoSig]
                temp_input_path,temp_advo_sig_path, _ = HelperFunction.makeTempFile(pdfs=pdf,images=imgs)
                return FilingService.addPageNoInIndex(temp_input_path,isOrignal,index_map,temp_advo_sig_path)
            
            temp_input_path, _ = HelperFunction.makeTempFile(pdfs=pdf)
            return FilingService.addPageNoInIndex(temp_input_path,isOrignal,index_map)
        except Exception as error:
            print(error)
            return FilingView.renderError(str(error))
    
    @staticmethod
    def addBookMarkToWholeFile(pdf_file,bookmark):
        try:
            temp_input_path, _ = HelperFunction.makeTempFile(pdfs=[pdf_file])
            return FilingService.addBookMarkToWholeFile(temp_input_path,bookmark)
        except Exception as error:
            return FilingView.renderError(str(error))
