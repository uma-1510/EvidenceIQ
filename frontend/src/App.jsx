import { useState } from 'react';
import './styles/globals.css';


// ── Tab config 
const TABS = [
  { id:'timeline', label:'Event Timeline' },
  { id:'report',   label:'Evidence Report' },
];

// ── Header 
function Header({ jobId, hasResults, onReset }) {
  return (
    <header style={{
      height:52, flexShrink:0,
      background:'rgba(6,9,15,0.92)', backdropFilter:'blur(14px)',
      borderBottom:'1px solid var(--border-dim)',
      display:'flex', alignItems:'center',
      padding:'0 20px', gap:12, zIndex:50,
    }}>
      {/* Logo */}
      <div style={{display:'flex', alignItems:'center', gap:9}}>
        <span style={{fontSize:18, lineHeight:1}}>⚖</span>
        <span style={{
          fontFamily:'Syne, sans-serif', fontWeight:800, fontSize:17,
          letterSpacing:'-0.02em', color:'var(--text-primary)',
        }}>
          Evidence<span style={{color:'var(--accent)'}}>IQ</span>
        </span>
      </div>

      {/* Nova badge */}
      <span style={{
        fontFamily:'DM Mono, monospace', fontSize:8, fontWeight:700,
        letterSpacing:'0.12em', color:'var(--accent)',
        background:'var(--accent-glow)', padding:'3px 9px',
        borderRadius:20, border:'1px solid var(--border-accent)',
        textTransform:'uppercase',
      }}>
        Powered by Amazon Nova
      </span>

      <div style={{flex:1}}/>

      {/* Right actions */}
      {hasResults && (
        <div style={{display:'flex', gap:8}}>
          <button
            onClick={()=>downloadReport(jobId)}
            style={{
              display:'flex', alignItems:'center', gap:6,
              padding:'6px 14px', borderRadius:'var(--r-md)',
              background:'var(--accent)', border:'none',
              color:'#fff', fontSize:11, fontWeight:600, cursor:'pointer',
              fontFamily:'DM Sans, sans-serif',
              transition:'all var(--t) var(--ease)',
            }}
            onMouseEnter={e=>e.currentTarget.style.background='var(--accent-hover)'}
            onMouseLeave={e=>e.currentTarget.style.background='var(--accent)'}
          >
            📄 Download PDF
          </button>
          <button
            onClick={onReset}
            style={{
              padding:'6px 14px', borderRadius:'var(--r-md)',
              background:'var(--bg-elevated)', border:'1px solid var(--border-default)',
              color:'var(--text-secondary)', fontSize:11, cursor:'pointer',
              fontFamily:'DM Sans, sans-serif',
              transition:'all var(--t) var(--ease)',
            }}
            onMouseEnter={e=>e.currentTarget.style.borderColor='var(--accent)'}
            onMouseLeave={e=>e.currentTarget.style.borderColor='var(--border-default)'}
          >
            ← New Analysis
          </button>
        </div>
      )}
    </header>
  );
}

// ── Right panel placeholder (before analysis) 
function RightPlaceholder() {
  return (
    <div style={{
      display:'flex', flexDirection:'column', alignItems:'center',
      justifyContent:'center', height:'100%',
      gap:14, color:'var(--text-dim)',
    }}>
      <div style={{
        width:64, height:64, borderRadius:'50%',
        border:'1.5px dashed var(--border-dim)',
        display:'flex', alignItems:'center', justifyContent:'center',
        fontSize:26,
      }}>📋</div>
      <div style={{
        fontFamily:'Syne, sans-serif', fontWeight:600, fontSize:15,
        color:'var(--text-muted)', textAlign:'center', lineHeight:1.5,
      }}>
        Analysis results<br/>appear here
      </div>
      <div style={{
        fontSize:11, color:'var(--text-dim)',
        fontFamily:'DM Mono, monospace', textAlign:'center', lineHeight:1.7,
      }}>
        Timeline · Causal chains<br/>Evidence report · PDF export
      </div>
    </div>
  );
}

// ── Tab button 
function Tab({ id, label, active, badge, onClick }) {
  return (
    <button onClick={onClick} style={{
      fontFamily:'DM Sans, sans-serif', fontSize:12, fontWeight: active ? 600 : 400,
      padding:'10px 16px', cursor:'pointer', border:'none',
      borderBottom:`2px solid ${active ? 'var(--accent)' : 'transparent'}`,
      background:'transparent',
      color: active ? 'var(--accent-bright)' : 'var(--text-muted)',
      transition:'all var(--t) var(--ease)',
      display:'flex', alignItems:'center', gap:6, whiteSpace:'nowrap',
    }}>
      {label}
      {badge != null && (
        <span style={{
          fontFamily:'DM Mono, monospace', fontSize:9,
          background: active ? 'var(--accent-glow)' : 'var(--bg-elevated)',
          color: active ? 'var(--accent-bright)' : 'var(--text-muted)',
          padding:'1px 6px', borderRadius:20,
        }}>{badge}</span>
      )}
    </button>
  );
}

// // ── Main App 
export default function App() {

}