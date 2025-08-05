from flask import jsonify, send_file
from io import BytesIO
import base64

class FilingView:
    @staticmethod
    def renderError(message):
        return jsonify({"error": message }), 500
    
    @staticmethod
    def renderParticulars(words,doc):
        return jsonify({'text': words, 'len': len(doc)}), 200
    
    @staticmethod
    def renderFileAlongWithJson(writer, bookMark, reader):
        try:
            output_stream = BytesIO()
            writer.write(output_stream)
            output_stream.seek(0)

            bookMark.append({
                "page": len(reader.pages),
                "title": "last"
            })

            pdf_base64 = base64.b64encode(output_stream.getvalue()).decode('utf-8')
            return jsonify({"pdf": pdf_base64, "bookmarks": bookMark}), 200
        except Exception as error:
            print(error)
            return FilingView.renderError(str(error)), 500
    
    @staticmethod
    def renderPDFFile(writer):
        try:
            output_stream = BytesIO()
            writer.write(output_stream)
            output_stream.seek(0)
            return send_file(output_stream,mimetype="application/pdf",download_name="process_pdf.pdf",as_attachment=True), 200
        except Exception as error:
            return FilingView.renderError(str(error)), 500
