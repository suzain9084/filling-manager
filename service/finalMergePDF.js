import { PDFDocument, StandardFonts, rgb } from 'pdf-lib'

class AddpageNumberService {
    static async addPageNoTitle(blobList) {
        const mergeDoc = await PDFDocument.create()
        let currPage = 1
        const fontSize = 20
        const font = await mergeDoc.embedFont(StandardFonts.Helvetica)

        for (let i = 0; i < blobList.length; i++) {
            const fileBuffer = await blobList[i].arrayBuffer()
            const loadedPdf = await PDFDocument.load(fileBuffer)
            const copiedPages = await mergeDoc.copyPages(loadedPdf, loadedPdf.getPageIndices())

            if (i === 0) {
                copiedPages.forEach((page) => {
                    mergeDoc.addPage(page)
                })
            } else {
                copiedPages.forEach((page) => {
                    const { width, height } = page.getSize()
                    page.text
                    page.drawText(`${currPage}`, {
                        x: width - 40,
                        y: height - 30,
                        size: fontSize,
                        font,
                        color: rgb(0, 0, 0),
                    })

                    mergeDoc.addPage(page)
                    currPage += 1
                })
            }
        };

        const pdfBytes = await mergeDoc.save()
        return { success: true, pdf: pdfBytes }
    }
}

export default AddpageNumberService