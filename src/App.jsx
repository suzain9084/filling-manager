import React, { useState, useRef } from 'react'
import './App.css'
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import DocumentScannerIcon from '@mui/icons-material/DocumentScanner';
import MergePDF from '../service/merge_pdf_service';
import AddpageNumberService from '../service/finalMergePDF';


function App() {
  const [index, setindex] = useState([])
  const [firstfiles, setfirstFiles] = useState([]);
  const [annexurefiles, setannexureFiles] = useState([]);
  const [application, setapplication] = useState([])
  const [vakalatnamafiles, setvakalatnamaFiles] = useState([]);
  const [proofService, setproofService] = useState([])
  const [courtFee, setcourtFee] = useState([])
  
  const [advocateSig, setadvocateSig] = useState(null)
  const [clientSig, setclientSig] = useState(null)
  const currSection = useRef(-1)
  
  const IndexLen = useRef(0)
  const particulars = useRef([])
  const bookMarks = useRef([])
  const indexMap = useRef({})

  const blobArrayRef = useRef([])

  const base64ToBlob = (base64, mimeType = 'application/pdf') => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);

    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }

    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  }

  const makeBookMarkForWholeDocument = () => {
    let currPageInc = 0
    let bookmark = {}
    let index_map = {}
    bookmark['1'] = 'Index'
    for (let i = 0; i < bookMarks.current.length; i++) {
      for (let j = 0; j < bookMarks.current[i].length; j++) {
        if (bookMarks.current[i][j]['title'] == "last") {
          currPageInc += bookMarks.current[i][j]['page']
        } else {
          const page = bookMarks.current[i][j]['page']
          const title = bookMarks.current[i][j]['title']
          bookmark[page + currPageInc + IndexLen.current] = title
          index_map[title] = page + currPageInc
        }
      }
    }
    bookMarks.current = bookmark
    indexMap.current = index_map
    console.log(bookmark)
    console.log(index_map)
  }

  const handleFileChange = (event) => {
    const newFiles = Array.from(event.target.files).map((file) => ({
      file,
      title: file.name.replace('.pdf', ''),
    }));
    if (currSection.current == 0) {
      setindex(newFiles)
    } else if (currSection.current == 1) {
      setfirstFiles((prev) => [...prev, ...newFiles]);
    } else if (currSection.current == 2) {
      setannexureFiles((prev) => [...prev, ...newFiles])
    } else if (currSection.current == 3) {
      setapplication((prev) => [...prev, ...newFiles])
    } else if (currSection.current == 4) {
      setvakalatnamaFiles((prev) => [...prev, ...newFiles])
    } else if (currSection.current == 5) {
      setproofService((prev) => [...prev, ...newFiles])
    } else {
      setcourtFee((prev) => [...prev, ...newFiles])
    }
  };


  const handleDelete = (index, section) => {
    if (section == 0) {
      setindex([])
    } else if (section == 1) {
      const updatedFiles = firstfiles.filter((_, i) => i !== index);
      setfirstFiles(updatedFiles);
    } else if (section == 2) {
      const updatedFiles = annexurefiles.filter((_, i) => i !== index);
      setannexureFiles(updatedFiles);
    } else if (section == 3) {
      const updatedFiles = application.filter((_, i) => i !== index);
      setapplication(updatedFiles);
    } else if (section == 4) {
      const updatedFiles = vakalatnamafiles.filter((_, i) => i !== index);
      setvakalatnamaFiles(updatedFiles)
    } else if (section == 5) {
      const updatedFiles = proofService.filter((_, i) => i !== index);
      setproofService(updatedFiles)
    } else {
      const updatedFiles = courtFee.filter((_, i) => i !== index);
      setcourtFee(updatedFiles)
    }
  };

  const handleSignature = (e, i) => {
    if (i == 0) {
      setadvocateSig(e.target.files[0])
    } else {
      setclientSig(e.target.files[0])
    }
  }

  const getFormData = (files) => {
    let formdata = new FormData()
    files.forEach((e, i) => {
      formdata.append(`doc-${i}`, e.file)
      formdata.append(`title-${i}`, e.title)
    })
    formdata.append("docCount", files.length)
    return formdata
  }

  const getTitlesFromIndex = async () => {
    let formdata = new FormData()
    formdata.append('index', index[0].file)
    let res = await fetch("http://127.0.0.1:5000/handleIndex", {
      method: 'POST',
      body: formdata
    })
    if (res.ok) {
      let list = await res.json()
      particulars.current = Array.from(list['text'])
      IndexLen.current = list['len']
      console.log("Done with Title")
    }
    return res.ok
  }

  const workonfirstSection = async (files) => {
    if (!advocateSig || !clientSig) {
      alert("Please upload both signatures before submitting.");
      return;
    }
    let formdata = getFormData(files)
    let response = await MergePDF.mergeFirstpdf(formdata)
    if (response.success) {
      let form = new FormData()
      form.append("pdf", new Blob([response.pdf], { type: "application/pdf" }));
      form.append("advocate-sig", advocateSig)
      form.append('client-sig', clientSig)
      form.append("words", JSON.stringify(particulars.current))
      let res = await fetch("http://127.0.0.1:5000/handlefirst", {
        method: 'POST',
        body: form
      })

      if (res.ok) {
        let data = await res.json()
        const updated = [...blobArrayRef.current, base64ToBlob(data.pdf)]
        blobArrayRef.current = updated
        let copyBookMarks = [...bookMarks.current, data.bookmarks]
        bookMarks.current = copyBookMarks
        console.log("Done with first pdf")
      }
    }
  }

  const handleAnnexures = async () => {
    let formdata = getFormData(annexurefiles)
    let response = await MergePDF.mergeAnnexures(formdata, particulars.current)
    if (response.success) {
      let form = new FormData()
      form.append("pdf", new Blob([response.pdf], { type: "application/pdf" }));
      form.append("bookmark", JSON.stringify(response.bookmark))

      let res = await fetch("http://127.0.0.1:5000/handleAnnexure", {
        method: 'POST',
        body: form
      })
      if (res.ok) {
        let data = await res.blob()
        let copyBookMarks = [...bookMarks.current, response.bookmark]
        bookMarks.current = copyBookMarks
        const updated = [...blobArrayRef.current, data]
        blobArrayRef.current = updated
        console.log("Done with Annexure")
      }
    }
  }

  const handleFinalFiles = async (files,title) => {
    console.log(files)
    let formdata = getFormData(files)
    let response = await MergePDF.mergeLastDoc(formdata, title)
    if (response.success) {
      let form = new FormData()
      form.append("pdf", new Blob([response.pdf], { type: "application/pdf" }));
      form.append("advocate-sig", advocateSig)
      form.append('client-sig', clientSig)
      let res = await fetch("http://127.0.0.1:5000/handleFinal", {
        method: 'POST',
        body: form
      })
      if (res.ok) {
        let data = await res.blob()
        blobArrayRef.current = [...blobArrayRef.current,data]
        let copyBookMarks = [...bookMarks.current, response.bookmark]
        bookMarks.current = copyBookMarks
        console.log("Done with last Doc");
      }
    }
  }

  // const makeParallelProcessing = async () => {
  //   await workonfirstSection()
  //   await handleAnnexures()
  //   await handleFinalFiles()
  // }

  const addPageNumberInIndex = async () => {
    let formdata = new FormData()
    formdata.append("pdf", index[0].file)
    formdata.append("index_map", JSON.stringify(indexMap.current))
    formdata.append('advocate-sig',advocateSig)
    let res = await fetch("http://127.0.0.1:5000/handleFinalIndexPDF", {
      method: 'POST',
      body: formdata
    })
    if (res.ok) {
      console.log("done with index page no")
      const data = await res.blob()
      blobArrayRef.current = [data, ...blobArrayRef.current]
    }
  }

  const handleSubmitFile = async () => {
    let res = await getTitlesFromIndex()
    if (res) {
      let temp = []
      let i = 0
      while (i < particulars.current.length && particulars.current[i].toLowerCase().search(/annexure/) === -1) {
        if (particulars.current[i].toLowerCase().search(/court fee/) !== -1) {
          if (temp.length !== 0) {
            await workonfirstSection(temp)
          }
          await handleFinalFiles(courtFee,particulars.current[i])
          temp = []
        } else if (particulars.current[i].toLowerCase().search(/application under/) !== -1){
            await handleFinalFiles(application,particulars.current[i])
        } else {
          if ( i < firstfiles.length){
            temp.push(firstfiles[i])
          }
        }
        i++;
      }
      if (temp.length != 0) {
        await workonfirstSection(temp)
      }
      await handleAnnexures()
      i = particulars.current.length - 1
      while (i >= 0 && particulars.current[i].toLowerCase().search(/annexure/) === -1){
        i--;
      }
      while (i < particulars.current.length){
        if (particulars.current[i].toLowerCase().search(/application under/) !== -1) {
          await handleFinalFiles(application,particulars.current[i])
        } else if (particulars.current[i].toLowerCase().search(/vakalatnama/) !== -1){
          await handleFinalFiles(vakalatnamafiles,particulars.current[i])
        } else if (particulars.current[i].toLowerCase().search(/proof of service/) !== -1){
          await handleFinalFiles(proofService,particulars.current[i])
        }
        i++;
      }
      makeBookMarkForWholeDocument()
      await addPageNumberInIndex()
      console.log(blobArrayRef.current)
      let response = await AddpageNumberService.addPageNoTitle(blobArrayRef.current)
      if (response.success) {
        let formdata = new FormData()
        formdata.append("pdf", new Blob([response.pdf], { type: 'application/pdf' }))
        formdata.append("bookmark", JSON.stringify(bookMarks.current))
        let res = await fetch("http://127.0.0.1:5000/addBookMarks", {
          method: 'POST',
          body: formdata
        })
        if (res.ok) {
          const blob = await res.blob()
          const blobUrl = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = blobUrl;
          a.download = "merged.pdf";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(blobUrl);
        }
      }
    }
  }

  return (
    <div className="pdf-container">
      <h1 className="title">PDF Annexure Manager</h1>
      <p className="subtitle">
        Upload multiple PDF files, add titles, and generate a merged PDF with bookmarks and OCR.
      </p>

      <div>
        <input type="file" accept="application/pdf" multiple hidden onChange={handleFileChange} />
      </div>

      <div className="uploaded-section">
        <h2>Upload Index</h2>
        {index.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 0)}><DeleteForeverIcon /></div>
          </div>
        ))}
        {index.length == 0 && <div className="actions">
          <button className="add-more-btn" onClick={() => { currSection.current = 0; document.querySelector('input[type="file"]').click() }} >
            + Add Index
          </button>
        </div>}
      </div>

      <div className="uploaded-section">
        <h2>Upload First Files</h2>
        {firstfiles.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 1)}><DeleteForeverIcon /></div>
          </div>
        ))}
        <div className="actions">
          <button className="add-more-btn" onClick={() => { currSection.current = 1; document.querySelector('input[type="file"]').click() }} >
            + Add More Files
          </button>
        </div>
      </div>




      <div className="uploaded-section">
        <h2>Upload Annexure Files</h2>
        {annexurefiles.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 2)}><DeleteForeverIcon /></div>
          </div>
        ))}
        <div className="actions">
          <button className="add-more-btn" onClick={() => { currSection.current = 2; document.querySelector('input[type="file"]').click() }}>
            + Add More Files
          </button>
        </div>
      </div>



      <div className="uploaded-section">
        <h2>Upload Application</h2>
        {application.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 3)}><DeleteForeverIcon /></div>
          </div>
        ))}
        {application.length == 0 && <div className="actions">
          <button className="add-more-btn" onClick={() => { currSection.current = 3; document.querySelector('input[type="file"]').click() }}>
            + Add Applcation
          </button>
        </div>}
      </div>



      <div className="uploaded-section">
        <h2>Uploaded vakalatnama</h2>
        {vakalatnamafiles.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 4)}><DeleteForeverIcon /></div>
          </div>
        ))}
        <div className="actions">
          {vakalatnamafiles.length == 0 && <button className="add-more-btn" onClick={() => { currSection.current = 4; document.querySelector('input[type="file"]').click() }}>
            + Add More Files
          </button>}
        </div>
      </div>

      <div className="uploaded-section">
        <h2>Uploaded Proof of Service</h2>
        {proofService.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 5)}><DeleteForeverIcon /></div>
          </div>
        ))}
        <div className="actions">
          {proofService.length == 0 && <button className="add-more-btn" onClick={() => { currSection.current = 5; document.querySelector('input[type="file"]').click() }} >
            + Add More Files
          </button>}
        </div>
      </div>

      <div className="uploaded-section">
        <h2>Uploaded Court Fee Receipt</h2>
        {courtFee.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 6)}><DeleteForeverIcon /></div>
          </div>
        ))}
        <div className="actions">
          {courtFee.length == 0 && <button className="add-more-btn" onClick={() => { currSection.current = 6; document.querySelector('input[type="file"]').click() }}>
            + Add More Files
          </button>}
        </div>
      </div>



      <div className="uploaded-section">
        <h2>Uploaded Signature</h2>
        <div className="signature-upload-wrapper">
          <div className="signature-block">
            <p>Upload Advocate Signature</p>
            <input type="file" id="advocate" accept='png jpg' className="signature-input" file={advocateSig || ''} onChange={(e) => { handleSignature(e, 0) }} />
          </div>
          <div className="signature-block">
            <p>Upload Client Signature</p>
            <input type="file" id="client" accept='png jpg' className="signature-input" file={clientSig || ''} onChange={(e) => { handleSignature(e, 1) }} />
          </div>
        </div>
      </div>

      <div className="actions">
        <button className="generate-btn" onClick={handleSubmitFile}>
          Generate Final PDF
        </button>
      </div>

      <footer className="footer">© 2025 PDF Annexure Manager. All rights reserved.</footer>
      {/* {submitting && (
        <div className='loader-cont'>
          <div>
            <CircularProgress
              variant="indeterminate"
              disableShrink
              sx={(theme) => ({
                color: '#1a90ff',
                animationDuration: '550ms',
                position: 'absolute',
                left: 0,
                [`& .${circularProgressClasses.circle}`]: {
                  strokeLinecap: 'round',
                },
                ...theme.applyStyles('dark', {
                  color: '#308fe8',
                }),
              })}
              size={40}
              thickness={4}
            />
          </div>
        </div>
      )} */}
    </div>
  )
}

export default App
