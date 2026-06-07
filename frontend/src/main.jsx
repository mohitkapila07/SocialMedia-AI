import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import { CalendarDays, Sparkles, BarChart3, Lightbulb, Users, Bell, Plus, ChevronLeft, ChevronRight, X, Search, Trash2, CheckCircle2, LogOut, ShieldCheck, LockKeyhole, UserPlus, Settings as SettingsIcon, Download, RotateCcw, Pencil, ListChecks, SlidersHorizontal, MapPin, Clock3, Tag, KanbanSquare, GripVertical, ArrowRightCircle, Eye, ThumbsUp, ThumbsDown, Bookmark } from 'lucide-react';
import './index.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API = axios.create({ baseURL: API_BASE });
const mediaSrc = (url) => url?.startsWith('/uploads') ? `${API_BASE}${url}` : url;
const PLATFORMS = ['Instagram', 'Facebook', 'LinkedIn', 'Twitter', 'YouTube', 'TikTok', 'Pinterest'];
const POST_TYPES = ['image', 'reel', 'video', 'carousel', 'text', 'poll'];
const STATUSES = ['Idea', 'Drafting', 'Ready', 'Scheduled', 'Posted'];
const WORKFLOW_COLUMNS = [
  { key: 'Idea', label: 'Ideas', hint: 'Raw content ideas waiting for planning' },
  { key: 'Drafting', label: 'Drafting', hint: 'Caption/design work in progress' },
  { key: 'Ready', label: 'Ready', hint: 'Approved and ready to schedule' },
  { key: 'Scheduled', label: 'Scheduled', hint: 'Placed on calendar with time/date' },
  { key: 'Posted', label: 'Posted', hint: 'Published or marked complete' },
];

API.interceptors.request.use((config) => {
  const token = localStorage.getItem('sm_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

function Toast({ message }) { return message ? <div className="toast"><CheckCircle2 size={16}/>{message}</div> : null; }

function LoginPage({ onLogin }) {
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function suggestBestTime() {
    setAiLoading(true);
    try {
      const base = editPost ? new Date(editPost.scheduled_at) : new Date(selectedDate || new Date());
      const post_day = base.toLocaleDateString('en', { weekday: 'long' });
      const res = await API.post('/ai/best-time', { platform: form.platform, post_type: form.post_type, post_day, occasion: form.occasion, content: form.content, media_score: mediaResult?.media_score || form.media_score || null });
      setAiResult(res.data);
      if (res.data.best_time) setForm(f => ({ ...f, time: res.data.best_time }));
      if (res.data.hashtags?.length) {
        setForm(f => ({ ...f, content: f.content ? `${f.content}\n\n${res.data.hashtags.join(' ')}` : res.data.hashtags.join(' ') }));
      }
    } catch { setAiResult({ error: 'AI suggestion failed. Check backend.' }); }
    setAiLoading(false);
  }
  async function uploadMedia(file) {
    if (!file) return;
    setMediaLoading(true);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await API.post('/media/analyze', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setMediaResult(res.data);
      setForm(f => ({ ...f, media_url: res.data.media_url, media_type: res.data.media_type, media_score: res.data.media_score }));
      setAiResult(null);
    } catch {
      setMediaResult({ error: 'Media analysis failed. Check backend.' });
    }
    setMediaLoading(false);
  }
  async function submit(e) {
    e.preventDefault(); setError(''); setLoading(true);
    try {
      const res = await API.post('/auth/login', form);
      localStorage.setItem('sm_token', res.data.access_token);
      localStorage.setItem('sm_user', JSON.stringify(res.data.user));
      onLogin(res.data.user);
    } catch (err) { setError(err.response?.data?.detail || 'Login failed. Check backend is running.'); }
    setLoading(false);
  }
  return <div className="login-page">
    <div className="login-left">
      <div className="brand big">SocialMedia <span>AI</span></div>
      <h1>Secure social media scheduler</h1>
      <p>Plan content, connect accounts, generate captions, and manage posts from a clean dashboard.</p>
      <div className="secure-note"><ShieldCheck size={18}/> Your data stays protected on the backend.</div>
    </div>
    <form className="login-card" onSubmit={submit}>
      <LockKeyhole size={26}/><h2>Admin Login</h2><p></p>
      <label>Email<input value={form.email} onChange={e=>setForm({...form,email:e.target.value})} autoFocus /></label>
      <label>Password<input type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} /></label>
      {error && <div className="error">{error}</div>}
      <button className="primary login-submit" disabled={loading}>{loading ? 'Signing in...' : 'Login'}</button>
      <small></small>
    </form>
  </div>
}

function Sidebar({ active, setActive, onLogout }) {
  const nav = [
    ['PLAN', [[CalendarDays, 'Calendar', 'calendar'], [Eye, 'Preview', 'preview'], [KanbanSquare, 'Queue', 'workflow'], [Sparkles, 'Create', 'creator']]],
    ['MEASURE', [[BarChart3, 'Analytics', 'analytics']]],
    ['MANAGE', [[Users, 'Channels', 'accounts'], [Bell, 'Notifications', 'notifications'], [SettingsIcon, 'Settings', 'settings']]],
  ];
  return <aside className="sidebar simplified-sidebar">
    <div className="brand"><div className="brand-title">SocialMedia <span>AI</span></div><div className="brand-sub">Simple content planner</div></div>
    <nav>{nav.map(([section, items]) => <div key={section} className="nav-section"><p>{section}</p>{items.map(([Icon, label, key]) => <button key={key} onClick={() => setActive(key)} className={active === key ? 'nav-item active' : 'nav-item'}><Icon size={16}/><span>{label}</span></button>)}</div>)}</nav>
    <div className="sidebar-help"><Sparkles size={16}/><span>Smart scheduling enabled</span></div>
    <div className="profile"><div className="avatar">MC</div><div><strong>Mohit C.</strong><span>Admin</span></div></div>
    <button className="logout" onClick={onLogout}><LogOut size={15}/> Logout</button>
  </aside>
}

function PageHead({title, children}){ return <header className="topbar"><h1>{title}</h1><div className="top-actions">{children}</div></header> }
function fmtDate(v){ return new Date(v).toLocaleDateString('en-IN',{day:'2-digit', month:'short', year:'numeric'}); }
function fmtTime(v){ return new Date(v).toLocaleTimeString('en-IN',{hour:'2-digit', minute:'2-digit'}); }

function PostModal({ open, onClose, selectedDate, onSave, editPost }) {
  const empty = { title: '', platform: 'Instagram', post_type: 'image', content: '', time: '10:00', status: 'Scheduled', location: 'Online', occasion: 'General', media_url: '', media_type: '', media_score: '', ai_score: '' };
  const [form, setForm] = useState(empty);
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  const [mediaResult, setMediaResult] = useState(null);
  const [mediaLoading, setMediaLoading] = useState(false);
  useEffect(() => {
    if (!open) return;
    if (editPost) {
      const d = new Date(editPost.scheduled_at);
      setForm({ title: editPost.title, platform: editPost.platform, post_type: editPost.post_type || 'image', content: editPost.content || '', time: `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`, status: editPost.status || 'Scheduled', location: editPost.location || 'Online', occasion: editPost.occasion || 'General', media_url: editPost.media_url || '', media_type: editPost.media_type || '', media_score: editPost.media_score || '', ai_score: editPost.ai_score || '' });
      setMediaResult(editPost.media_score ? { media_score: editPost.media_score, media_type: editPost.media_type, media_url: editPost.media_url, factors: ['Previously analyzed media'] } : null);
    } else setForm(empty);
    setAiResult(null);
    if (!editPost) setMediaResult(null);
  }, [open, editPost]);
  if (!open) return null;
  async function aiCaption() {
    setLoading(true);
    try { const res = await API.post('/ai/caption', { topic: form.title || form.occasion || 'new campaign', platform: form.platform }); setForm(f => ({ ...f, content: res.data.caption })); }
    catch { setForm(f => ({ ...f, content: `Fresh ${form.platform} caption for ${form.title || 'your new post'} with a clear CTA.` })); }
    setLoading(false);
  }
  async function suggestBestTime() {
    setAiLoading(true);
    try {
      const base = editPost ? new Date(editPost.scheduled_at) : new Date(selectedDate || new Date());
      const post_day = base.toLocaleDateString('en', { weekday: 'long' });
      const res = await API.post('/ai/best-time', { platform: form.platform, post_type: form.post_type, post_day, occasion: form.occasion, content: form.content, media_score: mediaResult?.media_score || form.media_score || null });
      setAiResult(res.data);
      if (res.data.best_time) setForm(f => ({ ...f, time: res.data.best_time }));
      if (res.data.hashtags?.length) {
        setForm(f => ({ ...f, content: f.content ? `${f.content}\n\n${res.data.hashtags.join(' ')}` : res.data.hashtags.join(' ') }));
      }
    } catch { setAiResult({ error: 'AI suggestion failed. Check backend.' }); }
    setAiLoading(false);
  }
  async function uploadMedia(file) {
    if (!file) return;
    setMediaLoading(true);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await API.post('/media/analyze', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setMediaResult(res.data);
      setForm(f => ({ ...f, media_url: res.data.media_url, media_type: res.data.media_type, media_score: res.data.media_score }));
      setAiResult(null);
    } catch {
      setMediaResult({ error: 'Media analysis failed. Check backend.' });
    }
    setMediaLoading(false);
  }
  async function submit(e) {
    e.preventDefault(); if (!form.title.trim()) return;
    const base = editPost ? new Date(editPost.scheduled_at) : new Date(selectedDate || new Date());
    const [h,m] = form.time.split(':'); base.setHours(Number(h), Number(m), 0, 0);
    await onSave({ title: form.title.trim(), platform: form.platform, post_type: form.post_type, content: form.content, scheduled_at: base.toISOString(), status: form.status, location: form.location, occasion: form.occasion, media_url: form.media_url || null, media_type: form.media_type || null, media_score: form.media_score ? Number(form.media_score) : null, ai_score: aiResult?.ai_score || form.ai_score || null, ai_details: aiResult || null }, editPost?.id);
  }
  return <div className="overlay" onMouseDown={onClose}><form className="modal" onMouseDown={e=>e.stopPropagation()} onSubmit={submit}>
    <div className="modal-head"><h2>{editPost ? 'Edit Post' : 'New Post'}</h2><button type="button" onClick={onClose}><X size={18}/></button></div>
    <label>Title<input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="Campaign title" autoFocus /></label>
    <div className="two"><label>Platform<select value={form.platform} onChange={e=>setForm({...form,platform:e.target.value})}>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select></label><label>Post type<select value={form.post_type} onChange={e=>setForm({...form,post_type:e.target.value})}>{POST_TYPES.map(p=><option key={p}>{p}</option>)}</select></label></div>
    <div className="two"><label>Time<input type="time" value={form.time} onChange={e=>setForm({...form,time:e.target.value})}/></label><label>AI score<input readOnly value={aiResult?.ai_score ? `${aiResult.ai_score}/100 • ${aiResult.score_label}` : form.ai_score ? `${form.ai_score}/100` : 'Click Suggest Best Time'} /></label></div>
    <div className="two"><label>Place / Channel<input value={form.location} onChange={e=>setForm({...form,location:e.target.value})} placeholder="Instagram Feed / Store / Event" /></label><label>Occasion<input value={form.occasion} onChange={e=>setForm({...form,occasion:e.target.value})} placeholder="Launch, festival, giveaway" /></label></div>
    <label>Status<select value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>{STATUSES.map(s=><option key={s}>{s}</option>)}</select></label>
    <label>Content<textarea value={form.content} onChange={e=>setForm({...form,content:e.target.value})} placeholder="Write caption here..." /></label>
    <label>Image / Video upload <span className="field-hint">optional, improves AI score</span><input type="file" accept="image/*,video/*" onChange={e=>uploadMedia(e.target.files?.[0])} /></label>
    {mediaLoading && <div className="media-analysis">Analyzing media...</div>}
    {mediaResult && <div className="media-analysis">{mediaResult.error ? mediaResult.error : <><strong>Media score: {mediaResult.media_score}/100</strong><span>{mediaResult.media_type}</span>{mediaResult.media_url && mediaResult.media_type === 'image' && <img src={mediaSrc(mediaResult.media_url)} alt="Uploaded media preview" />}{(mediaResult.factors||[]).map((f,i)=><small key={i}>{f}</small>)}</>}</div>}
    <div className="ai-actions"><button type="button" className="ai-btn" onClick={aiCaption} disabled={loading}>{loading ? 'Generating...' : 'Generate AI Caption'}</button><button type="button" className="ai-btn strong" onClick={suggestBestTime} disabled={aiLoading}>{aiLoading ? 'Analyzing...' : 'Suggest Best Time'}</button></div>
    {aiResult && <div className="ai-result">{aiResult.error ? aiResult.error : <><strong>AI recommendation: {aiResult.ai_score}/100 ({aiResult.score_label || aiResult.confidence})</strong><span>Best time: {aiResult.best_time} • Engagement estimate: {aiResult.predicted_engagement}</span><small>Formula: {aiResult.score_formula || 'timing + caption + media'} • Top times: {(aiResult.top_times||[]).map(t=>`${t.time} (${t.ai_score || t.score}/100)`).join(', ')}</small><em>{aiResult.message}</em></>}</div>}
    <div className="actions"><button type="button" onClick={onClose}>Cancel</button><button className="primary">{editPost ? 'Save Changes' : 'Schedule Post'}</button></div>
  </form></div>
}

function ContentCalendar({ query, setQuery, posts, setPosts, setToast }) {
  const [cursor, setCursor] = useState(new Date(2026, 3, 1));
  const [modalDate, setModalDate] = useState(null);
  const [editPost, setEditPost] = useState(null);
  const [view, setView] = useState('Monthly');
  const [platformFilter,setPlatformFilter]=useState('All');
  const [statusFilter,setStatusFilter]=useState('All');
  const [cellSize,setCellSize]=useState(110);
  const year = cursor.getFullYear(), month = cursor.getMonth();
  useEffect(() => { load(); }, [month, year, platformFilter, statusFilter]);
  async function load() { try { const res = await API.get(`/posts?month=${month+1}&year=${year}&platform=${platformFilter}&status=${statusFilter}`); setPosts(res.data); } catch (e) { if(e.response?.status===401) window.dispatchEvent(new Event('force-logout')); else setToast('Backend not running.'); } }
  const monthDays = useMemo(() => { const first = new Date(year, month, 1).getDay(); const total = new Date(year, month + 1, 0).getDate(); const arr=[]; for(let i=0;i<first;i++) arr.push(null); for(let d=1;d<=total;d++) arr.push(new Date(year,month,d)); while(arr.length%7) arr.push(null); return arr; }, [month, year]);
  const weekDays = useMemo(() => { const start = new Date(cursor); start.setDate(cursor.getDate() - cursor.getDay()); return Array.from({length:7}, (_,i)=>{ const d=new Date(start); d.setDate(start.getDate()+i); return d; }); }, [cursor]);
  const dayList = useMemo(() => [new Date(cursor)], [cursor]);
  const visibleDays = view === 'Monthly' ? monthDays : view === 'Weekly' ? weekDays : dayList;
  const rangeTitle = view === 'Monthly' ? cursor.toLocaleString('en', { month: 'long', year: 'numeric' }) : view === 'Weekly' ? `${weekDays[0].toLocaleDateString('en-IN',{day:'2-digit',month:'short'})} - ${weekDays[6].toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})}` : cursor.toLocaleDateString('en-IN',{weekday:'long',day:'2-digit',month:'long',year:'numeric'});
  const filtered = posts.filter(p => (p.title+p.platform+p.content+(p.location||'')+(p.occasion||'')).toLowerCase().includes(query.toLowerCase()));
  const dateKey = d => `${d.getFullYear()}-${d.getMonth()+1}-${d.getDate()}`;
  const byDate = filtered.reduce((a,p)=>{ const d = new Date(p.scheduled_at); (a[dateKey(d)] ||= []).push(p); return a; }, {});
  const goPrev = () => { if(view==='Monthly') setCursor(new Date(year, month-1, 1)); else { const d=new Date(cursor); d.setDate(cursor.getDate()-(view==='Weekly'?7:1)); setCursor(d); } };
  const goNext = () => { if(view==='Monthly') setCursor(new Date(year, month+1, 1)); else { const d=new Date(cursor); d.setDate(cursor.getDate()+(view==='Weekly'?7:1)); setCursor(d); } };
  async function savePost(payload, id) { try { const res = id ? await API.put(`/posts/${id}`, payload) : await API.post('/posts', payload); setPosts(id ? posts.map(p=>p.id===id?res.data:p) : [...posts, res.data]); setToast(id ? 'Post updated' : 'Post scheduled'); } catch { setToast('Could not save post'); } setModalDate(null); setEditPost(null); }
  async function del(id) { try { await API.delete(`/posts/${id}`); setPosts(posts.filter(p=>p.id!==id)); setToast('Post deleted'); } catch { setToast('Could not delete post'); } }
  async function reset(){ try{ await API.post('/posts/reset'); await load(); setToast('All posts cleared'); }catch{setToast('Could not reset posts')} }
  async function seedDemo(){ try{ await API.post('/demo/seed'); await load(); setToast('Sample content loaded'); }catch{setToast('Could not load sample content')} }
  async function exp(){ try{ const r=await API.get('/posts/export'); const blob=new Blob([JSON.stringify(r.data,null,2)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='socialmedia-posts.json'; a.click(); setToast('Posts exported'); }catch{setToast('Export failed')} }
  return <main className="main calendar-main"><PageHead title="Content Calendar"><div className="search"><Search size={15}/><input placeholder="Search posts, place, occasion" value={query} onChange={e=>setQuery(e.target.value)} /></div><button onClick={()=>window.dispatchEvent(new Event('open-account'))}>+ Connect Channel</button><button className="primary" onClick={()=>setModalDate(new Date(year,month,new Date().getDate()))}>+ New Post</button></PageHead>
    <section className="calendar-shell">
      <div className="calendar-toolbar">
        <div className="filters"><select value={platformFilter} onChange={e=>setPlatformFilter(e.target.value)}><option>All</option>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select><select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option>All</option>{STATUSES.map(s=><option key={s}>{s}</option>)}</select><button onClick={seedDemo}><Sparkles size={15}/> Load sample content</button><button onClick={exp}><Download size={15}/> Export</button><button onClick={reset}><RotateCcw size={15}/> Clear posts</button></div>
        <div className="size-control"><SlidersHorizontal size={16}/><span>Calendar size</span><input type="range" min="88" max="165" value={cellSize} onChange={e=>setCellSize(Number(e.target.value))}/></div>
      </div>
      <div className="calendar-title-row"><button className="iconbtn" onClick={goPrev}><ChevronLeft/></button><h2>{rangeTitle}</h2><button className="iconbtn" onClick={goNext}><ChevronRight/></button><div className="view-switch">{['Monthly','Weekly','Daily'].map(v=><button key={v} className={view===v?'active':''} onClick={()=>setView(v)}>{v}</button>)}</div></div>
      <div className={`calendar-card ${view.toLowerCase()}-view`} style={{'--cell-h': `${cellSize}px`}}>
        {(view === 'Daily' ? [cursor.toLocaleDateString('en-IN',{weekday:'long'})] : ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']).map(d=><div className="weekday" key={d}>{d}</div>)}
        {visibleDays.map((date,i)=><div key={i} className={date?'day':'day muted-day'}>{date && <><div className="day-top"><b>{view==='Monthly' ? date.getDate() : date.toLocaleDateString('en-IN',{day:'2-digit', month:'short'})}</b><button onClick={()=>setModalDate(date)}>+ add</button></div><div className="pill-list">{(byDate[dateKey(date)]||[]).map(p=><div className={`post-pill ${p.platform.toLowerCase()}`} key={p.id} onClick={()=>setEditPost(p)} title="Click to edit"><span>{fmtTime(p.scheduled_at)}</span>{p.title}<small>{p.post_type || 'image'} • {p.location || 'Online'} • {p.occasion || 'General'}</small><button onClick={(e)=>{e.stopPropagation(); del(p.id)}}>×</button></div>)}</div></>}</div>)}
      </div>
    </section>
    <PostModal open={!!modalDate || !!editPost} selectedDate={modalDate} editPost={editPost} onClose={()=>{setModalDate(null);setEditPost(null)}} onSave={savePost}/>
  </main>
}

function PostsPage({ query, setQuery, posts, setPosts, setToast }){
  const [editPost,setEditPost]=useState(null);
  const [platform,setPlatform]=useState('All');
  const [status,setStatus]=useState('All');
  useEffect(()=>{load()},[platform,status]);
  async function load(){ try{ const r=await API.get(`/posts?platform=${platform}&status=${status}`); setPosts(r.data); }catch{setToast('Could not load posts')} }
  async function save(payload,id){ try{ const r=await API.put(`/posts/${id}`,payload); setPosts(posts.map(p=>p.id===id?r.data:p)); setEditPost(null); setToast('Post updated'); }catch{setToast('Could not update post')} }
  async function del(id){ try{ await API.delete(`/posts/${id}`); setPosts(posts.filter(p=>p.id!==id)); setToast('Post deleted'); }catch{setToast('Could not delete post')} }
  const rows=posts.filter(p=>(p.title+p.platform+(p.location||'')+(p.occasion||'')+p.status).toLowerCase().includes(query.toLowerCase()));
  return <main className="main"><PageHead title="Posts Library"><div className="search"><Search size={15}/><input placeholder="Search all posts" value={query} onChange={e=>setQuery(e.target.value)} /></div></PageHead>
    <section className="panel post-library-head"><div><h2>All scheduled content</h2><p>Stores every post with date, time, place/channel, occasion and status.</p></div><div className="filters compact"><select value={platform} onChange={e=>setPlatform(e.target.value)}><option>All</option>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select><select value={status} onChange={e=>setStatus(e.target.value)}><option>All</option>{STATUSES.map(s=><option key={s}>{s}</option>)}</select></div></section>
    <div className="posts-grid">{rows.map(p=><article className="post-card" key={p.id}><div className="post-card-top"><span className={`platform-dot ${p.platform.toLowerCase()}`}>{p.platform}</span><span className={`status-badge ${p.status.toLowerCase()}`}>{p.status}</span></div><h3>{p.title}</h3><div className="meta"><span><CalendarDays size={14}/>{fmtDate(p.scheduled_at)}</span><span><Clock3 size={14}/>{fmtTime(p.scheduled_at)}</span><span><MapPin size={14}/>{p.location || 'Online'}</span><span><Tag size={14}/>{p.occasion || 'General'} • {p.post_type || 'image'}</span></div><p>{p.content || 'No caption added yet.'}</p><div className="mini-actions"><button onClick={()=>setEditPost(p)}><Pencil size={15}/> Edit</button><button onClick={()=>del(p.id)}><Trash2 size={15}/> Delete</button></div></article>)}</div>
    {rows.length===0 && <div className="panel empty">No posts found.</div>}
    <PostModal open={!!editPost} editPost={editPost} onClose={()=>setEditPost(null)} onSave={save}/>
  </main>
}



function PreviewPage({ setToast }){
  const [items,setItems]=useState([]);
  const [platform,setPlatform]=useState('All');
  const [savedOnly,setSavedOnly]=useState(false);
  const [feedback,setFeedback]=useState({});
  const [loading,setLoading]=useState(true);
  const [search,setSearch]=useState('');

  useEffect(()=>{load()},[platform,savedOnly]);

  async function load(){
    setLoading(true);
    try{
      const r=await API.get(`/previews?platform=${platform}&saved_only=${savedOnly}`);
      setItems(r.data || []);
    }catch{
      setToast('Could not load previews');
    }
    setLoading(false);
  }

  async function savePreference(post, isSaved=true){
    try{
      const notes = feedback[post.id]?.notes ?? post.preference_notes ?? '';
      const r=await API.patch(`/posts/${post.id}/preference`, { is_saved:isSaved, preference_notes:notes });
      setItems(items.map(i=>i.id===post.id?r.data:i));
      setToast(isSaved ? 'Saved for future preference' : 'Removed from saved preferences');
    }catch{
      setToast('Could not save preference');
    }
  }

  async function sendFeedback(post, value){
    try{
      const reason = feedback[post.id]?.reason || '';
      await API.post(`/posts/${post.id}/feedback`, { feedback:value, reason });
      await load();
      setToast(value==='like' ? 'Like saved to training feedback' : 'Dislike saved to training feedback');
    }catch{
      setToast('Could not save feedback');
    }
  }

  const cards = items.filter(p => {
    const haystack = `${p.title || ''} ${p.platform || ''} ${p.content || ''} ${p.occasion || ''} ${p.post_type || ''}`.toLowerCase();
    return haystack.includes(search.toLowerCase());
  });

  return <main className="main preview-main">
    <PageHead title="Preview Studio">
      <div className="preview-toolbar">
        <div className="search preview-search"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search previews" /></div>
        <select value={platform} onChange={e=>setPlatform(e.target.value)}><option>All</option>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select>
        <button className={savedOnly?'primary':''} onClick={()=>setSavedOnly(!savedOnly)}><Bookmark size={15}/> {savedOnly?'Saved only':'All previews'}</button>
      </div>
    </PageHead>

    <section className="preview-hero">
      <div>
        <span className="eyebrow">Visual approval + AI training</span>
        <h2>Review posts and reels before publishing</h2>
        <p>Save the best styles for future preference and use direct like/dislike feedback to improve future AI scoring.</p>
      </div>
      <a className="ghost-link" href={`${API_BASE}/feedback/training`} target="_blank" rel="noreferrer">View training CSV</a>
    </section>

    {loading && <div className="panel preview-state">Loading previews...</div>}
    {!loading && !items.length && <div className="panel preview-state">No previews found. Create a post first.</div>}
    {!loading && items.length > 0 && !cards.length && <div className="panel preview-state">No previews match your search.</div>}

    <section className="preview-grid-clean">{cards.map(post=>{
      const type=(post.media_type || post.post_type || 'image').toLowerCase();
      const isVideo=type.includes('video') || type.includes('reel');
      const saved = !!post.is_saved;
      return <article className="preview-card-clean" key={post.id}>
        <div className="preview-card-head">
          <span className={`platform-dot ${post.platform.toLowerCase()}`}>{post.platform}</span>
          <span className={`status-badge ${post.status.toLowerCase()}`}>{post.status}</span>
        </div>

        <div className={`mock-preview ${isVideo?'reel':'post'}`}>
          <div className="mock-top"><span>{post.platform}</span><small>{isVideo?'Reel preview':'Post preview'}</small></div>
          <div className="media-stage-clean">
            {post.media_url ? (isVideo ? <video src={mediaSrc(post.media_url)} controls/> : <img src={mediaSrc(post.media_url)} alt={post.title}/>) : <div className="media-placeholder-clean"><Sparkles size={30}/><b>{isVideo?'Reel':'Image'} preview</b><span>No media uploaded yet</span></div>}
          </div>
          <div className="mock-caption"><b>{post.title}</b><p>{post.content || 'No caption added yet.'}</p></div>
        </div>

        <div className="preview-meta-grid">
          <span><Clock3 size={14}/>{fmtDate(post.scheduled_at)} · {fmtTime(post.scheduled_at)}</span>
          <span><Tag size={14}/>{post.occasion || 'General'} · {post.post_type}</span>
        </div>

        <div className="preview-score-strip">
          <b>AI {post.ai_score || '—'}/100</b>
          <span>Media {post.media_score || '—'}/100</span>
          <span>👍 {post.like_count || 0}</span>
          <span>👎 {post.dislike_count || 0}</span>
        </div>

        <label className="compact-label">Preference notes
          <textarea value={feedback[post.id]?.notes ?? post.preference_notes ?? ''} onChange={e=>setFeedback({...feedback,[post.id]:{...(feedback[post.id]||{}),notes:e.target.value}})} placeholder="Example: use this color tone, hook, product angle, or caption style again" />
        </label>
        <label className="compact-label">Feedback reason
          <input value={feedback[post.id]?.reason || ''} onChange={e=>setFeedback({...feedback,[post.id]:{...(feedback[post.id]||{}),reason:e.target.value}})} placeholder="Why did you like or dislike this?" />
        </label>

        <div className="preview-actions-clean">
          <button className={saved?'primary':''} onClick={()=>savePreference(post,!saved)}><Bookmark size={15}/> {saved?'Saved':'Save'}</button>
          <button onClick={()=>sendFeedback(post,'like')}><ThumbsUp size={15}/> Like</button>
          <button onClick={()=>sendFeedback(post,'dislike')}><ThumbsDown size={15}/> Dislike</button>
        </div>
      </article>
    })}</section>
  </main>
}

function WorkflowBoard({ query, setQuery, posts, setPosts, setToast }){
  const [dragId,setDragId]=useState(null);
  const [platform,setPlatform]=useState('All');
  const [aiScores,setAiScores]=useState({});
  const [loading,setLoading]=useState(true);
  const [mode,setMode]=useState('queue');
  const [modalDate,setModalDate]=useState(null);
  const [editPost,setEditPost]=useState(null);
  useEffect(()=>{ load(); }, [platform]);
  useEffect(()=>{ scorePosts(); }, [posts]);
  async function load(){
    setLoading(true);
    try{ const r=await API.get(`/posts?platform=${platform}&status=All`); setPosts(r.data); }
    catch{ setToast('Could not load queue posts'); }
    setLoading(false);
  }
  async function savePost(payload, id){
    try{
      const res = id ? await API.put(`/posts/${id}`, payload) : await API.post('/posts', payload);
      setPosts(id ? posts.map(p=>p.id===id?res.data:p) : [...posts, res.data]);
      setToast(id ? 'Post updated' : 'Post added to queue');
      setModalDate(null); setEditPost(null);
    } catch { setToast('Could not save post'); }
  }
  async function del(id){ try{ await API.delete(`/posts/${id}`); setPosts(posts.filter(p=>p.id!==id)); setToast('Post deleted'); }catch{setToast('Could not delete post')} }
  async function scorePosts(){
    const missing = posts.filter(p=>!aiScores[p.id]).slice(0, 20);
    if(!missing.length) return;
    const next={...aiScores};
    await Promise.all(missing.map(async p=>{
      try{
        const d=new Date(p.scheduled_at);
        const r=await API.post('/ai/predict', { platform:p.platform, post_type:p.post_type || 'image', post_day:d.toLocaleDateString('en',{weekday:'long'}), hour:d.getHours(), occasion:p.occasion || 'General', content:p.content || '', media_score:p.media_score || null });
        next[p.id]=r.data;
      }catch{ next[p.id]={ai_score:'--', score_label:'Needs data'}; }
    }));
    setAiScores(next);
  }
  async function movePost(post, newStatus){
    if(post.status === newStatus) return;
    const previous = posts;
    const updated = {...post, status:newStatus};
    setPosts(posts.map(p=>p.id===post.id?updated:p));
    try{ await API.patch(`/posts/${post.id}/status`, { status:newStatus }); setToast(`Moved to ${newStatus}`); }
    catch{ setPosts(previous); setToast('Could not update status'); }
  }
  const filtered = posts.filter(p => (p.title+p.platform+p.content+(p.location||'')+(p.occasion||'')).toLowerCase().includes(query.toLowerCase()));
  const upcoming = filtered.filter(p=>(p.status||'Scheduled')!=='Posted').sort((a,b)=>new Date(a.scheduled_at)-new Date(b.scheduled_at));
  const grouped = WORKFLOW_COLUMNS.reduce((acc,c)=>({...acc,[c.key]: filtered.filter(p=>(p.status||'Scheduled')===c.key)}),{});
  const totals = { total: filtered.length, scheduled: grouped.Scheduled.length, active: grouped.Drafting.length + grouped.Ready.length, posted: grouped.Posted.length };
  const aiText=(p)=>{ const ai=aiScores[p.id]; if(!ai) return 'checking'; return `${ai.ai_score ?? ai.predicted_engagement}/100 • ${ai.score_label || ai.confidence || 'AI'}`; };
  return <main className="main workflow-main simple-main"><PageHead title="Queue">
    <div className="search"><Search size={15}/><input placeholder="Search posts" value={query} onChange={e=>setQuery(e.target.value)} /></div>
    <button className="primary" onClick={()=>setModalDate(new Date())}>+ New Post</button>
  </PageHead>
    <section className="queue-hero panel">
      <div><h2>Plan posts without clutter</h2><p>Queue is your main working page. Use Board when you need lifecycle tracking.</p></div>
      <div className="workflow-stats"><span><b>{totals.total}</b>Total</span><span><b>{totals.scheduled}</b>Scheduled</span><span><b>{totals.active}</b>In progress</span><span><b>{totals.posted}</b>Posted</span></div>
    </section>
    <div className="workflow-controls simple-controls"><select value={platform} onChange={e=>setPlatform(e.target.value)}><option>All</option>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select><div className="segmented"><button className={mode==='queue'?'active':''} onClick={()=>setMode('queue')}>Queue</button><button className={mode==='board'?'active':''} onClick={()=>setMode('board')}>Board</button><button className={mode==='posts'?'active':''} onClick={()=>setMode('posts')}>All Posts</button></div><button onClick={load}><RotateCcw size={15}/> Refresh</button></div>
    {loading ? <div className="panel">Loading queue...</div> : mode==='queue' ? <section className="queue-list">
      {upcoming.map(post=><article className="queue-item" key={post.id} onDoubleClick={()=>setEditPost(post)}>
        <div className="queue-time"><strong>{fmtTime(post.scheduled_at)}</strong><span>{fmtDate(post.scheduled_at)}</span></div>
        <div className="queue-body"><div className="queue-title"><h3>{post.title}</h3><span className={`platform-dot ${post.platform.toLowerCase()}`}>{post.platform}</span></div><p>{post.content || 'No caption added yet.'}</p><div className="queue-meta"><span><MapPin size={13}/>{post.location || 'Online'}</span><span><Tag size={13}/>{post.occasion || 'General'}</span><span><Sparkles size={13}/>{aiText(post)}</span></div></div>
        {post.media_url && <img src={mediaSrc(post.media_url)} className="queue-thumb"/>}
        <div className="mini-actions"><button onClick={()=>setEditPost(post)}><Pencil size={15}/></button><button onClick={()=>movePost(post,'Posted')}><CheckCircle2 size={15}/></button></div>
      </article>)}
      {!upcoming.length && <div className="panel empty">No queued posts yet. Click + New Post to add one.</div>}
    </section> : mode==='posts' ? <section className="posts-grid compact-posts">
      {filtered.map(post=><article className="post-card" key={post.id}><div className="post-card-top"><span className={`platform-dot ${post.platform.toLowerCase()}`}>{post.platform}</span><span className={`status-badge ${(post.status||'Scheduled').toLowerCase()}`}>{post.status}</span></div>{post.media_url && <img src={mediaSrc(post.media_url)} className="post-thumb"/>}<h3>{post.title}</h3><p>{post.content || 'No content yet.'}</p><div className="meta"><span><Clock3 size={14}/>{fmtDate(post.scheduled_at)} {fmtTime(post.scheduled_at)}</span><span><MapPin size={14}/>{post.location}</span><span><Tag size={14}/>{post.occasion}</span><span><Sparkles size={14}/>{aiText(post)}</span></div><div className="mini-actions"><button onClick={()=>setEditPost(post)}><Pencil size={15}/> Edit</button><button onClick={()=>del(post.id)}><Trash2 size={15}/> Delete</button></div></article>)}
    </section> : <section className="kanban-board clean-kanban">
      {WORKFLOW_COLUMNS.map(col=><div className="kanban-column" key={col.key} onDragOver={e=>e.preventDefault()} onDrop={()=>{ const post=posts.find(p=>p.id===dragId); if(post) movePost(post,col.key); setDragId(null); }}>
        <div className="kanban-head"><div><h3>{col.label}</h3><p>{col.hint}</p></div><strong>{grouped[col.key].length}</strong></div>
        <div className="kanban-list">
          {grouped[col.key].map(post=>{ const ai=aiScores[post.id]; return <article className={`kanban-card ${post.platform.toLowerCase()}`} key={post.id} draggable onDragStart={()=>setDragId(post.id)} onDragEnd={()=>setDragId(null)} onDoubleClick={()=>setEditPost(post)}>
            <div className="card-grip"><GripVertical size={16}/><span>{post.platform}</span></div><h4>{post.title}</h4><p>{post.content || 'No content added yet.'}</p>
            <div className="meta-row"><span><Clock3 size={13}/>{fmtDate(post.scheduled_at)} • {fmtTime(post.scheduled_at)}</span><span><MapPin size={13}/>{post.location || 'Online'}</span></div>
            <div className="ai-score quiet-score"><Sparkles size={14}/><span>Post score</span><b>{ai ? `${ai.ai_score || ai.predicted_engagement}/100` : '...'}</b><em>{ai ? (ai.score_label || ai.confidence) : 'checking'}</em></div>
            <div className="move-row">{WORKFLOW_COLUMNS.filter(c=>c.key!==post.status).slice(0,2).map(c=><button key={c.key} onClick={()=>movePost(post,c.key)}><ArrowRightCircle size={13}/>{c.key}</button>)}</div>
          </article>})}
          {!grouped[col.key].length && <div className="empty-column">Drop posts here</div>}
        </div>
      </div>)}
    </section>}
    <PostModal open={!!modalDate || !!editPost} onClose={()=>{setModalDate(null);setEditPost(null)}} selectedDate={modalDate} editPost={editPost} onSave={savePost}/>
  </main>
}



async function startInstagramOAuth() {
  try {
    const res = await fetch(`${API_BASE}/oauth/meta/config`);
    const cfg = await res.json();
    if (!cfg.configured) {
      alert('Add META_APP_ID in backend/.env and restart backend.');
      return;
    }
    window.location.href = `${API_BASE}/oauth/meta/start`;
  } catch {
    alert('Start the backend first.');
  }
}

function AccountModal({ open, onClose, onCreate }) {
  const [form, setForm] = useState({ platform: 'Instagram', name: '', access_token: '' });
  useEffect(()=>{ if(open) setForm({ platform:'Instagram', name:'', access_token:'' }) },[open]);
  if (!open) return null;
  async function submit(e){ e.preventDefault(); if(!form.name.trim()) return; await onCreate(form); }
  return <div className="overlay" onMouseDown={onClose}><form className="modal small connect-modal" onMouseDown={e=>e.stopPropagation()} onSubmit={submit}>
    <div className="modal-head"><h2>Connect Channel</h2><button type="button" onClick={onClose}><X size={18}/></button></div>
    <div className="oauth-card">
      <div><strong>Instagram / Facebook OAuth</strong><p>Connect a professional account with Meta OAuth.</p></div>
      <button type="button" className="primary oauth-btn" onClick={startInstagramOAuth}>Connect Instagram</button>
    </div>
    <div className="divider"><span>Connect another way</span></div>
    <label>Platform<select value={form.platform} onChange={e=>setForm({...form, platform:e.target.value})}>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select></label>
    <label>Account name<input value={form.name} onChange={e=>setForm({...form, name:e.target.value})} placeholder="Example: Aum Creations" autoFocus /></label>
    <label>Token <span className="field-hint"></span><input type="password" value={form.access_token} onChange={e=>setForm({...form, access_token:e.target.value})} placeholder="Optional access token" /></label>
    <div className="security-box"><ShieldCheck size={16}/> </div>
    <div className="actions"><button type="button" onClick={onClose}>Cancel</button><button className="primary">Save Channel</button></div>
  </form></div>
}

function CreateAccountPage({ onCreate, setActive }) {
  const [form, setForm] = useState({ platform: 'Instagram', name: '', access_token: '' });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  async function submit(e) {
    e.preventDefault();
    if (!form.name.trim()) return setMessage('Please enter an account name.');
    setSaving(true); setMessage('');
    try {
      await onCreate(form, false);
      setMessage('Channel saved.');
      setForm({ platform: 'Instagram', name: '', access_token: '' });
    } catch { setMessage('Could not connect channel. Check backend is running.'); }
    setSaving(false);
  }
  return <main className="main"><PageHead title="Connect Channel"/>
    <div className="create-account-page connect-page">
      <section className="panel create-panel">
        <div className="form-title"><UserPlus size={24}/><div><h2>Connect a real channel</h2><p>Use OAuth for Instagram/Facebook. This is the safer and professional way to connect multiple accounts.</p></div></div>
        <div className="oauth-card large">
          <div><strong>Instagram / Facebook</strong><p>Redirects to Meta login. Add META_APP_ID and META_APP_SECRET in backend .env before real testing.</p></div>
          <button type="button" className="primary oauth-btn" onClick={startInstagramOAuth}>Connect Instagram</button>
        </div>
        <div className="divider"><span>Connect another way</span></div>
        <form onSubmit={submit}>
          <label>Platform<select value={form.platform} onChange={e=>setForm({...form, platform:e.target.value})}>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select></label>
          <label>Account / page name<input value={form.name} onChange={e=>setForm({...form, name:e.target.value})} placeholder="Example: Aum Creations Instagram" /></label>
          <label>Token <span className="field-hint">optional, </span><input type="password" value={form.access_token} onChange={e=>setForm({...form, access_token:e.target.value})} placeholder="Paste token only for testing" /></label>
          <div className="security-box"><ShieldCheck size={16}/> </div>
          {message && <div className="notice">{message}</div>}
          <div className="actions"><button type="button" onClick={()=>setActive('accounts')}>View Channels</button><button className="primary" disabled={saving}>{saving ? 'Saving...' : 'Save Channel'}</button></div>
        </form>
      </section>
      
    </div>
  </main>
}
function Creator({ setToast }) { 
  const [topic,setTopic]=useState('bridal collection'); 
  const [ideas,setIdeas]=useState([]); 
  const [aiForm,setAiForm]=useState({platform:'Instagram', post_type:'image', post_day:'Friday', occasion:'Launch'});
  const [prediction,setPrediction]=useState(null);
  async function gen(){ try{ const r=await API.post('/ai/ideas',{topic}); setIdeas(r.data.ideas); setToast('Ideas generated'); }catch{ setToast('Could not generate ideas'); } }
  async function predict(){ try{ const r=await API.post('/ai/best-time', aiForm); setPrediction(r.data); setToast('AI schedule suggestion ready'); }catch{ setToast('Could not run AI predictor'); } }
  return <main className="main"><PageHead title="Create"/><div className="ai-grid"><div className="panel"><h2>Generate content ideas</h2><div className="inline"><input value={topic} onChange={e=>setTopic(e.target.value)}/><button className="primary" onClick={gen}><Sparkles size={16}/> Generate</button></div><div className="cards">{ideas.map((x,i)=><div className="card" key={i}>{x}</div>)}</div></div><div className="panel"><h2>AI Best Time Predictor</h2><p className="muted-text">Uses your Kaggle social media engagement dataset from the backend.</p><div className="two"><label>Platform<select value={aiForm.platform} onChange={e=>setAiForm({...aiForm,platform:e.target.value})}>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select></label><label>Post type<select value={aiForm.post_type} onChange={e=>setAiForm({...aiForm,post_type:e.target.value})}>{POST_TYPES.map(p=><option key={p}>{p}</option>)}</select></label></div><div className="two"><label>Day<select value={aiForm.post_day} onChange={e=>setAiForm({...aiForm,post_day:e.target.value})}>{['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map(d=><option key={d}>{d}</option>)}</select></label><label>Occasion<input value={aiForm.occasion} onChange={e=>setAiForm({...aiForm,occasion:e.target.value})}/></label></div><button className="primary" onClick={predict}><Sparkles size={16}/> Predict Best Time</button>{prediction && <div className="ai-result big-result"><strong>{prediction.best_time}</strong><span>Predicted engagement: {prediction.predicted_engagement}</span><small>Confidence: {prediction.confidence} • Training rows: {prediction.training_rows}</small><em>{prediction.hashtags?.join(' ')}</em></div>}</div></div></main> }
function Analytics(){
  const [data,setData]=useState(null);
  const [insights,setInsights]=useState(null);
  const [loading,setLoading]=useState(true);
  useEffect(()=>{ Promise.allSettled([API.get('/analytics/summary'), API.get('/ai/insights')]).then(([a,b])=>{ if(a.status==='fulfilled') setData(a.value.data); if(b.status==='fulfilled') setInsights(b.value.data); }).finally(()=>setLoading(false)); },[]);
  const cards=data?.cards||{};
  const pretty=(k)=>k.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
  return <main className="main analytics-simple"><PageHead title="Analytics"/>
    {loading && <div className="panel">Loading analytics...</div>}
    {!loading && !data && <div className="panel">Could not load analytics. Check backend is running.</div>}
    {data && <>
      <div className="analytics-hero panel clean-analytics-hero">
        <div><h2>Performance at a glance</h2><p>{data.message}</p></div>
        <div className="model-badge"><Sparkles size={16}/> AI trained on {cards.training_rows} rows</div>
      </div>
      <div className="stat-grid ai-stats simple-stats">
        {Object.entries(cards).filter(([k])=>!['training_rows'].includes(k)).map(([k,v])=><div className="stat" key={k}><span>{pretty(k)}</span><strong>{String(v)}</strong></div>)}
      </div>
      {insights && <section className="panel insight-main merged-insights"><div className="insight-title"><Lightbulb size={23}/><div><h2>AI recommendations</h2><p>Short suggestions based on the trained engagement dataset.</p></div></div><div className="recommend-list compact-recommendations">{insights.recommendations.slice(0,4).map((r,i)=><div className="recommend-card" key={r}><b>{i+1}</b><span>{r}</span></div>)}</div></section>}
      <div className="analytics-grid">
        <section className="panel"><h2>Best platforms</h2><div className="rank-list">{data.dataset.platform_breakdown.map((r,i)=><div className="rank-row" key={r.name}><b>#{i+1}</b><span>{r.name}</span><em>{r.avg_engagement} avg</em><small>{r.rows} samples</small></div>)}</div></section>
        <section className="panel"><h2>Best content types</h2><div className="rank-list">{data.dataset.post_type_breakdown.map((r,i)=><div className="rank-row" key={r.name}><b>#{i+1}</b><span>{r.name}</span><em>{r.avg_engagement} avg</em><small>{r.rows} samples</small></div>)}</div></section>
        <section className="panel"><h2>Top posting times</h2><div className="rank-list">{data.dataset.top_times.map((r,i)=><div className="rank-row" key={r.time}><b>#{i+1}</b><span>{r.time}</span><em>{r.avg_engagement} avg</em><small>{r.rows} samples</small></div>)}</div></section>
        <section className="panel"><h2>Your app activity</h2><div className="activity-list"><p><ListChecks size={16}/> Total posts: <b>{data.app.total_posts}</b></p><p><Clock3 size={16}/> Scheduled: <b>{data.app.scheduled}</b></p><p><Tag size={16}/> Drafts: <b>{data.app.drafts}</b></p><p><CheckCircle2 size={16}/> Posted: <b>{data.app.posted}</b></p><p><Users size={16}/> Connected channels: <b>{data.app.connected_accounts}</b></p></div></section>
      </div>
    </>}
  </main>
}

function Insights(){
  const [data,setData]=useState(null);
  const [loading,setLoading]=useState(true);
  useEffect(()=>{API.get('/ai/insights').then(r=>setData(r.data)).catch(()=>setData(null)).finally(()=>setLoading(false))},[]);
  return <main className="main"><PageHead title="AI Insights"/>
    {loading && <div className="panel">Generating AI insights from trained dataset...</div>}
    {!loading && !data && <div className="panel">Could not load AI insights. Check backend is running.</div>}
    {data && <div className="insights-layout">
      <section className="panel insight-main">
        <div className="insight-title"><Sparkles size={24}/><div><h2>Recommendations</h2><p>Generated from your Kaggle engagement dataset and current scheduler data.</p></div></div>
        <div className="recommend-list">{data.recommendations.map((r,i)=><div className="recommend-card" key={r}><b>{i+1}</b><span>{r}</span></div>)}</div>
      </section>
      <section className="panel insight-score">
        <h2>AI best strategy</h2>
        <div className="strategy-grid"><div><span>Platform</span><strong>{data.best_platform.name}</strong><em>{data.best_platform.avg_engagement} avg engagement</em></div><div><span>Post type</span><strong>{data.best_post_type.name}</strong><em>{data.best_post_type.avg_engagement} avg engagement</em></div><div><span>Time</span><strong>{data.best_time.time}</strong><em>{data.best_time.avg_engagement} avg engagement</em></div></div>
        <p className="muted-text">Model: {data.model} • Training rows: {data.training_rows}</p>
      </section>
      <section className="panel"><h2>Best posting windows</h2><div className="rank-list">{data.top_times.map((t,i)=><div className="rank-row" key={t.time}><b>#{i+1}</b><span>{t.time}</span><em>{t.avg_engagement} avg engagement</em><small>{t.rows} samples</small></div>)}</div></section>
      <section className="panel"><h2>Warnings / accuracy notes</h2>{data.risks.length ? data.risks.map(r=><p className="warning-line" key={r}>⚠️ {r}</p>) : <p>No major warnings. Keep adding real posted results to improve accuracy.</p>}</section>
    </div>}
  </main>
}
function Accounts({ accounts,setAccounts,setToast }){ const [edit,setEdit]=useState(null); async function remove(id){ try{await API.delete(`/accounts/${id}`); setAccounts(accounts.filter(a=>a.id!==id)); setToast('Account removed'); }catch{ setToast('Could not remove account'); } } async function save(e){e.preventDefault(); try{const r=await API.put(`/accounts/${edit.id}`, edit); setAccounts(accounts.map(a=>a.id===edit.id?r.data:a)); setEdit(null); setToast('Account updated')}catch{setToast('Could not update account')}} return <main className="main"><PageHead title="Channels"/><div className="cards">{accounts.map(a=><div className="card account" key={a.id}><div><strong>{a.name}</strong><span>{a.platform} • {a.status}</span><em>{a.token_saved ? 'Token: saved, hidden' : 'Token: not saved'}</em></div><div className="mini-actions"><button onClick={()=>setEdit({...a, access_token:''})}><Pencil size={16}/></button><button onClick={()=>remove(a.id)}><Trash2 size={16}/></button></div></div>)}</div>{edit&&<div className="overlay" onMouseDown={()=>setEdit(null)}><form className="modal small" onMouseDown={e=>e.stopPropagation()} onSubmit={save}><div className="modal-head"><h2>Edit Account</h2><button type="button" onClick={()=>setEdit(null)}><X size={18}/></button></div><label>Name<input value={edit.name} onChange={e=>setEdit({...edit,name:e.target.value})}/></label><label>Platform<select value={edit.platform} onChange={e=>setEdit({...edit,platform:e.target.value})}>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select></label><label>Status<select value={edit.status} onChange={e=>setEdit({...edit,status:e.target.value})}><option>Connected</option><option>Needs Attention</option><option>Paused</option></select></label><label>Replace token<input type="password" value={edit.access_token} onChange={e=>setEdit({...edit,access_token:e.target.value})} placeholder="Leave blank to keep old token"/></label><div className="actions"><button type="button" onClick={()=>setEdit(null)}>Cancel</button><button className="primary">Save</button></div></form></div>}</main> }
function Notifications(){ return <main className="main"><PageHead title="Notifications"/><div className="panel"><p>No urgent notifications. Scheduled posts are ready.</p></div></main> }
function SettingsPage({ setToast }){ const [form,setForm]=useState({brand_name:'SocialMedia AI',default_platform:'Instagram',default_time:'10:00',theme:'dark',notifications:true}); useEffect(()=>{API.get('/settings').then(r=>setForm(r.data)).catch(()=>{})},[]); async function save(e){e.preventDefault(); try{await API.put('/settings',form); document.body.classList.toggle('light', form.theme==='light'); setToast('Settings saved')}catch{setToast('Could not save settings')}} return <main className="main"><PageHead title="Settings"/><form className="panel settings-form" onSubmit={save}><label>Brand name<input value={form.brand_name} onChange={e=>setForm({...form,brand_name:e.target.value})}/></label><label>Default platform<select value={form.default_platform} onChange={e=>setForm({...form,default_platform:e.target.value})}>{PLATFORMS.map(p=><option key={p}>{p}</option>)}</select></label><label>Default posting time<input type="time" value={form.default_time} onChange={e=>setForm({...form,default_time:e.target.value})}/></label><label>Theme<select value={form.theme} onChange={e=>setForm({...form,theme:e.target.value})}><option value="dark">Dark</option><option value="light">Light</option></select></label><label className="check"><input type="checkbox" checked={form.notifications} onChange={e=>setForm({...form,notifications:e.target.checked})}/> Enable notifications</label><button className="primary">Save Settings</button></form></main> }

function App() {
  const [user,setUser]=useState(()=>{ try{return JSON.parse(localStorage.getItem('sm_user'))}catch{return null} });
  const [active,setActive]=useState('calendar'); const [query,setQuery]=useState(''); const [posts,setPosts]=useState([]); const [accounts,setAccounts]=useState([]); const [accountOpen,setAccountOpen]=useState(false); const [toast,setToast]=useState('');
  function logout(){ localStorage.removeItem('sm_token'); localStorage.removeItem('sm_user'); setUser(null); }
  useEffect(()=>{ const f=()=>setAccountOpen(true); const lo=()=>logout(); window.addEventListener('open-account',f); window.addEventListener('force-logout',lo); return()=>{window.removeEventListener('open-account',f); window.removeEventListener('force-logout',lo)} },[]);
  useEffect(()=>{ if(user) API.get('/accounts').then(r=>setAccounts(r.data)).catch(()=>setToast('Could not load accounts')); },[user]);
  useEffect(()=>{ if(toast){ const t=setTimeout(()=>setToast(''),1800); return()=>clearTimeout(t)} },[toast]);
  async function createAccount(payload, closeModal=true){ const r=await API.post('/accounts',payload); setAccounts(prev=>[...prev,r.data]); if(closeModal) setAccountOpen(false); setToast('Account connected securely'); return r.data; }
  if(!user) return <><LoginPage onLogin={setUser}/><Toast message={toast}/></>;
  return <div className="app"><Sidebar active={active} setActive={setActive} onLogout={logout}/>{active==='calendar'&&<ContentCalendar query={query} setQuery={setQuery} posts={posts} setPosts={setPosts} setToast={setToast}/>} {active==='preview'&&<PreviewPage setToast={setToast}/>} {active==='workflow'&&<WorkflowBoard query={query} setQuery={setQuery} posts={posts} setPosts={setPosts} setToast={setToast}/>} {active==='posts'&&<PostsPage query={query} setQuery={setQuery} posts={posts} setPosts={setPosts} setToast={setToast}/>} {active==='creator'&&<Creator setToast={setToast}/>} {active==='createAccount'&&<CreateAccountPage onCreate={createAccount} setActive={setActive}/>} {active==='analytics'&&<Analytics/>} {active==='insights'&&<Insights/>} {active==='accounts'&&<Accounts accounts={accounts} setAccounts={setAccounts} setToast={setToast}/>} {active==='notifications'&&<Notifications/>} {active==='settings'&&<SettingsPage setToast={setToast}/>}<AccountModal open={accountOpen} onClose={()=>setAccountOpen(false)} onCreate={createAccount}/><Toast message={toast}/></div>
}

createRoot(document.getElementById('root')).render(<App />);
