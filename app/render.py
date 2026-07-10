"""STEP 5 (render) - ported from spec/.../build_artifact.py.

Same CSS/markup/JS as the original (single self-contained page, client-side streak
+ per-day "worked" tracking in localStorage), refactored into a pure function:

    render_html(page: PageData, streak: int) -> str

Two intentional additions over the original, both required by the brief:
  1. A red verification badge on every contact whose status is not
     LINKEDIN_VERIFIED ("NOT LINKEDIN-VERIFIED - confirm before outreach") plus a
     one-click LinkedIn link. No contact is ever shown as clean-active.
  2. The dormancy label reflects the engine's 30-day guard.

The data.json contract is unchanged (build_artifact.py could still render it); the
new fields (verif_status/verif_label) are additive.
"""
from __future__ import annotations

import json

from .models import PageData

# NOTE: kept as a plain string (not an f-string) because the body is full of { } JS.
_TEMPLATE = r"""<!doctype html><meta charset="utf-8">
<style>
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#f6f7f9;color:#16181d}
.wrap{max-width:1100px;margin:0 auto;padding:18px 18px 60px}
.top{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:6px}
.h1{font-size:22px;font-weight:800;letter-spacing:-.3px}
.sub{color:#646b76;font-size:13px;margin-top:2px}
.stats{display:flex;gap:10px;align-items:center}
.chip{background:#fff;border:1px solid #e6e8ec;border-radius:999px;padding:8px 14px;font-weight:700;font-size:13px;display:flex;gap:7px;align-items:center;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.flame{filter:saturate(1.2)}
.ring{--p:0;width:46px;height:46px;border-radius:50%;background:conic-gradient(#16a34a calc(var(--p)*1%),#e6e8ec 0);display:grid;place-items:center}
.ring i{width:36px;height:36px;border-radius:50%;background:#fff;display:grid;place-items:center;font-style:normal;font-weight:800;font-size:12px;color:#16181d}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:18px}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
.bubble{position:relative;background:#fff;border:1px solid #e6e8ec;border-radius:20px;padding:20px;cursor:pointer;transition:transform .12s ease,box-shadow .12s ease,border-color .12s;overflow:hidden;min-height:188px;display:flex;flex-direction:column;justify-content:space-between}
.bubble:hover{transform:translateY(-4px);box-shadow:0 14px 30px rgba(20,24,29,.10);border-color:#cdd2da}
.bubble.done{border-color:#16a34a;background:linear-gradient(180deg,#f1fbf4,#fff)}
.bubble .glow{position:absolute;right:-40px;top:-40px;width:130px;height:130px;border-radius:50%;background:radial-gradient(circle,rgba(99,102,241,.16),transparent 70%)}
.vtag{display:inline-block;font-size:11px;font-weight:700;color:#5b21b6;background:#efe9ff;padding:4px 9px;border-radius:999px}
.mtag{display:inline-block;font-size:11px;font-weight:800;color:#065f46;background:#d1fae5;border:1px solid #a7f3d0;padding:3px 9px;border-radius:999px;margin-left:6px}
.bname{font-size:19px;font-weight:800;margin:12px 0 4px}
.bmeta{font-size:12.5px;color:#646b76;line-height:1.5}
.dorm{margin-top:10px;font-size:12px;font-weight:700;color:#b45309;background:#fff6e8;border:1px solid #fde9c8;padding:6px 10px;border-radius:10px;display:inline-block}
.bopen{margin-top:14px;font-size:13px;font-weight:800;color:#4f46e5}
.donebadge{position:absolute;top:14px;right:14px;font-size:12px;font-weight:800;color:#16a34a;display:none}
.bubble.done .donebadge{display:block}
.bubble.fb{background:#fffbeb;border-color:#fde68a}
.bubble.fb:hover{border-color:#fbbf24}
.fbwarn{margin-top:10px;font-size:12px;font-weight:800;color:#92400e;background:#fef3c7;border:1px solid #fde68a;padding:6px 10px;border-radius:10px;display:inline-block}
.fbbanner{margin:14px 0;font-size:14px;font-weight:700;color:#92400e;background:#fef3c7;border:1px solid #fbbf24;padding:12px 14px;border-radius:12px}
.bubble.done .bopen{color:#16a34a}
.detail{display:none;margin-top:10px}
.back{background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:8px 14px;font-weight:700;cursor:pointer;font-size:13px}
.dhead{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;margin:14px 0}
.dname{font-size:24px;font-weight:850;letter-spacing:-.3px}
.dlinks{font-size:13px;margin-top:6px}
.dlinks a{color:#4f46e5;text-decoration:none;font-weight:700}
.recon{background:#eef2ff;border:1px solid #dfe4ff;color:#312e81;border-radius:12px;padding:10px 14px;font-size:13px;margin:6px 0 12px;font-weight:600}
.card{background:#fff;border:1px solid #e6e8ec;border-radius:16px;padding:18px;margin:14px 0}
.ov{font-size:14px;line-height:1.62;color:#2b2f37;white-space:pre-wrap}
.flag{margin-top:12px;background:#fff8ed;border:1px solid #fde9c8;border-radius:10px;padding:10px 13px;font-size:13px;color:#92400e}
.tier{font-size:13px;font-weight:850;letter-spacing:.4px;color:#646b76;margin:22px 0 4px;text-transform:uppercase}
.ct{border:1px solid #e6e8ec;border-radius:16px;padding:16px;margin:12px 0;background:#fff}
.cn{font-size:17px;font-weight:800}
.cn a{color:#0a66c2;text-decoration:none}
.crole{color:#646b76;font-size:13px;font-weight:600}
.cmeta{font-size:12.5px;color:#4b515b;margin-top:8px;line-height:1.6}
.warnflag{color:#b91c1c;font-weight:700}
.verif{margin-top:10px;background:#fee2e2;border:1px solid #fecaca;color:#b91c1c;border-radius:10px;padding:8px 11px;font-size:12.5px;font-weight:800;line-height:1.5}
.verif a{color:#b91c1c;text-decoration:underline}
.verif.held{background:#fef2f2;border-color:#f87171}
.verif.ok{background:#dcfce7;border-color:#86efac;color:#166534}
.verif.ok a{color:#166534}
.vbtn{margin-left:8px;font-size:11px;font-weight:800;border:1px solid currentColor;background:transparent;color:inherit;border-radius:999px;padding:2px 10px;cursor:pointer}
.vbtn.undo{font-weight:700;opacity:.8}
.srcbox{margin:12px 0 4px;background:#f0f7ff;border:1px solid #cfe3ff;border-radius:12px;padding:12px 14px}
.srch{font-size:13px;font-weight:800;color:#1e40af;margin-bottom:8px}
.srclinks{display:flex;flex-wrap:wrap;gap:8px}
.src{font-size:12px;font-weight:700;color:#0a66c2;background:#fff;border:1px solid #cfe3ff;border-radius:999px;padding:5px 11px;text-decoration:none}
.srcnote{font-size:11px;color:#5b6472;margin-top:8px}
.emails{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
@media(max-width:680px){.emails{grid-template-columns:1fr}}
.em{border:1px solid #e9ebef;border-radius:12px;padding:13px;background:#fafbfc}
.emh{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px}
.emtag{font-size:11px;font-weight:800;color:#3730a3;background:#e7e9ff;padding:3px 8px;border-radius:6px}
.emsub{font-size:12px;color:#646b76;margin-bottom:8px}
.emsub b{color:#16181d}
.embody{font-size:13px;line-height:1.55;color:#23272e;white-space:pre-wrap}
.copy{border:1px solid #d7dae0;background:#fff;border-radius:8px;padding:4px 10px;font-size:12px;font-weight:700;cursor:pointer}
.copy:hover{background:#f1f2f4}
.copy.ok{background:#16a34a;color:#fff;border-color:#16a34a}
.markbar{margin-top:18px;display:flex;gap:10px;align-items:center}
.mark{background:#4f46e5;color:#fff;border:none;border-radius:10px;padding:11px 18px;font-weight:800;cursor:pointer;font-size:14px}
.mark:hover{background:#4338ca}
.mark.done{background:#16a34a}
.toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(40px);background:#16181d;color:#fff;padding:12px 20px;border-radius:12px;font-weight:700;opacity:0;transition:all .3s;z-index:50}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.note{font-size:12px;color:#878d96;margin-top:26px;text-align:center;line-height:1.6}
.empty{background:#fff;border:1px dashed #cdd2da;border-radius:16px;padding:40px;text-align:center;color:#646b76}
</style>
<div class="wrap">
  <div id="home">
    <div class="top">
      <div>
        <div class="h1">Daily Re-Engagement &mdash; 3 to reopen</div>
        <div class="sub">__DATE__ &middot; __REPNAME__ &middot; dormant 30+ days &middot; no open deal &middot; your book (owner or ADR)</div>
      </div>
      <div class="stats">
        <div class="chip"><span class="flame">&#128293;</span><span id="streak">__STREAK__ day streak</span></div>
        <div class="ring" id="ring"><i id="ringtxt">0/3</i></div>
      </div>
    </div>
    <div class="grid" id="grid"></div>
    <div class="note">Each weekday at 7:00 this refreshes with newly-surfaced dormant accounts, researched with verification-flagged contacts and A/B emails. Click a bubble to open the full run. Drafts only &mdash; you enroll. Every contact must be confirmed on LinkedIn before outreach.</div>
  </div>
  <div class="detail" id="detail"></div>
</div>
<div class="toast" id="toast"></div>
<script>
const DATA=__DATA__;
const DAY="__DATE__";
const KEY="dpe_worked_"+DAY;
function worked(){try{return JSON.parse(localStorage.getItem(KEY)||"[]")}catch(e){return[]}}
function setWorked(a){localStorage.setItem(KEY,JSON.stringify(a))}
const VKEY="dpe_verified";
function verifiedSet(){try{return JSON.parse(localStorage.getItem(VKEY)||"[]")}catch(e){return[]}}
function isVerified(k){return verifiedSet().includes(k)}
function setVerified(k,on){let a=verifiedSet();if(on){if(!a.includes(k))a.push(k)}else{a=a.filter(x=>x!==k)}localStorage.setItem(VKEY,JSON.stringify(a))}
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function liPeople(q){return "https://www.linkedin.com/search/results/people/?keywords="+encodeURIComponent(q)}
function isFB(c){return /food\s*(&|and)?\s*beverage/i.test(c&&c.vertical||"")}
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),1700)}
const SKEY="dpe_streak";
function getStreak(){try{return JSON.parse(localStorage.getItem(SKEY)||'{"count":0,"last":null}')}catch(e){return{count:0,last:null}}}
function prevWeekday(ds){let x=new Date(ds+"T00:00:00");do{x.setDate(x.getDate()-1)}while(x.getDay()===0||x.getDay()===6);return x.toISOString().slice(0,10)}
function liveStreak(){const s=getStreak();if(!s.last)return 0;if(s.last===DAY||s.last===prevWeekday(DAY))return s.count;return 0}
function renderStreak(){const n=liveStreak();document.getElementById('streak').textContent=n+" day streak"}
function completeDay(){const s=getStreak();if(s.last===DAY)return;const cont=(s.last&&s.last===prevWeekday(DAY));const count=cont?(s.count||0)+1:1;localStorage.setItem(SKEY,JSON.stringify({count,last:DAY}));renderStreak()}
function updRing(){const w=worked().length,n=DATA.companies.length||1;const r=document.getElementById('ring');r.style.setProperty('--p',Math.round(w/n*100));document.getElementById('ringtxt').textContent=w+"/"+DATA.companies.length;if(DATA.companies.length&&w===DATA.companies.length){completeDay();toast("All worked. Streak +1. 🔥")}renderStreak()}
function grid(){
  const g=document.getElementById('grid');g.innerHTML="";
  if(!DATA.companies.length){g.innerHTML='<div class="empty">No eligible dormant accounts to surface today. The pool may be exhausted, or everything is recently contacted / has an open deal.</div>';renderStreak();return}
  DATA.companies.forEach((c,i)=>{
    const done=worked().includes(c.id);
    const fb=isFB(c);
    const d=document.createElement('div');d.className="bubble"+(done?" done":"")+(fb?" fb":"");
    const since=c.last_touch?("Dormant since "+esc((c.last_touch||'').split(' ')[0])):"Never contacted";
    d.innerHTML=`<div class="glow"></div><div class="donebadge">&#10003; reopened</div>
      <div><span class="vtag">${esc(c.vertical)}</span>${c.manual?'<span class="mtag">+ Added by you</span>':''}
      <div class="bname">${esc(c.name)}</div>
      <div class="bmeta">${esc(c.domain)} &middot; ${esc(c.status)}</div>
      <div class="dorm">${since}</div>
      ${fb?'<div class="fbwarn">&#9888; Enhanced qualification required</div>':''}</div>
      <div class="bopen">Open full run &rarr;</div>`;
    d.onclick=()=>openCo(i);
    g.appendChild(d);
  });
  updRing();
}
function emailCard(tag,subj,body){
  const full="Subject: "+subj+"\n\n"+body+"\n\n"+DATA.signature;
  return `<div class="em"><div class="emh"><span class="emtag">EMAIL ${tag}</span>
    <button class="copy" data-c="${esc(full).replace(/"/g,'&quot;')}">Copy</button></div>
    <div class="emsub">Subject: <b>${esc(subj)}</b></div>
    <div class="embody">${esc(body)}\n\n${esc(DATA.signature)}</div></div>`;
}
function contact(c,coId){
  const li=`<a href="${esc(c.li)}" target="_blank" rel="noopener">${esc(c.name)}</a>`;
  const emailWarn=/NO EMAIL|BAD|INVALID|DUPLICATE|not found|pattern-guess/i.test(c.email_note||"")||c.email==="not found";
  const unverified=c.verif_status && c.verif_status!=='linkedin_verified';
  const held=c.verif_status==='held_out';
  const vk=(coId||'')+'|'+(c.id||c.name||'');
  const done=isVerified(vk);
  let verif='';
  if(done){
    verif=`<div class="verif ok">&#10003; You confirmed this person on LinkedIn &mdash; <a href="${esc(c.li)}" target="_blank" rel="noopener">re-open profile &#8599;</a> <button class="vbtn undo" data-vk="${esc(vk)}">undo</button></div>`;
  }else if(unverified){
    verif=`<div class="verif${held?' held':''}">&#9888; ${esc(c.verif_label)} &mdash; <a href="${esc(c.li)}" target="_blank" rel="noopener">confirm on LinkedIn &#8599;</a> ${held?'':`<button class="vbtn" data-vk="${esc(vk)}">Mark verified</button>`}</div>`;
  }
  let emails="";
  if(c.a_subj){emails=`<div class="emails">${emailCard('A',c.a_subj,c.a_body)}${emailCard('B',c.b_subj,c.b_body)}</div>`}
  let linkedin="";
  if(c.li_msg){linkedin=`<div class="em" style="margin-top:12px"><div class="emh"><span class="emtag" style="color:#0a66c2;background:#e7f0fa">LINKEDIN MESSAGE</span>
    <button class="copy" data-c="${esc(c.li_msg).replace(/"/g,'&quot;')}">Copy</button></div>
    <div class="embody">${esc(c.li_msg)}</div></div>`}
  return `<div class="ct">
    <div class="cn">${li} <span class="crole">&mdash; ${esc(c.title)}</span></div>
    ${c.local?`<div style="display:inline-block;margin-top:6px;font-size:11px;font-weight:800;color:#9a3412;background:#fff1e6;border:1px solid #fed7aa;padding:3px 9px;border-radius:999px">&#127869;&#65039; Denver-based &mdash; offer in-person lunch</div>`:''}
    ${verif}
    <div class="cmeta">
      <div class="${emailWarn?'warnflag':''}">Email: ${esc(c.email)} &nbsp;<span style="color:#878d96">(${esc(c.email_note)})</span></div>
      <div>Phone: ${esc(c.phone)}</div>
      <div>LinkedIn: <a href="${esc(c.li)}" target="_blank" rel="noopener" style="color:#0a66c2;font-weight:700">${esc(c.li)}</a> (verify)</div>
      <div>HubSpot: ${c.hub_url?`<a href="${esc(c.hub_url)}" target="_blank" rel="noopener" style="color:#4f46e5;font-weight:700">open contact record &#8599;</a>`:'no record link'}${c.hub?` <span style="color:#878d96">(${esc(c.hub)})</span>`:''}</div>
      ${c.verif_sources?`<div style="color:#878d96">Verification: ${esc(c.verif_sources)}</div>`:''}
    </div>${emails}${linkedin}</div>`;
}
function openCo(i){
  const c=DATA.companies[i];
  document.getElementById('home').style.display='none';
  const D=document.getElementById('detail');D.style.display='block';
  const tiers={T1:[],T2:[],T3:[]};c.contacts.forEach(x=>{(tiers[x.tier]||(tiers[x.tier]=[])).push(x)});
  let body=`<button class="back" onclick="closeCo()">&larr; Back to today's slate</button>
    <div class="dhead"><div>
      <div class="dname">${esc(c.name)}</div>
      <div class="dlinks">${esc(c.vertical)} &middot; ${esc(c.status)} &middot; <a href="${esc(c.hubspot)}" target="_blank" rel="noopener">Open in HubSpot &#8599;</a></div>
    </div></div>
    ${isFB(c)?`<div class="fbbanner">&#9888; Enhanced qualification required &mdash; this is a Food &amp; Beverage account.</div>`:''}
    ${c.reconnect_ok?`<div class="recon">&#128260; Warm reconnect &mdash; prior meeting/event on record: ${esc(c.last_touch)}</div>`:`<div class="recon" style="background:#f3f4f6;border-color:#e5e7eb;color:#374151">&#10003; Fresh outreach &mdash; dormant account, no meeting/event on record.${c.last_touch?(' Last touch: '+esc(c.last_touch)):''}</div>`}
    ${c.proof?`<div class="recon" style="background:#f0fdf4;border-color:#bbf7d0;color:#166534">&#127919; Proof point to reference: ${esc(c.proof)}</div>`:''}
    ${c.hq_phone?`<div class="recon" style="background:#fff7ed;border-color:#fed7aa;color:#9a3412">&#9742; HQ main line: ${esc(c.hq_phone)} &mdash; any contact number flagged below matches this or is a shared line (not a direct dial)</div>`:''}
    <div class="card"><div class="ov">${esc(c.overview)}</div><div class="flag"><b>FLAG:</b> ${esc(c.flags)}</div></div>
    ${sourceBlock(c)}`;
  ["T1","T2","T3"].forEach(t=>{if(tiers[t]&&tiers[t].length){body+=`<div class="tier">${t} Contacts</div>`;tiers[t].forEach(x=>body+=contact(x,c.id))}});
  const done=worked().includes(c.id);
  body+=`<div class="markbar"><button class="mark ${done?'done':''}" id="markbtn" onclick="mark('${c.id}')">${done?'&#10003; Reopened':'Mark reopened'}</button>
    <span style="color:#646b76;font-size:13px">Sends nothing &mdash; just tracks your progress &amp; streak.</span></div>
    <div style="height:30px"></div>`;
  D.innerHTML=body;
  D.querySelectorAll('.copy').forEach(b=>b.onclick=()=>{navigator.clipboard.writeText(b.getAttribute('data-c'));b.textContent='Copied';b.classList.add('ok');setTimeout(()=>{b.textContent='Copy';b.classList.remove('ok')},1200)});
  D.querySelectorAll('.vbtn').forEach(b=>b.onclick=()=>{const k=b.getAttribute('data-vk');setVerified(k,!isVerified(k));openCo(i)});
  window.scrollTo(0,0);
}
function sourceBlock(c){
  const titles=["VP Operations","Director of Operations","Franchise Development","COO","President"];
  const links=titles.map(t=>`<a class="src" href="${liPeople('"'+(c.name||'')+'" '+t)}" target="_blank" rel="noopener">${esc(t)} &#8599;</a>`).join("");
  const all=`<a class="src" href="${liPeople(c.name||'')}" target="_blank" rel="noopener">All people &#8599;</a>`;
  const thin=(c.contacts||[]).length<2;
  const head=thin?'&#9888; Few or no contacts on file &mdash; source them on LinkedIn:':'Find more contacts on LinkedIn:';
  return `<div class="srcbox"><div class="srch">${head}</div><div class="srclinks">${all}${links}</div>`+
    `<div class="srcnote">Opens a LinkedIn people search for this company + role. Confirm the person on their profile, then work them here (drafts are a template) or add them in HubSpot.</div></div>`;
}
function closeCo(){document.getElementById('detail').style.display='none';document.getElementById('home').style.display='block';grid();window.scrollTo(0,0)}
function mark(id){let w=worked();if(w.includes(id)){w=w.filter(x=>x!==id);toast('Unmarked')}else{w.push(id);toast('Nice. Reopened. 🔥')}setWorked(w);const b=document.getElementById('markbtn');const done=w.includes(id);b.className='mark '+(done?'done':'');b.innerHTML=done?'&#10003; Reopened':'Mark reopened'}
grid();
</script>
"""


def render_html(page: PageData, streak: int = 1, rep_name: str = "") -> str:
    return render_data(page.to_data_json(), streak=streak, rep_name=rep_name)


def render_data(data: dict, streak: int = 1, rep_name: str = "") -> str:
    """Render straight from a data.json dict (used by incremental add/remove, which
    edit the payload directly rather than rebuilding every Company object)."""
    return (
        _TEMPLATE
        .replace("__DATA__", json.dumps(data))
        .replace("__DATE__", data.get("generated", ""))
        .replace("__STREAK__", str(streak))
        .replace("__REPNAME__", rep_name or "")
    )
