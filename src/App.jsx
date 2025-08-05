import React, { useState, useRef } from 'react'
import './App.css'
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import DocumentScannerIcon from '@mui/icons-material/DocumentScanner';
import MergePDF from '../service/merge_pdf_service';
import AddpageNumberService from '../service/finalMergePDF';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { FileText } from 'lucide-react';


function App() {
  const [index, setindex] = useState([])
  const [firstfiles, setfirstFiles] = useState([]);
  const [annexurefiles, setannexureFiles] = useState([]);
  const [application, setapplication] = useState([])
  const [vakalatnamafiles, setvakalatnamaFiles] = useState([]);
  const [proofService, setproofService] = useState([])
  const [courtFee, setcourtFee] = useState([])
  const [authLeter, setAuthLetter] = useState([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [currStep, setCurrStep] = useState([])
  
  const [advocateSig, setadvocateSig] = useState(null)
  const [clientSig, setclientSig] = useState(null)
  const currSection = useRef(-1)
  
  const IndexLen = useRef(0)
  const particulars = useRef([])
  const bookMarks = useRef([])
  const indexMap = useRef({})
  const typeRef = useRef(null)

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
          let next = bookMarks.current[i][j+1]['page']
          const page = bookMarks.current[i][j]['page']
          if ( bookMarks.current[i][j+1]['title'] !== "last") {
            next -= 1;
          }
          const title = bookMarks.current[i][j]['title']
          bookmark[page + currPageInc + IndexLen.current] = title
          index_map[title] = `${page + currPageInc} - ${currPageInc + next}`
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
      range: "",
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
    } else if (currSection.current == 6) {
      setcourtFee((prev) => [...prev, ...newFiles])
    } else {
      setAuthLetter((prev) => [...prev, ...newFiles])
    }
  };

  const handleRangeChange = (section, fileIndex, e) => {
    const value = e.target.value;

    const pattern = /^\d{1,4}-\d{1,4}$/;
    if (value !== "" && !pattern.test(value)) return;

    if (section === 1) {
      const updated = [...firstfiles];
      updated[fileIndex].range = value;
      setfirstFiles(updated);
    } else if (section === 3) {
      const updated = [...application];
      updated[fileIndex].range = value;
      setapplication(updated);
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
    } else if(section == 6) {
      const updatedFiles = courtFee.filter((_, i) => i !== index);
      setcourtFee(updatedFiles)
    } else {
      const updatedFiles = authLeter.filter((_, i) => i !== index);
      setAuthLetter(updatedFiles)
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
    if (index.length === 0) {
      alert("you have not uploaded first file");
      return
    }
    let formdata = new FormData()
    formdata.append('index', index[0].file)
    let res = await fetch("http://127.0.0.1:5000/api/extract-particulars", {
      method: 'POST',
      body: formdata
    })
    if (res.ok) {
      let list = await res.json()
      console.log(list)
      particulars.current = Array.from(list['text'])
      IndexLen.current = list['len']
      console.log("Done with Title")
    }
    return res.ok
  }

  const workonfirstSection = async (files,titles) => {
    let formdata = getFormData(files)
    let isOrignal = false
    if (!advocateSig && !clientSig) {
      isOrignal = true
    }
    let response = await MergePDF.mergeFirstpdf(formdata,advocateSig,isOrignal,typeRef.current.value)
    if (response.success) {
      let form = new FormData()
      form.append("pdf", new Blob([response.pdf], { type: "application/pdf" }));
      form.append('type',typeRef.current.value)
      if (advocateSig && clientSig) {
        form.append("advocate-sig", advocateSig)
        form.append('client-sig', clientSig)
        form.append('isOrignal', "false")
      } else {
        form.append('isOrignal', "true")
      }
      console.log("title: ",titles)
      form.append("words", JSON.stringify(titles))
      let res = await fetch("http://127.0.0.1:5000/api/work-on-first-file", {
        method: 'POST',
        body: form
      })

      if (res.ok) {
        let data = await res.json()
        console.log(data)
        const updated = [...blobArrayRef.current, base64ToBlob(data.pdf)]
        blobArrayRef.current = updated
        console.log(updated)
        let copyBookMarks = [...bookMarks.current, data.bookmarks]
        bookMarks.current = copyBookMarks
        console.log("Done with first pdf")
      } else{
        console.log(await res.json())
      }
    }
  }

  const handleAnnexures = async () => {
    let formdata = getFormData(annexurefiles)
    if (Number.parseInt(formdata.get('docCount')) === 0) {
      alert("upload Annexure files");
      return
    }
    let isOrignal = true
    if (advocateSig) {
      isOrignal = false
    }
    console.log(typeRef.current.value, advocateSig,isOrignal)
    let response = await MergePDF.mergeAnnexures(formdata, particulars.current,typeRef.current.value, advocateSig,isOrignal)
    if (response.success) {
      let form = new FormData()
      form.append("pdf", new Blob([response.pdf], { type: "application/pdf" }));
      form.append("bookmark", JSON.stringify(response.bookmark))

      let res = await fetch("http://127.0.0.1:5000/api/wotk-on-annexures", {
        method: 'POST',
        body: form
      })
      if (res.ok) {
        let data = await res.blob()
        console.log(data)
        let copyBookMarks = [...bookMarks.current, response.bookmark]
        bookMarks.current = copyBookMarks
        const updated = [...blobArrayRef.current, data]
        blobArrayRef.current = updated
        console.log("Done with Annexure")
      }
    }
  }

  const handleFinalFiles = async (files,title) => {
    if (files.length === 0) {
      alert(`You have not upload ${title} file`)
      return
    }
    let formdata = getFormData(files)
    let isOrignal = false
    if (!advocateSig && !clientSig) {
      isOrignal = true
    }
    let response = await MergePDF.mergeLastDoc(formdata, title,advocateSig,typeRef.current.value,isOrignal)
    if (response.success) {
      let form = new FormData()
      form.append("pdf", new Blob([response.pdf], { type: "application/pdf" }));
      let res = await fetch("http://127.0.0.1:5000/api/wotk-on-annexures", {
        method: 'POST',
        body: form
      })
      if (res.ok) {
        let data = await res.blob()
        console.log(data)
        blobArrayRef.current = [...blobArrayRef.current,data]
        let copyBookMarks = [...bookMarks.current, response.bookmark]
        bookMarks.current = copyBookMarks
        console.log("Done with last Doc");
      }
    }
  }

  const addPageNumberInIndex = async () => {
    if (index.length === 0) {
      alert("upload index");
      return
    }
    let formdata = new FormData()
    formdata.append("pdf", index[0].file)
    formdata.append("index_map", JSON.stringify(indexMap.current))
    if(advocateSig){
      formdata.append('advocate-sig',advocateSig)
      formdata.append("isOrignal", "false")
    }else{
      formdata.append("isOrignal", "true")
    }
    let res = await fetch("http://127.0.0.1:5000/api/add-page-no-in-index", {
      method: 'POST',
      body: formdata
    })
    if (res.ok) {
      console.log("done with index page no")
      const data = await res.blob()
      console.log(data)
      blobArrayRef.current = [data, ...blobArrayRef.current]
    }
  }

  const handleSubmitFile = async () => {
    setIsSubmitting(true)
    setCurrStep("Getting Data From Index")
    let res = await getTitlesFromIndex()
    if (res) {
      setCurrStep("work on first pdf (Doc before Annexures)")
      let temp = []
      let i = 0
      let j = 0
      let k = 0
      while (i < particulars.current.length && j < firstfiles.length && particulars.current[i].toLowerCase().search(/annexure/) === -1) {
        if (particulars.current[i].toLowerCase().search(/court fee/) !== -1) {
          if (temp.length !== 0) {
            console.log(temp)
            await workonfirstSection(temp,particulars.current.slice(k,i))
            k = i
          }
          await handleFinalFiles(courtFee,particulars.current[i])
          temp = []
          i++;
        } else {
          if ( j < firstfiles.length){
            temp.push(firstfiles[j])
            if(firstfiles[j].range !== ""){
              i = parseInt(firstfiles[j].range.split('-')[1])
            }
            j++;
          }
        }
      }
      if (temp.length != 0) {
        console.log(temp)
        await workonfirstSection(temp,particulars.current.slice(k,i))
      }
      setCurrStep("wok on Annexures")
      await handleAnnexures()
      setCurrStep("work on Application Vakalatnama and all...")
      i = particulars.current.length - 1;
      while (i >= 0 && !particulars.current[i].toLowerCase().startsWith("annexure")) {
        i--;
      }
      i++;
      let applicStartAt = null
      j = 0;

      console.log(application)
      if (application.length > 0) {
        console.log("application find out")
        applicStartAt = parseInt(application[0].range.split("-")[0]) - 1;
      }

      while (i < particulars.current.length){
        console.log("start at: ",applicStartAt,"index: ", i)
        if (applicStartAt !== null  && i == applicStartAt){
          let end = parseInt(application[j].range.split("-")[1]);
          console.log("go for application")
          await workonfirstSection([application[j]],particulars.current.slice(i,end));
          i = end - 1;
          j++;
          if (j < application.length){
            applicStartAt = parseInt(application[j].range.split("-")[0]);
          } else {
            applicStartAt = null;
          }
        } else if (particulars.current[i].toLowerCase().search(/vakalatnama/) !== -1){
          await handleFinalFiles(vakalatnamafiles,particulars.current[i])
        } else if (particulars.current[i].toLowerCase().search(/proof of service/) !== -1){
          await handleFinalFiles(proofService,particulars.current[i])
        } else if (particulars.current[i].toLowerCase().search(/authority letter/) !== -1){
          await handleFinalFiles(authLeter, particulars.current[i])
        } else if (particulars.current[i].toLowerCase().search(/court fee/) !== -1){
          await handleFinalFiles(courtFee, particulars.current[i])
        }
        console.log(particulars.current[i])
        i++;
      }
      setCurrStep("Adding book marks in whole doc")
      makeBookMarkForWholeDocument()
      setCurrStep("Insert page number range in Index")
      await addPageNumberInIndex()
      setCurrStep("Preparing Doc for downloading...")
      console.log(blobArrayRef.current)
      let response = await AddpageNumberService.addPageNoTitle(blobArrayRef.current)
      if (response.success) {
        let formdata = new FormData()
        formdata.append("pdf", new Blob([response.pdf], { type: 'application/pdf' }))
        formdata.append("bookmark", JSON.stringify(bookMarks.current))
        let res = await fetch("http://127.0.0.1:5000/api/add-book-mark", {
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
    setIsSubmitting(false)
  }

  return (
  <>
    <div className="pdf-container">

      <h1 className="title">PDF Annexure Manager</h1>
      <p className="subtitle">
        Upload multiple PDF files, add titles, and generate a merged PDF with bookmarks and OCR.
      </p>

      <label style={{marginRight: "10px"}} for="type">Select Court:</label>
      <select name="" id="type" ref={typeRef}>
        <option value="high_court">High Court</option>
        <option value="cat">CAT</option>
        <option value="ngt">NGT</option>
      </select>

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
            <div className="delete-btn" onClick={() => handleDelete(index, 0)}>
              <DeleteForeverIcon />
            </div>
          </div>
        ))}
        {index.length == 0 && <div className="actions">
          <button className="add-more-btn" onClick={() => { currSection.current = 0; document.querySelector('input[type="file"]').click() }} >
            + Add Index
          </button>
        </div>}
      </div>

      <div className="uploaded-section">
        <h2>Upload First Files (file before Annexures)</h2>
        {firstfiles.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
              <input
                type="text"
                placeholder="Index Serial Range (e.g., 1-2) of this doc"
                value={fileData.file.range}
                onChange={(e) => handleRangeChange(1, index, e)}
                className="range-input"
              />
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 1)}>
              <DeleteForeverIcon />
            </div>
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
            <div className="delete-btn" onClick={() => handleDelete(index, 2)}>
              <DeleteForeverIcon />
            </div>
          </div>
        ))}
        <div className="actions">
          <button className="add-more-btn" onClick={() => { currSection.current = 2; document.querySelector('input[type="file"]').click() }}>
            + Add More Files
          </button>
        </div>
      </div>



      <div className="uploaded-section">
        <h2>Upload Application (which come after annexure)</h2>
        {application.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
              <input
                type="text"
                placeholder="Index Serial Range (e.g., 1-2) of this doc"
                value={fileData.file.range}
                onChange={(e) => handleRangeChange(3, index, e)}
                className="range-input"  
              />
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 3)}>
              <DeleteForeverIcon />
            </div>
          </div>
        ))}
        <div className="actions">
          <button className="add-more-btn" onClick={() => { currSection.current = 3; document.querySelector('input[type="file"]').click() }}>
            + Add Applcation
          </button>
        </div>
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
        <h2>Uploaded Authority Letter</h2>
        {authLeter.map((fileData, index) => (
          <div className="file-card" key={index}>
            <div className="file-icon"><DocumentScannerIcon /></div>
            <div className="file-info">
              <strong>{fileData.file.name}</strong>
            </div>
            <div className="delete-btn" onClick={() => handleDelete(index, 7)}><DeleteForeverIcon /></div>
          </div>
        ))}
        <div className="actions">
          {authLeter.length == 0 && <button className="add-more-btn" onClick={() => { currSection.current = 7; document.querySelector('input[type="file"]').click() }}>
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
    </div>
    {isSubmitting && (
        <div className='loader-cont'>
          <FileText style={{width: "150px", height: "150px", color:"white", marginTop: "150px"}} className='animation' />
          <h1 style={{ color: "white"}}>{currStep}</h1>
          <Box sx={{ display: 'flex' }}>
            <CircularProgress />
          </Box>
        </div>
      )}
    </>
  )
}

export default App
