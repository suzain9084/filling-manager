from flask import Blueprint, request
from filing_app.view.filling_view import FilingView
from filing_app.controller.filing_controller import FilingController
import json

filing_routes_bp = Blueprint("filing_routes_bp", __name__)

@filing_routes_bp.route("/api/extract-particulars",methods=['POST'])
def getParticularsFromIndex():
    try: 
        index = request.files['index']
        return FilingController.getParticularsFromIndex(pdf=[index])
    except Exception as error:
        print(error)
        return FilingView.renderError(str(error))

@filing_routes_bp.route("/api/work-on-first-file", methods=['POST'])
def workOnFirstFile():
    try:
        pdf_file = request.files['pdf']
        print(pdf_file)
        print("Incoming request received.") 
        print("Request.files keys:", list(request.files.keys()))
        print("Request.form keys:", list(request.form.keys()))

        isOrignal = request.form['isOrignal'].lower() == "true"
        keyWords_json = request.form['words']
        keyWords = json.loads(keyWords_json)
        court_type = request.form['type']

        if not isOrignal:
            advoSig = request.files['advocate-sig']
            clieSig = request.files['client-sig']
            return FilingController.workOnFirstFile([pdf_file],isOrignal,keyWords,court_type,advoSig, clieSig)
        
        return FilingController.workOnFirstFile([pdf_file],isOrignal,keyWords,court_type)
    
    except Exception as error:
        return FilingView.renderError(str(error)), 400


@filing_routes_bp.route("/api/wotk-on-annexures", methods=['POST'])
def workOnAnnexures():
    try:
        pdf_file = request.files['pdf']
        return FilingController.workOnAnnexures(pdf=pdf_file)
    except Exception as error:
        return FilingView.renderError(str(error)), 400
    
@filing_routes_bp.route("/api/work-on-final-file",methods=['POST'])
def workOnFinalFile():
    try:
        print("hello i am there")
        pdf_file = request.files['pdf']
        isOrignal = request.form['isOrignal']
        court_type = request.form['type']
        print("")
        if not isOrignal:
            print("i am getting signature")
            advoSig = request.files['advocate-sig']
            clieSig = request.files['client-sig']
            return FilingController.workOnFinalFile([pdf_file],isOrignal,court_type,advoSig,clieSig)
        
        return FilingController.workOnFinalFile([pdf_file],isOrignal,court_type)
    except Exception as error:
        print(error)
        return FilingView.renderError(str(error))

@filing_routes_bp.route("/api/add-page-no-in-index", methods=['POST'])
def addPageNoInIndex():
    try:
        pdf_file = request.files["pdf"]
        isOrignal = request.form['isOrignal'].lower() == "true"
        index_map = json.loads(request.form["index_map"])
        if not isOrignal:
            advoSig = request.files['advocate-sig']
            return FilingController.addPageNoInIndex([pdf_file],isOrignal,index_map,advoSig)
    
        return FilingController.addPageNoInIndex([pdf_file],isOrignal,index_map)
    except Exception as error:
        print(error)
        return FilingView.renderError(str(error))
    
@filing_routes_bp.route("/api/add-book-mark", methods=['POST'])
def addBookMarkToWholeFile():
    try:
        pdf_file = request.files["pdf"]
        bookmark = json.loads(request.form["bookmark"])
        return FilingController.addBookMarkToWholeFile(pdf_file,bookmark)
    except Exception as error:
            return FilingView.renderError(str(error))