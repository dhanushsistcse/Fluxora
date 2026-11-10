import { useMemo, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import { api, BackendContractUnavailableError } from './services/api'

type Section = 'Universal Converter' | 'PDF Studio' | 'Document Studio' | 'Media Studio' | 'Compression Center' | 'Archive Manager' | 'Batch Processing' | 'Workflow Builder' | 'File Inspector' | 'Job History' | 'Security & Privacy'
type LocalFile = { file: File; id: string; format: string }

const navGroups: { label: string; items: { name: Section; icon: string }[] }[] = [
  { label: 'WORKSPACE', items: [{ name: 'Universal Converter', icon: '⇄' }, { name: 'PDF Studio', icon: '▤' }, { name: 'Document Studio', icon: '▧' }, { name: 'Media Studio', icon: '▣' }] },
  { label: 'TOOLS', items: [{ name: 'Compression Center', icon: '⌁' }, { name: 'Archive Manager', icon: '▣' }, { name: 'Batch Processing', icon: '▦' }, { name: 'Workflow Builder', icon: '⌘' }, { name: 'File Inspector', icon: '⌕' }] },
  { label: 'ACTIVITY', items: [{ name: 'Job History', icon: '◷' }, { name: 'Security & Privacy', icon: '◇' }] },
]
const modules: { name: Section; detail: string; icon: string; tone: string }[] = [
  { name: 'PDF Studio', detail: 'Merge, split, annotate and protect PDFs.', icon: '▤', tone: 'lavender' },
  { name: 'Document Studio', detail: 'Edit, organize and export documents.', icon: '▧', tone: 'blue' },
  { name: 'Media Studio', detail: 'Convert and optimize image, audio and video.', icon: '▣', tone: 'peach' },
  { name: 'Compression Center', detail: 'Reduce file size with quality in your control.', icon: '⌁', tone: 'mint' },
  { name: 'Archive Manager', detail: 'Create and inspect compressed archives.', icon: '▣', tone: 'yellow' },
  { name: 'Batch Processing', detail: 'Apply a consistent operation to many files.', icon: '▦', tone: 'pink' },
  { name: 'Workflow Builder', detail: 'Chain file operations into reusable flows.', icon: '⌘', tone: 'blue' },
  { name: 'File Inspector', detail: 'Review file properties and metadata.', icon: '⌕', tone: 'lavender' },
]
const operations: Record<string, string[]> = {
  'PDF Studio': ['Compress PDF', 'Merge documents', 'Split pages', 'Reorder pages', 'Rotate pages', 'Add watermark', 'Password protect', 'OCR scan', 'Edit PDF', 'Extract pages', 'Annotate PDF', 'PDF to DOCX', 'DOCX to PDF'],
  'Document Studio': ['DOCX editor', 'Text and tables', 'Insert image', 'Merge documents', 'Split document', 'Document metadata', 'Page layout', 'Export document'],
  'Media Studio': ['Image conversion', 'Resize image', 'Compress image', 'Audio conversion', 'Trim audio', 'Video conversion', 'Compress video', 'Extract audio', 'Generate GIF', 'Subtitle tools', 'Edit metadata'],
  'Compression Center': ['Compress PDF', 'Optimize image', 'Compress video', 'Create archive'],
  'Archive Manager': ['Create archive', 'Inspect archive', 'Extract files'],
  'Batch Processing': ['Convert multiple files', 'Compress multiple files', 'Apply saved workflow'],
  'Workflow Builder': ['Upload', 'Resize', 'Compress', 'Convert', 'Watermark', 'Export'],
}
const formatChoices = ['PDF', 'DOCX', 'TXT', 'JPG', 'PNG', 'WEBP', 'MP3', 'WAV', 'MP4', 'ZIP']
const formatOf = (file: File) => {
  const ext = file.name.split('.').pop()?.toUpperCase()
  return ext && ext !== file.name.toUpperCase() ? ext : (file.type.split('/').pop()?.toUpperCase() || 'UNKNOWN')
}
const bytes = (value: number) => value < 1024 * 1024 ? `${(value / 1024).toFixed(0)} KB` : `${(value / (1024 * 1024)).toFixed(1)} MB`

export default function App() {
  const [section, setSection] = useState<Section>('Universal Converter')
  const [files, setFiles] = useState<LocalFile[]>([])
  const [target, setTarget] = useState('PDF')
  const [quality, setQuality] = useState('Balanced')
  const [dragging, setDragging] = useState(false)
  const [dark, setDark] = useState(false)
  const [mobileNav, setMobileNav] = useState(false)
  const [notice, setNotice] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const addFiles = (selected: FileList | File[]) => {
    const incoming = Array.from(selected)
    if (!incoming.length) return
    setFiles((current) => [...current, ...incoming.map((file) => ({ file, id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2)}`, format: formatOf(file) }))])
    setNotice('')
  }
  const sourceFormats = useMemo(() => Array.from(new Set(files.map((item) => item.format))), [files])
  const drop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    addFiles(event.dataTransfer.files)
  }
  const pick = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) addFiles(event.target.files)
    event.target.value = ''
  }
  const runConversion = async () => {
    if (!files.length) return
    try {
      await api.createConversionJob({ files: files.map(({ file }) => file), targetFormat: target, quality })
      setNotice('The service accepted the request.')
    } catch (error) {
      setNotice(error instanceof BackendContractUnavailableError ? error.message : 'The request could not be completed. Check your connection and try again.')
    }
  }

  return <div className={`app-shell${dark ? ' theme-dark' : ''}`}>
    <aside className={`sidebar${mobileNav ? ' sidebar-open' : ''}`} aria-label="Main navigation">
      <button className="brand" onClick={() => setSection('Universal Converter')} aria-label="Fluxora home"><span className="brand-mark">f</span><span>fluxora<span className="brand-period">.</span></span></button>
      <div className="workspace-switch"><span className="workspace-avatar">F</span><span className="workspace-copy"><b>Local workspace</b><small>Account not connected</small></span><span className="chevron">⌄</span></div>
      <nav className="nav-list">{navGroups.map((group) => <div className="nav-group" key={group.label}><span className="nav-caption">{group.label}</span>{group.items.map((item) => <button key={item.name} className={`nav-item${section === item.name ? ' active' : ''}`} onClick={() => { setSection(item.name); setMobileNav(false); setNotice('') }}><span className="nav-icon">{item.icon}</span><span>{item.name}</span></button>)}</div>)}</nav>
      <div className="sidebar-bottom"><div className="storage-card"><div className="storage-heading"><span>Workspace status</span><span className="status-dot" /></div><p>Backend connection</p><small>Waiting for API contract</small><button className="text-action" onClick={() => setSection('Security & Privacy')}>Connection details <span>↗</span></button></div><div className="profile-row"><span className="profile-avatar">G</span><span className="profile-info"><b>Guest session</b><small>Authentication unavailable</small></span></div></div>
    </aside>
    {mobileNav && <button className="scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="mobile-menu" aria-label="Open navigation" onClick={() => setMobileNav(true)}>☰</button><div className="breadcrumbs">Workspace <span>/</span> <b>{section}</b></div></div><div className="topbar-actions"><div className="connection-pill"><span className="status-dot" /> API not connected</div><button className="icon-button theme-toggle" onClick={() => setDark((value) => !value)} aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}>{dark ? '☼' : '◐'}</button><button className="help-button" aria-label="Help">?</button></div></header>
      {section === 'Universal Converter' ? <div className="page-content"><div className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-line" /> YOUR FILE WORKSPACE</div><h1>Everything your files<br className="desktop-break" /> need, <span>in one place.</span></h1><p className="intro">Convert, organize, and refine your files with a workspace built to keep things simple.</p></div><div className="welcome-art" aria-hidden="true"><div className="art-orbit orbit-one"/><div className="art-orbit orbit-two"/><div className="art-file file-back">DOC</div><div className="art-file file-front">PDF</div><div className="art-spark">✦</div></div></div>
        <section className="converter-card" aria-labelledby="converter-title"><div className="card-title-row"><div className="title-icon">⇄</div><div><h2 id="converter-title">Universal converter</h2><p>Change file formats without changing your flow.</p></div><span className="secure-label"><span>◇</span> Private by design</span></div>
          <div className={`drop-zone${dragging ? ' is-dragging' : ''}${files.length ? ' has-files' : ''}`} onDragEnter={(e) => { e.preventDefault(); setDragging(true) }} onDragOver={(e) => e.preventDefault()} onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false) }} onDrop={drop} role={files.length ? 'group' : 'button'} tabIndex={0} aria-label="Upload files by dropping them here or browsing" onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputRef.current?.click() } }} onClick={() => inputRef.current?.click()}>
            <input ref={inputRef} className="visually-hidden" type="file" multiple onChange={pick} aria-label="Choose files to convert" />
            {files.length ? <><div className="file-list-head"><div><span className="upload-symbol small">↥</span><b>{files.length} {files.length === 1 ? 'file' : 'files'} ready</b><span className="muted"> · Drop more or browse</span></div><button className="clear-button" onClick={(e) => { e.stopPropagation(); setFiles([]); setNotice('') }}>Clear all</button></div><div className="selected-files">{files.map((item) => <div className="selected-file" key={item.id} onClick={(e) => e.stopPropagation()}><span className="file-type-icon">{item.format.slice(0, 3)}</span><span className="file-name"><b>{item.file.name}</b><small>{item.format} file · {bytes(item.file.size)}</small></span><button className="remove-file" aria-label={`Remove ${item.file.name}`} onClick={() => setFiles((current) => current.filter((entry) => entry.id !== item.id))}>×</button></div>)}</div></> : <div className="drop-empty"><span className="upload-symbol">↥</span><b>Drop your files here</b><span className="muted">or <span className="browse-link">browse files</span> from your device</span><small>Files remain on your device until a connected service accepts them.</small></div>}
          </div>
          <div className="converter-controls"><div className="select-field"><label htmlFor="source-format">From</label><div className="select-wrap"><span className="format-mark">{sourceFormats.length === 1 ? sourceFormats[0].slice(0, 3) : 'ANY'}</span><select id="source-format" value={sourceFormats.length === 1 ? sourceFormats[0] : 'Auto-detect'} disabled><option>{sourceFormats.length === 1 ? sourceFormats[0] : 'Auto-detect'}</option></select><span className="select-caret">⌄</span></div></div><div className="swap-wrap"><span className="swap-icon">→</span></div><div className="select-field"><label htmlFor="target-format">Convert to</label><div className="select-wrap"><span className="format-mark target-mark">{target.slice(0, 3)}</span><select id="target-format" value={target} onChange={(e) => setTarget(e.target.value)}>{formatChoices.map((format) => <option key={format} value={format}>{format}</option>)}</select><span className="select-caret">⌄</span></div></div><div className="select-field quality-field"><label htmlFor="quality">Quality preset</label><div className="select-wrap"><span className="quality-mark">◉</span><select id="quality" value={quality} onChange={(e) => setQuality(e.target.value)}>{['Smallest file', 'Balanced', 'Best quality'].map((option) => <option key={option}>{option}</option>)}</select><span className="select-caret">⌄</span></div></div></div>
          <div className="api-note"><span className="note-icon">i</span><span>Format support and quality options must be confirmed by the processing service before use.</span><button aria-label="More about format support" title="Backend format discovery is not available until API integration is implemented.">ⓘ</button></div>
          {notice && <div role="status" className={`notice${notice.includes('not configured') ? ' notice-warn' : ''}`}><span>!</span>{notice}</div>}
          <div className="converter-footer"><span className="limits-note"><span>◇</span> No upload limit configured</span><button className="primary-button" onClick={runConversion} disabled={!files.length}>Convert files <span>→</span></button></div>
        </section>
        <div className="section-heading"><div><div className="eyebrow">ONE WORKSPACE, MANY POSSIBILITIES</div><h2>Choose your next step</h2></div><button className="view-all" onClick={() => setSection('PDF Studio')}>Explore tools <span>→</span></button></div>
        <div className="module-grid">{modules.map((module) => <button className="module-card" key={module.name} onClick={() => setSection(module.name)}><span className={`module-icon ${module.tone}`}>{module.icon}</span><span className="module-arrow">↗</span><b>{module.name}</b><span className="module-detail">{module.detail}</span></button>)}</div>
        <div className="workflow-callout"><div className="workflow-icon">⌘</div><div><span className="callout-kicker">MAKE THE ROUTINE REPEATABLE</span><h3>One workflow. Every time.</h3><p>Build a reusable sequence of file operations for the work you do most.</p></div><button onClick={() => setSection('Workflow Builder')}>Explore workflows <span>→</span></button><span className="workflow-decoration">↗</span></div>
      </div> : <div className="page-content subpage-content"><div className="eyebrow"><span className="eyebrow-line" /> FLUXORA WORKSPACE</div><h1>{section}</h1><p className="intro">{sectionDescription(section)}</p>
        {section === 'Job History' ? <JobHistory onRetry={() => setSection('Universal Converter')} /> : section === 'Security & Privacy' ? <SecurityPanel /> : section === 'File Inspector' ? <InspectorPanel files={files} onChoose={() => inputRef.current?.click()} /> : <ToolPanel section={section} onUpload={() => inputRef.current?.click()} />}
        <input ref={inputRef} className="visually-hidden" type="file" multiple onChange={pick} aria-label="Choose files" />
      </div>}
      <footer className="app-footer"><span>Fluxora Studio <span>·</span> Your files, in good hands.</span><button onClick={() => setSection('Security & Privacy')}>Privacy & security</button><span>v0.1.0</span></footer>
    </main>
  </div>
}

function sectionDescription(section: Section) {
  const descriptions: Partial<Record<Section, string>> = {
    'PDF Studio': 'A focused space for working with pages, forms, and document workflows.',
    'Document Studio': 'Prepare, organize, and export your documents in one calm workspace.',
    'Media Studio': 'Tools for shaping image, audio, and video files to fit your needs.',
    'Compression Center': 'Find the right balance between a smaller file and the quality you need.',
    'Archive Manager': 'Create and inspect file archives with clear, controlled workflows.',
    'Batch Processing': 'Set up consistent operations for multiple files at once.',
    'Workflow Builder': 'Compose reusable file workflows from supported processing steps.',
    'File Inspector': 'Review the properties of a file before choosing what to do next.',
    'Job History': 'Track work submitted to the processing service.',
    'Security & Privacy': 'Understand how your files and processing requests are handled.',
  }
  return descriptions[section] ?? ''
}
function ToolPanel({ section, onUpload }: { section: Section; onUpload: () => void }) {
  const actions = operations[section] ?? []
  return <>
    {section === 'Workflow Builder' && <div className="contract-banner"><span>i</span><div><b>Workflow execution requires backend support</b><p>Visual steps will be enabled once the service contract defines validation, persistence, and execution APIs.</p></div></div>}
    <div className="tool-toolbar"><div><span className="subtle-label">{section === 'Workflow Builder' ? 'WORKFLOW STEPS' : 'AVAILABLE TOOLS'}</span><h2>{section === 'Workflow Builder' ? 'Start with a step' : `Explore ${section.replace(' Studio', '').toLowerCase()} tools`}</h2></div><button className="secondary-button" onClick={onUpload}>＋ Add files</button></div>
    <div className="tool-grid">{actions.map((action, index) => <article className="tool-card" key={action}><span className={`tool-number n${index % 4}`}>{String(index + 1).padStart(2, '0')}</span><div><h3>{action}</h3><p>{section === 'Workflow Builder' ? 'Workflow step · awaits API validation' : 'Operation settings and processing require a connected backend.'}</p></div><span className="pending-badge">Not connected</span><button className="tool-config" disabled title="Connect the documented processing API to configure this operation">Configure <span>→</span></button></article>)}</div>
    <div className="empty-feature"><div className="empty-art">✦</div><div><b>Ready when your processing service is</b><p>This workspace does not simulate processing. Connect the documented API to enable file operations and real job status.</p></div></div>
  </>
}
function JobHistory({ onRetry }: { onRetry: () => void }) {
  return <div className="job-history-card"><div className="history-table-head"><div><span className="subtle-label">RECENT ACTIVITY</span><h2>Processing jobs</h2></div><button className="secondary-button" disabled title="The job-list endpoint is not documented yet">↻ Refresh</button></div><div className="empty-state"><span className="empty-clock">◷</span><h3>No jobs to show yet</h3><p>Jobs will appear here after you submit a request to the connected processing service.</p><button className="primary-button" onClick={onRetry}>Start a conversion <span>→</span></button></div><div className="history-privacy"><span>◇</span> Job ownership, cancellation, retries, downloads, and expiry are controlled by the backend API.</div></div>
}
function SecurityPanel() {
  return <div className="security-layout"><div className="security-card"><div className="security-card-heading"><span className="security-icon">◇</span><div><h2>Connection & file handling</h2><p>We only show what can be verified from this frontend.</p></div></div><div className="security-row"><div><b>Processing API</b><span>No backend API contract found in this workspace.</span></div><span className="state-chip state-pending">Not configured</span></div><div className="security-row"><div><b>Authentication</b><span>Login and ownership controls depend on backend documentation.</span></div><span className="state-chip state-pending">Unknown</span></div><div className="security-row"><div><b>File retention & expiry</b><span>Retention policy and expiry indicators are not documented yet.</span></div><span className="state-chip state-pending">Unknown</span></div><div className="security-row"><div><b>Upload limits</b><span>Maximum file size and supported MIME types have not been provided.</span></div><span className="state-chip state-pending">Unknown</span></div></div><div className="privacy-aside"><span className="privacy-shield">⌑</span><h3>Transparency first</h3><p>This app does not send files, create fake jobs, or claim a privacy policy that the service has not documented.</p></div></div>
}
function InspectorPanel({ files, onChoose }: { files: LocalFile[]; onChoose: () => void }) {
  return <div className="inspector-card"><div className="inspector-head"><div><span className="subtle-label">LOCAL FILE DETAILS</span><h2>File inspector</h2><p>Properties are read from your browser selection; server-side metadata is unavailable.</p></div><button className="secondary-button" onClick={onChoose}>＋ Choose files</button></div>{files.length ? <div className="inspector-list">{files.map(({ file, format, id }) => <div className="inspector-row" key={id}><span className="file-type-icon">{format.slice(0, 3)}</span><div><b>{file.name}</b><small>{format} · {bytes(file.size)} · Modified {new Date(file.lastModified).toLocaleDateString()}</small></div><span className="state-chip">Local only</span></div>)}</div> : <div className="empty-state compact"><span className="empty-clock">⌕</span><h3>Select a file to inspect</h3><p>Nothing is uploaded by inspecting a local file here.</p><button className="primary-button" onClick={onChoose}>Choose a file <span>→</span></button></div>}</div>
}
