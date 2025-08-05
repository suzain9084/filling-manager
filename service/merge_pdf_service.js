import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

class MergePDF {
  static async mergeFirstpdf(formdata, imageFile, isOrignal, type) {
    const docCount = Number.parseInt(formdata.get("docCount"));
    const mergeDoc = await PDFDocument.create();
    const MM_TO_PT = 2.83465;
    const trueCopyX = 20 * MM_TO_PT;
    const trueCopyY = 10 * MM_TO_PT;

    let embeddedImage;
    if (imageFile) {
      const imageBuffer = await imageFile.arrayBuffer();
      if (imageFile.type === "image/png") {
        embeddedImage = await mergeDoc.embedPng(imageBuffer);
      } else {
        embeddedImage = await mergeDoc.embedJpg(imageBuffer);
      }
    }

    const imgWidth = 100;
    const imgHeight = 50;

    for (let i = 0; i < docCount; i++) {
      const file = formdata.get(`doc-${i}`);

      const fileBuffer = await file.arrayBuffer();
      const loadedPdf = await PDFDocument.load(fileBuffer,{ignoreEncryption: true});
      const copiedPages = await mergeDoc.copyPages(
        loadedPdf,
        loadedPdf.getPageIndices()
      );

      copiedPages.forEach((page) => {
        if (imageFile && !isOrignal && type === "cat") {
          console.log("inside signature if");
          page.drawImage(embeddedImage, {
            x: trueCopyX + 80,
            y: trueCopyY - 5,
            width: imgWidth,
            height: imgHeight,
          });
        }
        mergeDoc.addPage(page);
      });
    }
    const pdfBytes = await mergeDoc.save();
    return { success: true, pdf: pdfBytes };
  }

  static async mergeAnnexures(formdata, titles, type, imageFile, isOrignal) {
    const docCount = Number.parseInt(formdata.get("docCount"));
    const mergeDoc = await PDFDocument.create();
    const fontSize = 20;
    const font = await mergeDoc.embedFont(StandardFonts.Helvetica);
    let bookmark = [];
    let j = 0;
    let current = 1;
    const MM_TO_PT = 2.83465;
    const trueCopyX = 20 * MM_TO_PT;
    const trueCopyY = 10 * MM_TO_PT;

    let embeddedImage;
    if (imageFile) {
      const imageBuffer = await imageFile.arrayBuffer();
      if (imageFile.type === "image/png") {
        embeddedImage = await mergeDoc.embedPng(imageBuffer);
      } else {
        embeddedImage = await mergeDoc.embedJpg(imageBuffer);
      }
    }

    const imgWidth = 100;
    const imgHeight = 50;

    while (!titles[j].toLowerCase().startsWith("annexure")) {
      j++;
    }

    for (let i = 0; i < docCount; i++) {
      const file = formdata.get(`doc-${i}`);
      const fileBuffer = await file.arrayBuffer();
      const loadedPdf = await PDFDocument.load(fileBuffer,{ignoreEncryption: true});
      const copiedPages = await mergeDoc.copyPages(
        loadedPdf,
        loadedPdf.getPageIndices()
      );
      bookmark.push({ 
        page: current,
        title: titles[j],
      });

      copiedPages.forEach(async (page, pageIndex) => {
        if (pageIndex == 0) {
          const { height } = page.getSize();

          page.drawText(titles[j].split(":")[0], {
            x: 10,
            y: height - 40,
            size: fontSize,
            font,
            color: rgb(0, 0, 0),
          });
        }
        if (pageIndex === copiedPages.length - 1 && type !== "high_court") {
          page.drawText("True copy", {
            x: trueCopyX - 18,
            y: trueCopyY,
            font,
            size: 18,
            color: rgb(0, 0, 0),
          });
        }
        if (imageFile && !isOrignal && type !== "high_court") {
          if (
            (type === "ngt" && pageIndex === copiedPages.length - 1) ||
            type === "cat"
          ) {
            page.drawImage(embeddedImage, {
              x: trueCopyX + 80,
              y: trueCopyY - 5,
              width: imgWidth,
              height: imgHeight,
            });
          }
        }
        mergeDoc.addPage(page);
        current++;
      });
      j++;
    }
    bookmark.push({
      page: current - 1,
      title: "last",
    });
    const pdfBytes = await mergeDoc.save();
    return { success: true, pdf: pdfBytes, bookmark };
  }

  static async mergeLastDoc(formdata, title,imageFile,type,isOrignal) {
    const mergeDoc = await PDFDocument.create();
    let bookmark = [];
    let current = 1;
    const file = formdata.get(`doc-${0}`);

    const MM_TO_PT = 2.83465;
    const trueCopyX = 20 * MM_TO_PT;
    const trueCopyY = 10 * MM_TO_PT;

    let embeddedImage;
    if (imageFile) {
      const imageBuffer = await imageFile.arrayBuffer();
      if (imageFile.type === "image/png") {
        embeddedImage = await mergeDoc.embedPng(imageBuffer);
      } else {
        embeddedImage = await mergeDoc.embedJpg(imageBuffer);
      }
    }

    const imgWidth = 100;
    const imgHeight = 50;

    const fileBuffer = await file.arrayBuffer();
    const loadedPdf = await PDFDocument.load(fileBuffer, {ignoreEncryption: true});
    const copiedPages = await mergeDoc.copyPages(
      loadedPdf,
      loadedPdf.getPageIndices()
    );

    bookmark.push({
      page: current,
      title: title,
    });

    copiedPages.forEach((page) => {
      if (imageFile && !isOrignal && type === "cat") {
        console.log("inside signature if");
        page.drawImage(embeddedImage, {
          x: trueCopyX + 80,
          y: trueCopyY - 5,
          width: imgWidth,
          height: imgHeight,
        });
      }
      mergeDoc.addPage(page);
      current++;
    });

    bookmark.push({
      page: current - 1,
      title: "last",
    });
    const pdfBytes = await mergeDoc.save();
    return { success: true, pdf: pdfBytes, bookmark };
  }
}

export default MergePDF;
