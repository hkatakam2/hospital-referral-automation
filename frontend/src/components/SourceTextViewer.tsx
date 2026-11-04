import { useEffect, useRef } from 'react'
import type { DocumentDetail } from '../api/types'

export function SourceTextViewer({ document, pageNumber, quote, onPage }: {
  document: DocumentDetail; pageNumber: number; quote?: string; onPage: (page: number) => void
}) {
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => { heading.current?.focus() }, [document.id, pageNumber, quote])
  const page = document.pages.find(value => value.page_number === pageNumber)
  return <div className="source-viewer">
    <h3 ref={heading} tabIndex={-1}>Source: {document.original_filename}, page {pageNumber}</h3>
    <div className="page-selector"><label htmlFor="source-page">Page</label>
      <select id="source-page" value={pageNumber} onChange={event => onPage(Number(event.target.value))}>
        {document.pages.map(item => <option key={item.page_number} value={item.page_number}>{item.page_number}</option>)}
      </select>
    </div>
    {quote && <blockquote><span className="eyebrow">Cited evidence</span><p>{quote}</p></blockquote>}
    {!page ? <p className="error" role="alert">Source page is unavailable.</p> : page.text_status === 'no_text'
      ? <p className="warning">This page has no usable text. It may be blank or require OCR.</p>
      : <pre>{page.text}</pre>}
  </div>
}
