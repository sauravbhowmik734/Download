from flask import Flask, request, jsonify, Response, send_file
from urllib.parse import urlparse, unquote
from pathlib import Path
import requests
import re
import html as html_lib
import os
import json
import shutil
import subprocess
import tempfile
import sys
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

MAX_FILE_SIZE = 500 * 1024 * 1024
TIMEOUT = (10, 60)
PARALLEL_CHUNKS = max(2, min(8, int(os.environ.get("NEO_DROP_CHUNKS", "4"))))
CHUNK_SIZE = 1024 * 1024
PREPARE_TTL = 15 * 60
PREPARED_DIR = Path(tempfile.gettempdir()) / "neo_drop_prepared"
PREPARED_DIR.mkdir(parents=True, exist_ok=True)
PREPARED = {}

# ============================================================
# EMBEDDED HTML
# ============================================================
INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#f5f0df">
<meta name="description" content="NEO-DROP media transfer interface">
<link rel="manifest" href="/manifest.webmanifest">
<title>NEO-DROP // MEDIA DOWNLOADER</title>

<style>
/* =========================================================
   NEO-DROP // CORE RESET
   ========================================================= */
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
    min-height:100vh;
    background:#f5f0df;
    color:#101010;
    font-family:Arial,Helvetica,sans-serif;
    overflow-x:hidden;
}
button,input,select{font:inherit}
button{cursor:pointer}
a{color:inherit}
img{max-width:100%;display:block}

/* =========================================================
   DESIGN TOKENS
   ========================================================= */
:root{
    --paper:#f5f0df;
    --ink:#101010;
    --yellow:#ffe66d;
    --pink:#ff78ad;
    --blue:#76c7ff;
    --green:#9cf29c;
    --orange:#ff9b54;
    --white:#fffdf4;
    --shadow:8px 8px 0 var(--ink);
    --shadow-sm:5px 5px 0 var(--ink);
    --border:4px solid var(--ink);
    --radius:18px;
}

/* =========================================================
   APP SHELL
   ========================================================= */
.app{
    width:min(1500px,calc(100% - 24px));
    margin:12px auto 60px;
}
.topbar{
    border:var(--border);
    background:var(--white);
    box-shadow:var(--shadow);
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:16px;
    padding:14px;
    position:sticky;
    top:10px;
    z-index:50;
}
.brand{
    display:flex;
    align-items:center;
    gap:12px;
    min-width:0;
}
.logo-box{
    width:54px;
    height:54px;
    border:var(--border);
    background:var(--yellow);
    box-shadow:4px 4px 0 var(--ink);
    display:grid;
    place-items:center;
    font-weight:1000;
    font-size:24px;
    flex:none;
}
.brand-text{min-width:0}
.brand-title{
    font-size:clamp(20px,4vw,34px);
    line-height:.9;
    font-weight:1000;
    letter-spacing:-1.8px;
}
.brand-sub{
    margin-top:5px;
    font-size:11px;
    font-weight:900;
    letter-spacing:1px;
}
.top-actions{
    display:flex;
    gap:8px;
    flex-wrap:wrap;
    justify-content:flex-end;
}
.mini-btn{
    border:3px solid var(--ink);
    background:var(--paper);
    padding:10px 12px;
    font-weight:1000;
    box-shadow:3px 3px 0 var(--ink);
}
.mini-btn:active{transform:translate(3px,3px);box-shadow:none}

/* =========================================================
   HERO
   ========================================================= */
.hero{
    margin-top:28px;
    border:var(--border);
    background:var(--blue);
    box-shadow:var(--shadow);
    padding:clamp(20px,5vw,56px);
    position:relative;
    overflow:hidden;
}
.hero:before{
    content:"";
    position:absolute;
    width:180px;
    height:180px;
    border:var(--border);
    background:var(--pink);
    transform:rotate(16deg);
    right:-50px;
    top:-70px;
}
.hero:after{
    content:"";
    position:absolute;
    width:90px;
    height:90px;
    border:var(--border);
    background:var(--yellow);
    transform:rotate(-13deg);
    right:90px;
    bottom:-45px;
}
.kicker{
    display:inline-block;
    border:3px solid var(--ink);
    background:var(--yellow);
    padding:7px 10px;
    font-size:12px;
    font-weight:1000;
    box-shadow:4px 4px 0 var(--ink);
}
.hero h1{
    margin-top:18px;
    max-width:980px;
    font-size:clamp(42px,8vw,100px);
    line-height:.82;
    letter-spacing:-6px;
    font-weight:1000;
    text-transform:uppercase;
}
.hero p{
    max-width:820px;
    margin-top:22px;
    font-size:clamp(14px,2vw,20px);
    line-height:1.35;
    font-weight:800;
}

/* =========================================================
   PROGRESSIVE INPUT / PREMIUM MOTION
   ========================================================= */
.reveal-after-paste{
    display:none !important;
}
.reveal-after-paste.is-visible{
    display:block !important;
    animation:neoReveal .55s cubic-bezier(.2,.9,.2,1) both;
}
@keyframes neoReveal{
    from{opacity:0;transform:translateY(18px) scale(.985);filter:blur(4px)}
    to{opacity:1;transform:none;filter:none}
}
.url-row{
    position:relative;
}
.paste-btn{
    border:var(--border);
    background:var(--yellow);
    padding:0 20px;
    font-weight:1000;
    font-size:15px;
    box-shadow:var(--shadow-sm);
    white-space:nowrap;
    transition:transform .12s ease,box-shadow .12s ease;
}
.paste-btn:active{transform:translate(5px,5px);box-shadow:none}
.url-row.has-value .url-input{
    background:var(--yellow);
}
.url-row.has-value{
    animation:urlPulse .5s ease;
}
@keyframes urlPulse{
    0%{filter:brightness(1)}
    35%{filter:brightness(1.15)}
    100%{filter:brightness(1)}
}
.refresh-btn{
    background:var(--green);
}

/* floating background motion */
body::before{
    content:"";
    position:fixed;
    inset:-30%;
    z-index:-1;
    pointer-events:none;
    opacity:.13;
    background:
        linear-gradient(90deg,transparent 49%,var(--ink) 50%,transparent 51%) 0 0/72px 72px,
        linear-gradient(0deg,transparent 49%,var(--ink) 50%,transparent 51%) 0 0/72px 72px;
    animation:neoGrid 18s linear infinite;
}
@keyframes neoGrid{
    from{transform:translate3d(0,0,0) rotate(.001deg)}
    to{transform:translate3d(72px,72px,0) rotate(.001deg)}
}

/* random click particles */
.neo-click-burst{
    position:fixed;
    left:0;top:0;
    width:16px;height:16px;
    pointer-events:none;
    z-index:9999;
    transform:translate(-50%,-50%);
}
.neo-particle{
    position:absolute;
    left:50%;top:50%;
    width:var(--s);height:var(--s);
    background:var(--c);
    border:2px solid var(--ink);
    box-shadow:2px 2px 0 var(--ink);
    transform:translate(-50%,-50%) rotate(0deg);
    animation:neoParticle var(--d) cubic-bezier(.1,.8,.2,1) forwards;
}
@keyframes neoParticle{
    0%{opacity:1;transform:translate(-50%,-50%) rotate(0deg) scale(.4)}
    70%{opacity:1}
    100%{opacity:0;transform:translate(calc(-50% + var(--x)),calc(-50% + var(--y))) rotate(var(--r)) scale(1.15)}
}
.neo-ripple{
    position:fixed;
    width:20px;height:20px;
    border:4px solid var(--ink);
    border-radius:50%;
    pointer-events:none;
    z-index:9998;
    transform:translate(-50%,-50%) scale(.2);
    animation:neoRipple .7s ease-out forwards;
}
@keyframes neoRipple{
    to{opacity:0;transform:translate(-50%,-50%) scale(7)}
}
.neo-spark{
    position:fixed;
    pointer-events:none;
    z-index:9999;
    font-weight:1000;
    font-size:20px;
    animation:neoSpark .8s ease-out forwards;
}
@keyframes neoSpark{
    0%{opacity:0;transform:translate(-50%,-20%) scale(.4) rotate(0)}
    15%{opacity:1}
    100%{opacity:0;transform:translate(calc(-50% + var(--x)),calc(-50% + var(--y))) scale(1.2) rotate(var(--r))}
}

/* progressive display modes preserve each component's native layout */
.reveal-after-paste{display:none !important}
.helper-row.reveal-after-paste.is-visible{display:flex !important}
.options.reveal-after-paste.is-visible{display:grid !important}
.download-zone.reveal-after-paste.is-visible{display:block !important}
.status-stack.reveal-after-paste.is-visible{display:grid !important}
.progress-panel.reveal-after-paste.is-visible{display:block !important}
.history.reveal-after-paste.is-visible{display:block !important}
.features.reveal-after-paste.is-visible{display:grid !important}
.faq.reveal-after-paste.is-visible{display:block !important}
.footer.reveal-after-paste.is-visible{display:flex !important}
.url-row:not(.has-value) #detectBtn{display:none}

/* =========================================================
   URL WORKSPACE
   ========================================================= */
.workspace{
    margin-top:30px;
    display:grid;
    grid-template-columns:minmax(0,1.8fr) minmax(300px,.8fr);
    gap:24px;
}
.panel{
    border:var(--border);
    background:var(--white);
    box-shadow:var(--shadow);
}
.panel-head{
    border-bottom:var(--border);
    padding:14px 16px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:10px;
}
.panel-title{
    font-size:18px;
    font-weight:1000;
    text-transform:uppercase;
}
.panel-tag{
    border:3px solid var(--ink);
    background:var(--green);
    padding:5px 8px;
    font-size:10px;
    font-weight:1000;
}
.panel-body{padding:18px}
.url-row{
    display:flex;
    gap:10px;
    align-items:stretch;
}
.url-input{
    flex:1;
    min-width:0;
    border:var(--border);
    background:#fff;
    padding:16px;
    font-size:16px;
    font-weight:800;
    outline:none;
}
.url-input:focus{
    background:var(--yellow);
    box-shadow:5px 5px 0 var(--ink);
}
.primary{
    border:var(--border);
    background:var(--pink);
    padding:0 24px;
    font-weight:1000;
    font-size:16px;
    box-shadow:var(--shadow-sm);
    white-space:nowrap;
}
.primary:active{
    transform:translate(5px,5px);
    box-shadow:none;
}
.secondary{
    border:3px solid var(--ink);
    background:var(--paper);
    padding:11px 14px;
    font-weight:1000;
}
.helper-row{
    display:flex;
    flex-wrap:wrap;
    gap:8px;
    margin-top:12px;
}
.chip{
    border:3px solid var(--ink);
    background:var(--yellow);
    padding:7px 9px;
    font-size:11px;
    font-weight:1000;
}

/* =========================================================
   MEDIA DETECTION CARD
   ========================================================= */
.detected{
    margin-top:18px;
    border:var(--border);
    background:var(--paper);
    display:none;
}
.detected.show{display:block}
.detected-grid{
    display:grid;
    grid-template-columns:160px 1fr;
    gap:16px;
    padding:16px;
}
.thumb{
    position:relative;
    aspect-ratio:16/10;
    min-height:120px;
    overflow:hidden;
    border:var(--border);
    background:
        linear-gradient(135deg,#111 25%,transparent 25%) 0 0/24px 24px,
        linear-gradient(315deg,#111 25%,transparent 25%) 0 0/24px 24px,
        var(--yellow);
    display:grid;
    place-items:center;
    font-weight:1000;
    text-align:center;
}
.thumb img,.thumb video{
    width:100%;
    height:100%;
    object-fit:cover;
    display:block;
    background:#111;
}
.thumb .preview-empty{
    padding:14px;
    font-size:12px;
    line-height:1.2;
}
.thumb .file-preview{
    width:100%;
    height:100%;
    min-height:120px;
    display:grid;
    place-items:center;
    text-align:center;
    padding:18px;
    background:var(--white);
}
.file-preview strong{
    display:block;
    font-size:clamp(22px,5vw,42px);
    line-height:1;
    word-break:break-word;
}
.file-preview span{
    display:block;
    margin-top:8px;
    font-size:12px;
    font-weight:1000;
    word-break:break-all;
}
.detected-title{
    font-size:clamp(18px,3vw,28px);
    font-weight:1000;
    line-height:1;
}
.detected-meta{
    display:flex;
    flex-wrap:wrap;
    gap:7px;
    margin-top:10px;
}
.meta{
    border:3px solid var(--ink);
    background:var(--white);
    padding:6px 8px;
    font-size:11px;
    font-weight:900;
}

/* =========================================================
   OPTIONS
   ========================================================= */
.options{
    margin-top:18px;
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:12px;
}
.field{
    border:3px solid var(--ink);
    background:var(--white);
    padding:12px;
}
.field label{
    display:block;
    font-size:11px;
    font-weight:1000;
    text-transform:uppercase;
    margin-bottom:7px;
}
.field select,
.field input{
    width:100%;
    border:3px solid var(--ink);
    background:var(--paper);
    padding:11px;
    font-weight:900;
    outline:none;
}
.field select:focus,
.field input:focus{background:var(--yellow)}
.quality-list{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:7px;
}
.quality{
    border:3px solid var(--ink);
    background:var(--white);
    padding:10px 5px;
    text-align:center;
    font-weight:1000;
    font-size:12px;
}
.quality.active{
    background:var(--green);
    box-shadow:3px 3px 0 var(--ink);
}
.download-zone{
    margin-top:16px;
    border:var(--border);
    background:var(--green);
    padding:16px;
}
.download-btn{
    width:100%;
    border:var(--border);
    background:var(--ink);
    color:var(--white);
    min-height:64px;
    font-size:clamp(18px,3vw,26px);
    font-weight:1000;
    letter-spacing:1px;
    box-shadow:var(--shadow-sm);
}
.download-btn:active{
    transform:translate(5px,5px);
    box-shadow:none;
}
.download-note{
    margin-top:9px;
    font-size:11px;
    font-weight:900;
}

/* =========================================================
   SIDE STATUS
   ========================================================= */
.status-stack{
    display:grid;
    gap:14px;
}
.status-card{
    border:3px solid var(--ink);
    padding:15px;
    background:var(--yellow);
}
.status-card:nth-child(2){background:var(--pink)}
.status-card:nth-child(3){background:var(--orange)}
.status-label{
    font-size:10px;
    font-weight:1000;
    text-transform:uppercase;
}
.status-value{
    margin-top:6px;
    font-size:24px;
    font-weight:1000;
}
.platforms{
    display:grid;
    grid-template-columns:repeat(2,1fr);
    gap:8px;
}
.platform{
    border:3px solid var(--ink);
    padding:11px 8px;
    background:var(--white);
    font-weight:1000;
    font-size:12px;
    text-align:center;
}
.platform small{
    display:block;
    margin-top:3px;
    font-size:9px;
}

/* =========================================================
   PROGRESS
   ========================================================= */
.progress-panel{
    margin-top:30px;
}
.progress-wrap{
    padding:18px;
}
.progress-top{
    display:flex;
    justify-content:space-between;
    gap:10px;
    font-weight:1000;
    margin-bottom:10px;
}
.progress-track{
    height:28px;
    border:var(--border);
    background:var(--white);
    overflow:hidden;
}
.progress-bar{
    width:0%;
    height:100%;
    background:var(--pink);
    transition:width .2s linear;
}
.progress-log{
    margin-top:14px;
    border:3px solid var(--ink);
    background:#111;
    color:#f8f8f8;
    min-height:120px;
    max-height:220px;
    overflow:auto;
    padding:12px;
    font-family:monospace;
    font-size:12px;
    line-height:1.5;
}

/* =========================================================
   HISTORY
   ========================================================= */
.history{
    margin-top:30px;
}
.history-list{
    padding:14px;
    display:grid;
    gap:10px;
}
.history-item{
    border:3px solid var(--ink);
    background:var(--paper);
    padding:12px;
    display:grid;
    grid-template-columns:1fr auto;
    gap:12px;
    align-items:center;
}
.history-url{
    font-size:12px;
    font-weight:900;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
}
.history-time{
    font-size:10px;
    font-weight:800;
    margin-top:4px;
}
.history-actions{
    display:flex;
    gap:6px;
}

/* =========================================================
   FEATURE GRID
   ========================================================= */
.features{
    margin-top:30px;
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:18px;
}
.feature{
    border:var(--border);
    box-shadow:var(--shadow);
    padding:20px;
    min-height:180px;
}
.feature:nth-child(1){background:var(--yellow)}
.feature:nth-child(2){background:var(--pink)}
.feature:nth-child(3){background:var(--blue)}
.feature:nth-child(4){background:var(--green)}
.feature:nth-child(5){background:var(--orange)}
.feature:nth-child(6){background:var(--white)}
.feature-number{
    font-size:42px;
    line-height:1;
    font-weight:1000;
}
.feature h3{
    margin-top:14px;
    font-size:20px;
    font-weight:1000;
}
.feature p{
    margin-top:8px;
    font-size:12px;
    line-height:1.45;
    font-weight:800;
}

/* =========================================================
   FAQ
   ========================================================= */
.faq{
    margin-top:30px;
}
.faq-list{
    padding:14px;
    display:grid;
    gap:10px;
}
details{
    border:3px solid var(--ink);
    background:var(--paper);
    padding:13px;
}
summary{
    cursor:pointer;
    font-weight:1000;
}
details p{
    margin-top:10px;
    font-size:12px;
    font-weight:800;
    line-height:1.5;
}

/* =========================================================
   FOOTER
   ========================================================= */
.footer{
    margin-top:35px;
    border:var(--border);
    background:var(--ink);
    color:var(--white);
    box-shadow:var(--shadow);
    padding:22px;
    display:flex;
    justify-content:space-between;
    gap:18px;
    flex-wrap:wrap;
}
.footer strong{font-size:18px}
.footer span{
    font-size:11px;
    font-weight:800;
    max-width:700px;
    line-height:1.5;
}

/* =========================================================
   TOAST
   ========================================================= */
.toast{
    position:fixed;
    left:50%;
    bottom:22px;
    transform:translate(-50%,30px);
    opacity:0;
    pointer-events:none;
    z-index:100;
    border:var(--border);
    background:var(--yellow);
    box-shadow:var(--shadow-sm);
    padding:14px 18px;
    font-weight:1000;
    max-width:calc(100% - 30px);
    text-align:center;
    transition:.2s ease;
}
.toast.show{
    transform:translate(-50%,0);
    opacity:1;
}

/* =========================================================
   MODAL
   ========================================================= */
.modal{
    position:fixed;
    inset:0;
    background:rgba(0,0,0,.65);
    display:none;
    place-items:center;
    padding:18px;
    z-index:90;
}
.modal.show{display:grid}
.modal-box{
    width:min(620px,100%);
    border:var(--border);
    background:var(--white);
    box-shadow:12px 12px 0 #000;
}
.modal-head{
    padding:14px;
    border-bottom:var(--border);
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.modal-head h2{font-size:20px;font-weight:1000}
.close{
    border:3px solid var(--ink);
    background:var(--pink);
    width:40px;
    height:40px;
    font-weight:1000;
}
.modal-body{padding:18px}
.modal-body p{
    font-size:13px;
    line-height:1.55;
    font-weight:800;
}
.modal-actions{
    display:flex;
    gap:10px;
    margin-top:18px;
}
.modal-actions button{flex:1;min-height:48px}

/* =========================================================
   RESPONSIVE
   ========================================================= */
@media(max-width:900px){
    .workspace{grid-template-columns:1fr}
    .features{grid-template-columns:repeat(2,1fr)}
}
@media(max-width:650px){
    .app{width:calc(100% - 14px);margin:7px auto 40px}
    .topbar{position:relative;top:auto}
    .top-actions{display:flex}
    .top-actions .desktop-action{display:none}
    .refresh-btn{display:block;padding:9px 10px;font-size:11px}
    .hero{margin-top:20px}
    .hero h1{letter-spacing:-3px}
    .url-row{
        display:grid;
        grid-template-columns:minmax(0,1fr) auto;
        gap:8px;
    }
    .url-input{min-width:0;padding:14px 12px}
    .paste-btn{padding:0 14px;min-height:54px}
    .primary{min-height:56px;grid-column:1 / -1}
    .detected-grid{grid-template-columns:1fr}
    .thumb{max-width:260px}
    .options{grid-template-columns:1fr}
    .quality-list{grid-template-columns:repeat(2,1fr)}
    .features{grid-template-columns:1fr}
    .history-item{grid-template-columns:1fr}
    .history-actions{justify-content:flex-start}
    .footer{box-shadow:var(--shadow-sm)}
}
</style>
</head>

<body>
<div class="app">

<header class="topbar">
    <div class="brand">
        <div class="logo-box">N</div>
        <div class="brand-text">
            <div class="brand-title">NEO-DROP</div>
            <div class="brand-sub">MEDIA UTILITY // DIRECT FILE WORKFLOW</div>
        </div>
    </div>
    <div class="top-actions">
        <button class="mini-btn refresh-btn" id="refreshBtn" aria-label="Refresh page">↻ REFRESH</button>
        <button class="mini-btn desktop-action" id="historyBtn">HISTORY</button>
        <button class="mini-btn desktop-action" id="helpBtn">HOW IT WORKS</button>
        <button class="mini-btn desktop-action" id="themeBtn">INVERT</button>
    </div>
</header>

<section class="hero">
    <span class="kicker">01 // PASTE → CHOOSE → DOWNLOAD</span>
    <h1>TURN A MEDIA LINK INTO A FILE.</h1>
    <p>
        A bold, fast and mobile-first media utility interface. Paste a direct media URL
        or an authorized supported media page URL, inspect it, then start the transfer.
    </p>
</section>

<main class="workspace">

<section class="panel">
    <div class="panel-head">
        <div class="panel-title">Media Input</div>
        <div class="panel-tag" id="connectionTag">SERVER READY</div>
    </div>

    <div class="panel-body">

        <div class="url-row">
            <input
                id="urlInput"
                class="url-input"
                type="url"
                inputmode="url"
                autocomplete="off"
                placeholder="Paste a direct media URL or an authorized supported page URL..."
                aria-label="Media URL">
            <button class="paste-btn" id="pasteBtn" type="button">PASTE</button>
            <button class="primary" id="detectBtn" type="button">DETECT</button>
        </div>

        <div class="helper-row reveal-after-paste" id="helperRow">
            <span class="chip">VIDEO</span>
            <span class="chip">AUDIO</span>
            <span class="chip">1080P UI</span>
            <span class="chip">MOBILE</span>
            <span class="chip">FAST TRANSFER</span>
        </div>

        <div class="detected" id="detectedCard">
            <div class="detected-grid">
                <div class="thumb" id="thumbBox">MEDIA<br>PREVIEW</div>
                <div>
                    <div class="detected-title" id="detectedTitle">DIRECT MEDIA RESOURCE</div>
                    <div class="detected-meta">
                        <span class="meta" id="detectedType">TYPE: UNKNOWN</span>
                        <span class="meta" id="detectedSize">SIZE: --</span>
                        <span class="meta" id="selectedEstimate">SELECTED: --</span>
                        <span class="meta" id="detectedHost">HOST: --</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="options reveal-after-paste" id="optionsPanel">

            <div class="field">
                <label>Media mode</label>
                <select id="modeSelect">
                    <option value="video">VIDEO</option>
                    <option value="audio">AUDIO</option>
                    <option value="auto">AUTO DETECT</option>
                    <option value="image">PHOTO / BANNER</option>
                </select>
            </div>

            <div class="field">
                <label>Output format</label>
                <select id="formatSelect">
                    <option value="mp4">MP4</option>
                    <option value="webm">WEBM</option>
                    <option value="mp3">MP3</option>
                    <option value="original">ORIGINAL / DIRECT</option>
                    <option value="thumbnail">THUMBNAIL</option>
                </select>
            </div>

            <div class="field">
                <label>Quality</label>
                <div class="quality-list">
                    <button class="quality" data-quality="360p">360P</button>
                    <button class="quality" data-quality="480p">480P</button>
                    <button class="quality" data-quality="720p">720P</button>
                    <button class="quality" data-quality="1080p">1080P</button>
                    <button class="quality" data-quality="1440p">1440P</button>
                    <button class="quality" data-quality="source">SOURCE</button>
                </div>
            </div>

        </div>

        <div class="download-zone reveal-after-paste" id="downloadZone">
            <button class="download-btn" id="downloadBtn">
                START DOWNLOAD
            </button>
            <div class="download-note">
                Use this tool only for media you own or have permission to download.
            </div>
        </div>

    </div>
</section>

<aside class="status-stack reveal-after-paste" id="statusStack">

    <div class="status-card">
        <div class="status-label">Current mode</div>
        <div class="status-value" id="modeStatus">VIDEO</div>
    </div>

    <div class="status-card">
        <div class="status-label">Selected quality</div>
        <div class="status-value" id="qualityStatus">SOURCE</div>
    </div>

    <div class="status-card">
        <div class="status-label">Output</div>
        <div class="status-value" id="formatStatus">MP4</div>
    </div>

    <div class="panel" style="box-shadow:none">
        <div class="panel-head">
            <div class="panel-title">Compatible workflow</div>
        </div>
        <div class="panel-body">
            <div class="platforms">
                <div class="platform">DIRECT URL<small>HTTP / HTTPS</small></div>
                <div class="platform">MP4<small>VIDEO</small></div>
                <div class="platform">WEBM<small>VIDEO</small></div>
                <div class="platform">AUDIO<small>MEDIA</small></div>
                <div class="platform">1080P<small>OPTION</small></div>
                <div class="platform">SOURCE<small>ORIGINAL</small></div>
            </div>
        </div>
    </div>

</aside>

</main>

<section class="panel progress-panel reveal-after-paste" id="progressPanel">
    <div class="panel-head">
        <div class="panel-title">Transfer Monitor</div>
        <div class="panel-tag" id="transferState">IDLE</div>
    </div>
    <div class="progress-wrap">
        <div class="progress-top">
            <span id="progressLabel">WAITING FOR DOWNLOAD</span>
            <span id="progressPercent">0%</span>
        </div>
        <div class="progress-track">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <div class="progress-log" id="logBox">
[NEO-DROP] client initialized
[NEO-DROP] waiting for a media URL or supported media page...
        </div>
    </div>
</section>

<section class="panel history reveal-after-paste" id="historySection">
    <div class="panel-head">
        <div class="panel-title">Local Session History</div>
        <button class="secondary" id="clearHistoryBtn">CLEAR</button>
    </div>
    <div class="history-list" id="historyList">
        <div class="history-item">
            <div>
                <div class="history-url">No downloads in this session.</div>
                <div class="history-time">History stays in this browser.</div>
            </div>
        </div>
    </div>
</section>

<section class="features reveal-after-paste" id="featuresSection">

    <article class="feature">
        <div class="feature-number">01</div>
        <h3>ONE BOX</h3>
        <p>
            A single URL input keeps the interface simple. Paste an authorized
            direct media resource and let the backend inspect it.
        </p>
    </article>

    <article class="feature">
        <div class="feature-number">02</div>
        <h3>QUALITY CONTROL</h3>
        <p>
            Choose a preferred quality in the UI. The backend respects the available source quality and never pretends an unsupported native resolution exists.
        </p>
    </article>

    <article class="feature">
        <div class="feature-number">03</div>
        <h3>FORMAT SWITCH</h3>
        <p>
            MP4, WebM and audio-oriented choices are exposed as clear output
            preferences for the server workflow.
        </p>
    </article>

    <article class="feature">
        <div class="feature-number">04</div>
        <h3>LIVE STATUS</h3>
        <p>
            Transfer state, percentage and server messages are shown in the
            brutalist monitor panel.
        </p>
    </article>

    <article class="feature">
        <div class="feature-number">05</div>
        <h3>MOBILE FIRST</h3>
        <p>
            The layout collapses into a touch-friendly single-column interface
            for Android and small screens.
        </p>
    </article>

    <article class="feature">
        <div class="feature-number">06</div>
        <h3>NO FAKE BUTTONS</h3>
        <p>
            The download action communicates with a real backend endpoint instead
            of pretending that frontend JavaScript can fetch every platform page.
        </p>
    </article>

</section>

<section class="panel faq reveal-after-paste" id="faqSection">
    <div class="panel-head">
        <div class="panel-title">FAQ / Rules</div>
    </div>
    <div class="faq-list">

        <details open>
            <summary>What kind of URL should I paste?</summary>
            <p>
                Paste a direct HTTP or HTTPS URL that points to a media resource
                you are authorized to retrieve, such as your own hosted MP4 or
                another permitted audio/video file.
            </p>
        </details>

        <details>
            <summary>Can the frontend itself download any website?</summary>
            <p>
                No. A normal browser page cannot reliably turn arbitrary platform
                pages into downloadable media. This UI therefore talks to a
                controlled server endpoint.
            </p>
        </details>

        <details>
            <summary>Does selecting 1080P create a 1080P file?</summary>
            <p>
                No. A quality selector is a preference. A direct file that is only
                720P cannot honestly become native 1080P simply because the button
                says 1080P.
            </p>
        </details>

        <details>
            <summary>Where is history stored?</summary>
            <p>
                This interface stores the current session's history in browser
                localStorage. It is not uploaded to a third-party analytics system.
            </p>
        </details>

        <details>
            <summary>What happens if the URL is invalid?</summary>
            <p>
                The server returns a structured error and the monitor panel shows
                the failure message so the user can correct the URL.
            </p>
        </details>

    </div>
</section>

<footer class="footer reveal-after-paste" id="footerSection">
    <strong>NEO-DROP // BUILD 01</strong>
    <span>
        Media transfer interface for authorized direct media resources.
        Respect copyright, platform rules, and the rights of content owners.
    </span>
</footer>

</div>

<div class="toast" id="toast">READY</div>

<div class="modal" id="helpModal">
    <div class="modal-box">
        <div class="modal-head">
            <h2>HOW NEO-DROP WORKS</h2>
            <button class="close" id="closeHelp">X</button>
        </div>
        <div class="modal-body">
            <p>
                1. Paste an authorized direct media URL.<br>
                2. Press DETECT to inspect the resource.<br>
                3. Choose mode, format and quality preference.<br>
                4. Press START DOWNLOAD.<br>
                5. The server retrieves the permitted resource and returns a file.
            </p>
            <div class="modal-actions">
                <button class="secondary" id="modalOk">GOT IT</button>
            </div>
        </div>
    </div>
</div>

<script>
/* =========================================================
   NEO-DROP // CLIENT ENGINE
   ========================================================= */

const state = {
    quality: "source",
    detected: false,
    busy: false,
    qualitySizes: {},
    sourceSize: 0
};

const $ = (selector) => document.querySelector(selector);

const urlInput = $("#urlInput");
const urlRow = document.querySelector(".url-row");
const pasteBtn = $("#pasteBtn");
const detectBtn = $("#detectBtn");
const refreshBtn = $("#refreshBtn");
const revealBlocks = document.querySelectorAll(".reveal-after-paste");
const downloadBtn = $("#downloadBtn");
const detectedCard = $("#detectedCard");
const detectedTitle = $("#detectedTitle");
const detectedType = $("#detectedType");
const detectedSize = $("#detectedSize");
const selectedEstimate = $("#selectedEstimate");
const detectedHost = $("#detectedHost");
const thumbBox = $("#thumbBox");
const modeSelect = $("#modeSelect");
const formatSelect = $("#formatSelect");
const modeStatus = $("#modeStatus");
const qualityStatus = $("#qualityStatus");
const formatStatus = $("#formatStatus");
const transferState = $("#transferState");
const progressLabel = $("#progressLabel");
const progressPercent = $("#progressPercent");
const progressBar = $("#progressBar");
const logBox = $("#logBox");
const toast = $("#toast");
const historyList = $("#historyList");

function log(message){
    const stamp = new Date().toLocaleTimeString();
    logBox.textContent += `\n[${stamp}] ${message}`;
    logBox.scrollTop = logBox.scrollHeight;
}

function showToast(message){
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.remove("show"), 2200);
}

function setProgress(value,label){
    const safe = Math.max(0,Math.min(100,Number(value)||0));
    progressBar.style.width = safe + "%";
    progressPercent.textContent = Math.round(safe) + "%";
    progressLabel.textContent = label;
}

function setBusy(value){
    state.busy = value;
    detectBtn.disabled = value;
    downloadBtn.disabled = value;
    detectBtn.style.opacity = value ? ".55" : "1";
    downloadBtn.style.opacity = value ? ".55" : "1";
}

function validUrl(value){
    try{
        const u = new URL(value);
        return u.protocol === "http:" || u.protocol === "https:";
    }catch{
        return false;
    }
}

function formatBytes(bytes){
    if(!bytes || bytes < 1) return "--";
    const units = ["B","KB","MB","GB"];
    let i = 0;
    let n = bytes;
    while(n >= 1024 && i < units.length-1){
        n /= 1024;
        i++;
    }
    return n.toFixed(i ? 1 : 0) + " " + units[i];
}

function hostOf(value){
    try{
        return new URL(value).hostname;
    }catch{
        return "--";
    }
}

function updateSelectedEstimate(){
    const value = Number(state.qualitySizes[state.quality] || 0);
    if(value > 0){
        selectedEstimate.textContent = "SELECTED: " + formatBytes(value);
    }else if(state.sourceSize > 0 && state.quality === "source"){
        selectedEstimate.textContent = "SELECTED: " + formatBytes(state.sourceSize);
    }else if(state.detected){
        selectedEstimate.textContent = "SELECTED: SIZE UNKNOWN";
    }else{
        selectedEstimate.textContent = "SELECTED: --";
    }
}

function setStatus(){
    modeStatus.textContent = modeSelect.value.toUpperCase();
    qualityStatus.textContent = state.quality.toUpperCase();
    formatStatus.textContent = formatSelect.value.toUpperCase();
}

function applyDetectedMode(data){
    const mode = String(data.media_mode || "file").toLowerCase();
    const media = mode === "video" || mode === "photo" || mode === "audio";
    if(mode === "video") {
        modeSelect.value = "video";
        if(formatSelect.value === "original" || formatSelect.value === "thumbnail") formatSelect.value = "mp4";
    }else if(mode === "photo") {
        modeSelect.value = "image";
        formatSelect.value = "original";
    }else if(mode === "audio") {
        modeSelect.value = "audio";
        if(formatSelect.value === "original" || formatSelect.value === "thumbnail") formatSelect.value = "mp3";
    }else{
        modeSelect.value = "auto";
        formatSelect.value = "original";
    }
    document.querySelectorAll(".quality").forEach(button => {
        button.disabled = !media || mode !== "video";
        button.style.opacity = (!media || mode !== "video") ? ".45" : "1";
    });
    setStatus();
}

document.querySelectorAll(".quality").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".quality").forEach(x => x.classList.remove("active"));
        button.classList.add("active");
        state.quality = button.dataset.quality;
        setStatus();
        updateSelectedEstimate();
        log("quality preference -> " + state.quality);
    });
});

modeSelect.addEventListener("change", () => {
    setStatus();
    log("mode -> " + modeSelect.value);
});

formatSelect.addEventListener("change", () => {
    setStatus();
    log("format -> " + formatSelect.value);
});

function revealAfterPaste(force=false){
    const hasValue = force || urlInput.value.trim().length > 0;
    urlRow.classList.toggle("has-value", hasValue);
    revealBlocks.forEach((el,index) => {
        if(hasValue){
            el.classList.add("is-visible");
            el.style.animationDelay = Math.min(index * 55, 330) + "ms";
        }else{
            el.classList.remove("is-visible");
            el.style.animationDelay = "0ms";
        }
    });
}

function randomClickAnimation(x,y){
    const colors = ["var(--yellow)","var(--pink)","var(--blue)","var(--green)","var(--orange)"];
    const burst = document.createElement("div");
    burst.className = "neo-click-burst";
    burst.style.left = x + "px";
    burst.style.top = y + "px";
    const count = 7 + Math.floor(Math.random()*7);
    for(let i=0;i<count;i++){
        const p = document.createElement("i");
        p.className = "neo-particle";
        const angle = Math.random() * Math.PI * 2;
        const distance = 28 + Math.random() * 75;
        p.style.setProperty("--x", Math.cos(angle)*distance + "px");
        p.style.setProperty("--y", Math.sin(angle)*distance + "px");
        p.style.setProperty("--s", (5 + Math.random()*11) + "px");
        p.style.setProperty("--d", (.48 + Math.random()*.55) + "s");
        p.style.setProperty("--r", (-180 + Math.random()*360) + "deg");
        p.style.setProperty("--c", colors[Math.floor(Math.random()*colors.length)]);
        p.style.animationDelay = (Math.random()*.08) + "s";
        burst.appendChild(p);
    }
    document.body.appendChild(burst);

    const ripple = document.createElement("div");
    ripple.className = "neo-ripple";
    ripple.style.left = x + "px";
    ripple.style.top = y + "px";
    ripple.style.borderColor = colors[Math.floor(Math.random()*colors.length)];
    document.body.appendChild(ripple);

    const symbols = ["✦","✦","+","◆","★","↗"];
    if(Math.random() > .28){
        const spark = document.createElement("div");
        spark.className = "neo-spark";
        spark.textContent = symbols[Math.floor(Math.random()*symbols.length)];
        spark.style.left = x + "px";
        spark.style.top = y + "px";
        spark.style.color = colors[Math.floor(Math.random()*colors.length)];
        spark.style.setProperty("--x", (-30 + Math.random()*60) + "px");
        spark.style.setProperty("--y", (-45 - Math.random()*55) + "px");
        spark.style.setProperty("--r", (-25 + Math.random()*50) + "deg");
        document.body.appendChild(spark);
        setTimeout(()=>spark.remove(),900);
    }
    setTimeout(()=>burst.remove(),1200);
    setTimeout(()=>ripple.remove(),800);
}

urlInput.addEventListener("input", () => {
    revealAfterPaste();
    if(urlInput.value.trim()) log("URL entered / pasted");
});

pasteBtn.addEventListener("click", async () => {
    try{
        const text = await navigator.clipboard.readText();
        if(!text.trim()){
            showToast("CLIPBOARD IS EMPTY");
            urlInput.focus();
            return;
        }
        urlInput.value = text.trim();
        revealAfterPaste(true);
        showToast("LINK PASTED");
        log("clipboard URL pasted");
        setTimeout(() => detectMedia(), 180);
    }catch(error){
        urlInput.focus();
        showToast("ALLOW CLIPBOARD OR LONG-PRESS PASTE");
        log("clipboard paste unavailable");
    }
});

refreshBtn.addEventListener("click", () => {
    refreshBtn.animate([
        {transform:"rotate(0deg) scale(1)"},
        {transform:"rotate(360deg) scale(1.12)"},
        {transform:"rotate(720deg) scale(1)"}
    ],{duration:620,easing:"cubic-bezier(.2,.8,.2,1)"});
    setTimeout(() => location.reload(), 260);
});

detectBtn.addEventListener("click", detectMedia);

function renderPreview(data, fallbackUrl){
    thumbBox.innerHTML = "";

    const previewUrl = data.thumbnail || data.preview_url || "";
    const type = String(data.content_type || "").toLowerCase();
    const directUrl = data.final_url || fallbackUrl;

    if(previewUrl){
        const img = document.createElement("img");
        img.src = previewUrl;
        img.alt = "Media thumbnail";
        img.loading = "eager";
        img.referrerPolicy = "no-referrer";
        img.onerror = () => {
            thumbBox.innerHTML = '<div class="preview-empty">THUMBNAIL COULD NOT BE LOADED</div>';
        };
        thumbBox.appendChild(img);
        return;
    }

    if(type.startsWith("image/")){
        const img = document.createElement("img");
        img.src = directUrl;
        img.alt = "Image preview";
        img.loading = "eager";
        img.referrerPolicy = "no-referrer";
        img.onerror = () => {
            thumbBox.innerHTML = '<div class="preview-empty">IMAGE PREVIEW FAILED</div>';
        };
        thumbBox.appendChild(img);
        return;
    }

    if(type.startsWith("video/") && directUrl){
        const video = document.createElement("video");
        video.src = directUrl;
        video.muted = true;
        video.playsInline = true;
        video.preload = "metadata";
        video.setAttribute("aria-label", "Video preview");
        video.addEventListener("loadeddata", () => {
            try { video.currentTime = 0.1; } catch(e) {}
        }, {once:true});
        video.onerror = () => {
            thumbBox.innerHTML = '<div class="preview-empty">VIDEO PREVIEW UNAVAILABLE</div>';
        };
        thumbBox.appendChild(video);
        return;
    }

    const filename = data.filename || data.title || "FILE";
    const ext = (filename.includes(".") ? filename.split(".").pop() : "FILE").toUpperCase();
    thumbBox.innerHTML = '<div class="file-preview"><div><strong>' + ext + '</strong><span>' + filename.replace(/[<>]/g, "_") + '</span></div></div>';
}

urlInput.addEventListener("keydown", event => {
    if(event.key === "Enter"){
        detectMedia();
    }
});

async function detectMedia(){
    const url = urlInput.value.trim();

    if(!validUrl(url)){
        showToast("ENTER A VALID HTTP/HTTPS URL");
        log("detect rejected: invalid URL");
        return;
    }

    setBusy(true);
    transferState.textContent = "CHECKING";
    transferState.style.background = "var(--yellow)";
    setProgress(12,"CONTACTING SERVER");
    log("detect request started");

    try{
        const response = await fetch("/api/inspect",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({url})
        });

        let data = {};
        try{
            data = await response.json();
        }catch{
            throw new Error("Server returned an invalid response (" + response.status + ")");
        }

        if(!response.ok || !data.success){
            throw new Error(data.error || ("Inspection failed (" + response.status + ")"));
        }

        state.detected = true;
        detectedCard.classList.add("show");
        detectedTitle.textContent = data.filename || data.title || "MEDIA RESOURCE";
        detectedType.textContent = "TYPE: " + (data.content_type || "UNKNOWN").toUpperCase();
        detectedSize.textContent = "SIZE: " + formatBytes(data.size);
        detectedHost.textContent = "HOST: " + (data.host || hostOf(url));
        state.qualitySizes = data.quality_sizes || {};
        state.sourceSize = Number(data.size || 0);
        applyDetectedMode(data);
        updateSelectedEstimate();
        renderPreview(data, url);

        transferState.textContent = data.method === "yt-dlp" ? "EXTRACTED" : "READY";
        transferState.style.background = "var(--green)";
        setProgress(100, data.method === "yt-dlp" ? "MEDIA FOUND" : "MEDIA DETECTED");
        log("detect success");
        log("method -> " + (data.method || "direct"));
        log("content-type -> " + (data.content_type || "unknown"));
        log("size -> " + formatBytes(data.size));
        if(data.note) log("note -> " + data.note);
        showToast("MEDIA READY");

    }catch(error){
        state.detected = false;
        state.qualitySizes = {};
        state.sourceSize = 0;
        updateSelectedEstimate();
        detectedCard.classList.remove("show");
        transferState.textContent = "ERROR";
        transferState.style.background = "var(--pink)";
        setProgress(0,"DETECTION FAILED");
        log("detect error -> " + error.message);
        showToast("DETECTION FAILED");
    }finally{
        setBusy(false);
    }
}

downloadBtn.addEventListener("click", startDownload);

async function startDownload(){
    const url = urlInput.value.trim();
    if(!validUrl(url)){
        showToast("PASTE A VALID MEDIA URL FIRST");
        return;
    }

    setBusy(true);
    transferState.textContent = "PREPARING";
    transferState.style.background = "var(--orange)";
    setProgress(5,"DOWNLOADING IN BACKGROUND");
    log("background prepare started");

    const payload = {
        url,
        mode: modeSelect.value,
        format: formatSelect.value,
        quality: state.quality
    };

    try{
        const response = await fetch("/api/prepare", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify(payload)
        });
        const data = await response.json();
        if(!response.ok || !data.success) throw new Error(data.error || "Background download failed");

        setProgress(100,"DOWNLOAD READY");
        transferState.textContent = "READY";
        transferState.style.background = "var(--green)";
        log("background download complete -> " + data.filename);

        const go = confirm("DOWNLOAD READY\n\n" + data.filename + "\n" + formatBytes(data.size) + "\n\nPress OK to send it to Chrome Downloads.");
        if(go){
            const link = document.createElement("a");
            link.href = data.download_url;
            link.download = data.filename || "download";
            link.rel = "noopener";
            document.body.appendChild(link);
            link.click();
            link.remove();
            addHistory(url, data.filename || "Download");
            showToast("SENT TO CHROME DOWNLOADS");
            log("browser download triggered");
        }else{
            showToast("DOWNLOAD KEPT READY");
        }
    }catch(error){
        transferState.textContent = "ERROR";
        transferState.style.background = "var(--pink)";
        setProgress(0,"DOWNLOAD FAILED");
        log("download error -> " + error.message);
        showToast("DOWNLOAD FAILED");
    }finally{
        setBusy(false);
    }
}

function getHistory(){
    try{
        return JSON.parse(localStorage.getItem("neoDropHistory") || "[]");
    }catch{
        return [];
    }
}

function saveHistory(items){
    localStorage.setItem("neoDropHistory",JSON.stringify(items.slice(0,20)));
}

function addHistory(url,name){
    const items = getHistory();
    items.unshift({
        url,
        name,
        time:new Date().toLocaleString()
    });
    saveHistory(items);
    renderHistory();
}

function renderHistory(){
    const items = getHistory();

    if(!items.length){
        historyList.innerHTML = `
            <div class="history-item">
                <div>
                    <div class="history-url">No downloads in this session.</div>
                    <div class="history-time">History stays in this browser.</div>
                </div>
            </div>
        `;
        return;
    }

    historyList.innerHTML = items.map((item,index) => `
        <div class="history-item">
            <div>
                <div class="history-url" title="${escapeHtml(item.url)}">${escapeHtml(item.name)}</div>
                <div class="history-time">${escapeHtml(item.time)} · ${escapeHtml(item.url)}</div>
            </div>
            <div class="history-actions">
                <button class="secondary" data-copy="${index}">COPY URL</button>
            </div>
        </div>
    `).join("");

    historyList.querySelectorAll("[data-copy]").forEach(button => {
        button.addEventListener("click",async() => {
            const item = items[Number(button.dataset.copy)];
            try{
                await navigator.clipboard.writeText(item.url);
                showToast("URL COPIED");
            }catch{
                showToast("COPY NOT AVAILABLE");
            }
        });
    });
}

function escapeHtml(value){
    return String(value)
        .replaceAll("&","&amp;")
        .replaceAll("<","&lt;")
        .replaceAll(">","&gt;")
        .replaceAll('"',"&quot;")
        .replaceAll("'","&#039;");
}

$("#clearHistoryBtn").addEventListener("click",() => {
    localStorage.removeItem("neoDropHistory");
    renderHistory();
    showToast("HISTORY CLEARED");
});

$("#historyBtn").addEventListener("click",() => {
    $("#historySection").scrollIntoView({behavior:"smooth"});
});

$("#helpBtn").addEventListener("click",() => {
    $("#helpModal").classList.add("show");
});

$("#closeHelp").addEventListener("click",() => {
    $("#helpModal").classList.remove("show");
});

$("#modalOk").addEventListener("click",() => {
    $("#helpModal").classList.remove("show");
});

$("#helpModal").addEventListener("click",event => {
    if(event.target.id === "helpModal"){
        $("#helpModal").classList.remove("show");
    }
});

$("#themeBtn").addEventListener("click",() => {
    const inverted = document.body.dataset.inverted === "1";

    if(!inverted){
        document.body.dataset.inverted = "1";
        document.documentElement.style.setProperty("--paper","#171717");
        document.documentElement.style.setProperty("--ink","#f8f8f8");
        document.documentElement.style.setProperty("--white","#222");
        showToast("INVERT MODE");
    }else{
        document.body.dataset.inverted = "0";
        document.documentElement.style.setProperty("--paper","#f5f0df");
        document.documentElement.style.setProperty("--ink","#101010");
        document.documentElement.style.setProperty("--white","#fffdf4");
        showToast("NORMAL MODE");
    }
});

document.addEventListener("click", event => {
    if(event.clientX < 0 || event.clientY < 0) return;
    randomClickAnimation(event.clientX,event.clientY);
});

async function checkServer(){
    try{
        const response = await fetch("/api/health");
        if(response.ok){
            $("#connectionTag").textContent = "SERVER ONLINE";
            $("#connectionTag").style.background = "var(--green)";
            log("server health -> online");
        }else{
            throw new Error("offline");
        }
    }catch{
        $("#connectionTag").textContent = "SERVER OFFLINE";
        $("#connectionTag").style.background = "var(--pink)";
        log("server health -> offline");
    }
}

setStatus();
renderHistory();
revealAfterPaste();
checkServer();
</script>

</body>
</html>

<!-- NEO-DROP EXTENSION SLOT 1442: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1443: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1444: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1445: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1446: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1447: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1448: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1449: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1450: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1451: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1452: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1453: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1454: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1455: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1456: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1457: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1458: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1459: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1460: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1461: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1462: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1463: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1464: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1465: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1466: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1467: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1468: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1469: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1470: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1471: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1472: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1473: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1474: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1475: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1476: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1477: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1478: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1479: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1480: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1481: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1482: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1483: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1484: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1485: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1486: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1487: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1488: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1489: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1490: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1491: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1492: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1493: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1494: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1495: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1496: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1497: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1498: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1499: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1500: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1501: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1502: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1503: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1504: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1505: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1506: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1507: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1508: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1509: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1510: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1511: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1512: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1513: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1514: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1515: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1516: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1517: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1518: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1519: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1520: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1521: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1522: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1523: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1524: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1525: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1526: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1527: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1528: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1529: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1530: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1531: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1532: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1533: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1534: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1535: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1536: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1537: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1538: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1539: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1540: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1541: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1542: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1543: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1544: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1545: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1546: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1547: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1548: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1549: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1550: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1551: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1552: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1553: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1554: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1555: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1556: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1557: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1558: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1559: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1560: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1561: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1562: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1563: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1564: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1565: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1566: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1567: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1568: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1569: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1570: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1571: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1572: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1573: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1574: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1575: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1576: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1577: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1578: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1579: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1580: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1581: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1582: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1583: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1584: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1585: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1586: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1587: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1588: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1589: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1590: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1591: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1592: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1593: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1594: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1595: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1596: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1597: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1598: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1599: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1600: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1601: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1602: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1603: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1604: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1605: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1606: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1607: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1608: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1609: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1610: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1611: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1612: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1613: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1614: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1615: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1616: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1617: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1618: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1619: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1620: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1621: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1622: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1623: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1624: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1625: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1626: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1627: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1628: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1629: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1630: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1631: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1632: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1633: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1634: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1635: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1636: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1637: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1638: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1639: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1640: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1641: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1642: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1643: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1644: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1645: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1646: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1647: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1648: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1649: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1650: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1651: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1652: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1653: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1654: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1655: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1656: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1657: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1658: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1659: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1660: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1661: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1662: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1663: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1664: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1665: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1666: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1667: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1668: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1669: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1670: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1671: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1672: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1673: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1674: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1675: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1676: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1677: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1678: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1679: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1680: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1681: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1682: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1683: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1684: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1685: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1686: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1687: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1688: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1689: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1690: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1691: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1692: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1693: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1694: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1695: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1696: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1697: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1698: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1699: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1700: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1701: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1702: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1703: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1704: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1705: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1706: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1707: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1708: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1709: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1710: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1711: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1712: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1713: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1714: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1715: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1716: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1717: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1718: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1719: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1720: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1721: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1722: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1723: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1724: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1725: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1726: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1727: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1728: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1729: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1730: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1731: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1732: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1733: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1734: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1735: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1736: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1737: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1738: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1739: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1740: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1741: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1742: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1743: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1744: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1745: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1746: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1747: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1748: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1749: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1750: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1751: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1752: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1753: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1754: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1755: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1756: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1757: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1758: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1759: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1760: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1761: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1762: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1763: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1764: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1765: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1766: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1767: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1768: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1769: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1770: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1771: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1772: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1773: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1774: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1775: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1776: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1777: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1778: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1779: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1780: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1781: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1782: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1783: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1784: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1785: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1786: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1787: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1788: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1789: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1790: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1791: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1792: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1793: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1794: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1795: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1796: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1797: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1798: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1799: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1800: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1801: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1802: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1803: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1804: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1805: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1806: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1807: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1808: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1809: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1810: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1811: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1812: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1813: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1814: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1815: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1816: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1817: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1818: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1819: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1820: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1821: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1822: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1823: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1824: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1825: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1826: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1827: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1828: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1829: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1830: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1831: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1832: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1833: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1834: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1835: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1836: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1837: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1838: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1839: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1840: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1841: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1842: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1843: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1844: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1845: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1846: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1847: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1848: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1849: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1850: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1851: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1852: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1853: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1854: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1855: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1856: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1857: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1858: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1859: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1860: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1861: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1862: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1863: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1864: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1865: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1866: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1867: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1868: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1869: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1870: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1871: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1872: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1873: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1874: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1875: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1876: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1877: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1878: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1879: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1880: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1881: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1882: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1883: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1884: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1885: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1886: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1887: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1888: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1889: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1890: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1891: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1892: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1893: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1894: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1895: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1896: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1897: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1898: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1899: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1900: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1901: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1902: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1903: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1904: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1905: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1906: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1907: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1908: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1909: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1910: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1911: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1912: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1913: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1914: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1915: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1916: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1917: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1918: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1919: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1920: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1921: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1922: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1923: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1924: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1925: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1926: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1927: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1928: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1929: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1930: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1931: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1932: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1933: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1934: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1935: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1936: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1937: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1938: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1939: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1940: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1941: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1942: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1943: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1944: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1945: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1946: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1947: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1948: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1949: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1950: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1951: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1952: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1953: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1954: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1955: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1956: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1957: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1958: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1959: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1960: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1961: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1962: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1963: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1964: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1965: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1966: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1967: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1968: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1969: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1970: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1971: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1972: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1973: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1974: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1975: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1976: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1977: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1978: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1979: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1980: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1981: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1982: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1983: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1984: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1985: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1986: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1987: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1988: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1989: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1990: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1991: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1992: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1993: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1994: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1995: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1996: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1997: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1998: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 1999: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2000: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2001: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2002: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2003: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2004: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2005: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2006: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2007: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2008: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2009: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2010: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2011: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2012: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2013: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2014: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2015: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2016: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2017: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2018: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2019: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2020: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2021: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2022: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2023: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2024: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2025: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2026: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2027: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2028: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2029: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2030: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2031: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2032: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2033: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2034: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2035: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2036: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2037: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2038: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2039: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2040: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2041: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2042: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2043: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2044: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2045: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2046: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2047: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2048: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2049: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2050: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2051: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2052: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2053: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2054: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2055: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2056: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2057: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2058: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2059: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2060: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2061: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2062: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2063: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2064: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2065: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2066: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2067: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2068: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2069: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2070: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2071: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2072: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2073: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2074: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2075: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2076: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2077: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2078: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2079: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2080: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2081: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2082: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2083: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2084: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2085: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2086: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2087: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2088: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2089: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2090: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2091: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2092: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2093: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2094: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2095: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2096: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2097: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2098: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2099: reserved for future UI modules, accessibility notes, and maintenance documentation. -->
<!-- NEO-DROP EXTENSION SLOT 2100: reserved for future UI modules, accessibility notes, and maintenance documentation. -->

"""


# ============================================================
# HELPERS / ROBUST MEDIA BACKEND
# ============================================================
ALLOWED_MEDIA_PREFIXES = ("video/", "audio/", "image/")
ALLOWED_DIRECT_EXTENSIONS = {
    ".mp4", ".webm", ".mov", ".m4v", ".mkv",
    ".mp3", ".m4a", ".aac", ".wav", ".ogg", ".oga", ".flac",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif",
    ".pdf", ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".apk", ".aab", ".txt", ".csv", ".json", ".xml", ".html",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".epub"
}

MIME_BY_EXT = {
    ".mp4": "video/mp4", ".webm": "video/webm",
    ".mov": "video/quicktime", ".m4v": "video/mp4",
    ".mkv": "video/x-matroska", ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".wav": "audio/wav", ".ogg": "audio/ogg",
    ".oga": "audio/ogg", ".flac": "audio/flac",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp", ".avif": "image/avif",
    ".pdf": "application/pdf", ".zip": "application/zip", ".rar": "application/vnd.rar",
    ".7z": "application/x-7z-compressed", ".tar": "application/x-tar", ".gz": "application/gzip",
    ".bz2": "application/x-bzip2", ".apk": "application/vnd.android.package-archive",
    ".aab": "application/octet-stream", ".txt": "text/plain", ".csv": "text/csv",
    ".json": "application/json", ".xml": "application/xml", ".html": "text/html",
    ".doc": "application/msword", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".epub": "application/epub+zip"
}

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0 Mobile Safari/537.36 NeoDrop/2.0"
)

def is_http_url(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False

def safe_filename(value, fallback="download"):
    value = (value or "").strip()
    value = re.sub(r"[^a-zA-Z0-9._ -]+", "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:120] or fallback

def extension_from_url(url):
    try:
        return Path(urlparse(url).path.lower()).suffix
    except Exception:
        return ""

def extension_from_content_type(content_type):
    clean = (content_type or "").split(";", 1)[0].lower().strip()
    for ext, mime in MIME_BY_EXT.items():
        if mime == clean:
            return ext
    return ""

def filename_from_response(response):
    header = response.headers.get("Content-Disposition", "")
    match = re.search(r"filename\*=[^']*''([^;]+)", header, flags=re.I)
    if match:
        return Path(unquote(match.group(1).strip().strip('"'))).name
    match = re.search(r'filename\s*=\s*"([^"]+)"', header, flags=re.I)
    if match:
        return Path(match.group(1)).name
    match = re.search(r"filename\s*=\s*([^;]+)", header, flags=re.I)
    if match:
        return Path(unquote(match.group(1).strip().strip('"'))).name
    return Path(urlparse(response.url).path).name

def sniff_mime(data):
    """Best-effort file signature detection for extensionless/CDN download URLs."""
    if not data:
        return ""
    b = bytes(data[:65536])

    # Images
    if b.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if b.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if b.startswith((b"GIF87a", b"GIF89a")): return "image/gif"
    if len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP": return "image/webp"
    if b.startswith(b"BM"): return "image/bmp"
    if len(b) >= 12 and b[4:12] == b"ftypavif": return "image/avif"

    # Documents / archives
    if b.startswith(b"%PDF-"): return "application/pdf"
    if b.startswith(b"Rar!\x1a\x07"): return "application/vnd.rar"
    if b.startswith(b"7z\xbc\xaf\x27\x1c"): return "application/x-7z-compressed"
    if b.startswith(b"\x1f\x8b"): return "application/gzip"

    # ZIP-family files. APK/AAB are ZIP containers, so inspect their entries
    # when the server gives us an extensionless application/octet-stream URL.
    if b.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        if b"AndroidManifest.xml" in b and b"classes.dex" in b:
            return "application/vnd.android.package-archive"
        if b"base/manifest/AndroidManifest.xml" in b:
            return "application/x-android-app-bundle"
        if b"word/" in b and b"[Content_Types].xml" in b:
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if b"xl/" in b and b"[Content_Types].xml" in b:
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if b"ppt/" in b and b"[Content_Types].xml" in b:
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        if b"META-INF/container.xml" in b:
            return "application/epub+zip"
        return "application/zip"

    # Audio
    if b.startswith(b"ID3") or (len(b) >= 2 and b[0] == 0xff and (b[1] & 0xe0) == 0xe0): return "audio/mpeg"
    if b.startswith(b"RIFF") and len(b) >= 12 and b[8:12] == b"WAVE": return "audio/wav"
    if b.startswith(b"fLaC"): return "audio/flac"
    if b.startswith(b"OggS"): return "audio/ogg"

    # Video / media containers
    if len(b) >= 12 and b[4:8] == b"ftyp": return "video/mp4"
    if b.startswith(b"\x1a\x45\xdf\xa3"): return "video/x-matroska"
    return ""

def extension_for_detected_mime(content_type):
    """Map a detected MIME to a real download extension."""
    return extension_from_content_type(content_type) or {
        "application/vnd.android.package-archive": ".apk",
        "application/x-android-app-bundle": ".aab",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/epub+zip": ".epub",
        "application/octet-stream": "",
    }.get(clean_content_type(content_type), "")

def normalize_detected_filename(filename, content_type, fallback_stem="download"):
    """Never expose names such as unknown_video when a format is known."""
    raw = Path(filename or "").name
    stem = Path(raw).stem if raw else fallback_stem
    suffix = Path(raw).suffix.lower() if raw else ""
    ext = extension_for_detected_mime(content_type)
    if suffix in ALLOWED_DIRECT_EXTENSIONS:
        ext = suffix
    if not ext:
        return safe_filename(stem or fallback_stem, fallback_stem)
    return safe_filename(stem or fallback_stem, fallback_stem) + ext

def mime_from_extension(ext):
    return MIME_BY_EXT.get((ext or "").lower(), "application/octet-stream")

def clean_content_type(value):
    return (value or "").split(";", 1)[0].lower().strip()

def direct_headers():
    return {
        "User-Agent": USER_AGENT,
        "Accept": "video/*,audio/*,image/*,application/octet-stream,*/*;q=0.2",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    }

def upstream(url, range_probe=False):
    headers = direct_headers()
    if range_probe:
        headers["Range"] = "bytes=0-8191"
    return requests.get(
        url, headers=headers, stream=True,
        allow_redirects=True, timeout=TIMEOUT
    )

def validate_media(response):
    content_type = clean_content_type(response.headers.get("Content-Type", ""))
    ext = extension_from_url(response.url)
    disposition_name = filename_from_response(response)
    disposition_ext = Path(disposition_name).suffix.lower() if disposition_name else ""

    if content_type.startswith(ALLOWED_MEDIA_PREFIXES):
        return content_type

    generic = content_type in {"", "application/octet-stream", "binary/octet-stream"}
    if generic:
        if ext in ALLOWED_DIRECT_EXTENSIONS:
            return mime_from_extension(ext)
        if disposition_ext in ALLOWED_DIRECT_EXTENSIONS:
            return mime_from_extension(disposition_ext)

        # Some CDN/release links intentionally use a UUID or an extensionless
        # path and application/octet-stream. The first bytes still reveal many
        # common media/file formats without downloading the whole file.
        try:
            sample = response.raw.read(8192)
            sniffed = sniff_mime(sample)
            if sniffed:
                return sniffed
            # It is still a legitimate direct binary response when the server
            # explicitly advertises octet-stream. Keep it as a generic FILE so
            # APK/archives/custom binaries download unchanged.
            if content_type in {"application/octet-stream", "binary/octet-stream"}:
                return "application/octet-stream"
        except Exception:
            pass
    return None

def response_size(response):
    value = response.headers.get("Content-Length")
    if value and value.isdigit():
        return int(value)
    match = re.search(r"/(\d+)$", response.headers.get("Content-Range", ""))
    return int(match.group(1)) if match else 0

def direct_probe(url):
    response = None
    try:
        response = upstream(url, range_probe=True)
        if response.status_code >= 400:
            return {"ok": False, "error": f"Source returned HTTP {response.status_code}."}

        final_url = response.url
        response_filename = filename_from_response(response)
        content_type = validate_media(response)
        size = response_size(response)

        if content_type:
            raw_name = response_filename or Path(urlparse(final_url).path).name or "download"
            detected_filename = normalize_detected_filename(
                raw_name, content_type,
                fallback_stem=Path(urlparse(final_url).path).stem or "download"
            )
            return {
                "ok": True, "method": "direct", "url": final_url,
                "content_type": content_type, "size": size,
                "filename": detected_filename,
                "host": urlparse(final_url).hostname or "",
                "media_mode": (
                    "video" if content_type.startswith("video/") else
                    "photo" if content_type.startswith("image/") else
                    "audio" if content_type.startswith("audio/") else
                    "file"
                )
            }

        return {
            "ok": False,
            "error": "The URL returned a webpage instead of a direct media file.",
            "html_page": True
        }
    except requests.RequestException as exc:
        return {"ok": False, "error": f"Could not reach source: {exc}"}
    finally:
        if response is not None:
            response.close()

def page_media_probe(url):
    """Public-page fallback: use OpenGraph media advertised by the page.
    This helps Instagram photo/video pages when their public HTML exposes og:image/og:video.
    It does not bypass login, private posts, DRM, or access controls."""
    try:
        r = requests.get(url, headers=direct_headers(), stream=True, allow_redirects=True, timeout=(10, 25))
        if r.status_code >= 400:
            r.close()
            return None
        ctype = clean_content_type(r.headers.get("Content-Type", ""))
        if "html" not in ctype:
            r.close()
            return None
        raw = r.raw.read(2 * 1024 * 1024)
        r.close()
        text = raw.decode("utf-8", errors="ignore")
        def meta(*properties):
            for prop in properties:
                pat = re.compile(r'<meta[^>]+(?:property|name)=["\\\']' + re.escape(prop) + r'["\\\'][^>]+content=["\\\']([^"\\\']+)', re.I)
                m = pat.search(text)
                if m:
                    return html_lib.unescape(m.group(1))
            return ""
        media_url = meta("og:video:secure_url", "og:video", "og:video:url", "twitter:player:stream")
        image_url = meta("og:image:secure_url", "og:image", "twitter:image")
        title = meta("og:title", "twitter:title")
        chosen = media_url or image_url
        if not chosen:
            return None
        chosen = chosen.replace("&amp;", "&")
        parsed = urlparse(chosen)
        if not parsed.scheme:
            chosen = requests.compat.urljoin(r.url if hasattr(r, "url") else url, chosen)
        direct = direct_probe(chosen)
        if not direct.get("ok"):
            return None
        if title:
            direct["title"] = title
        direct["method"] = "page-meta"
        direct["page_url"] = url
        return direct
    except requests.RequestException:
        return None
    except Exception:
        return None

def yt_dlp_command():
    for name in ("yt-dlp", "yt-dlp.exe"):
        path = shutil.which(name)
        if path:
            return [path]
    # Also support installations made with: python -m pip install yt-dlp
    try:
        probe = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True, text=True, timeout=10, check=False
        )
        if probe.returncode == 0:
            return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        pass
    return None

def yt_dlp_available():
    return yt_dlp_command() is not None

def run_ytdlp_info(url):
    if not yt_dlp_available():
        return None, "yt-dlp is not installed"

    base = yt_dlp_command()
    if not base:
        return None, "yt-dlp is not installed. Install it with: python -m pip install -U yt-dlp"
    command = base + [
        "--no-warnings", "--skip-download", "--no-playlist",
        "--extractor-retries", "3", "--retries", "3", "--fragment-retries", "3",
        "--socket-timeout", "20", "--add-header", "User-Agent:" + USER_AGENT,
        "--referer", url, "--dump-single-json", url
    ]
    try:
        proc = subprocess.run(
            command, capture_output=True, text=True,
            timeout=45, check=False
        )
    except Exception as exc:
        return None, str(exc)

    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout or "yt-dlp inspection failed")[-700:]

    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError:
        return None, "yt-dlp returned invalid metadata"

def ytdlp_quality_sizes(info):
    """Return best-known approximate download sizes for common quality caps.
    Uses yt-dlp's filesize/filesize_approx metadata when the site exposes it.
    A value of 0 means the site did not expose enough size information.
    """
    formats = info.get("formats") or []
    result = {}
    for label, cap in (("360p",360),("480p",480),("720p",720),("1080p",1080),("1440p",1440)):
        candidates = []
        for f in formats:
            h = f.get("height")
            if not isinstance(h, (int, float)) or h <= 0 or h > cap:
                continue
            size = f.get("filesize") or f.get("filesize_approx") or 0
            try: size = int(size)
            except Exception: size = 0
            if size <= 0: continue
            vcodec = f.get("vcodec") or "none"
            acodec = f.get("acodec") or "none"
            candidates.append((h, size, vcodec != "none", acodec != "none"))
        if not candidates:
            result[label] = 0
            continue
        muxed = [x for x in candidates if x[2] and x[3]]
        if muxed:
            best = max(muxed, key=lambda x: (x[0], x[1]))
            result[label] = best[1]
            continue
        video = [x for x in candidates if x[2]]
        audio = [x for x in candidates if x[3]]
        best_v = max(video, key=lambda x: (x[0], x[1]))[1] if video else 0
        best_a = max(audio, key=lambda x: x[1])[1] if audio else 0
        result[label] = best_v + best_a
    source = info.get("filesize") or info.get("filesize_approx") or 0
    try: result["source"] = int(source)
    except Exception: result["source"] = 0
    return result

def ytdlp_filename(info):
    title = safe_filename(info.get("title") or "download")
    ext = (info.get("ext") or "mp4").lower()
    return f"{title}.{ext}"

def ytdlp_mime(info):
    return mime_from_extension("." + (info.get("ext") or "mp4").lower())

def run_ytdlp_download(url, requested_format, quality, requested_name):
    base = yt_dlp_command()
    if not base:
        return None, "yt-dlp is not installed. Install it with: python -m pip install -U yt-dlp"

    requested_format = (requested_format or "original").lower()
    quality = (quality or "source").lower()

    # Thumbnail is a real image output, not a video renamed as an image.
    if requested_format == "thumbnail":
        temp_dir = Path(tempfile.mkdtemp(prefix="neo_drop_thumb_"))
        output_template = str(temp_dir / "%(title).120B.%(ext)s")
        command = base + [
            "--no-warnings", "--no-playlist", "--skip-download",
            "--write-thumbnail", "--convert-thumbnails", "jpg",
            "-o", output_template, url
        ]
        try:
            proc = subprocess.run(command, capture_output=True, text=True,
                                  timeout=180, check=False)
            if proc.returncode != 0:
                error = (proc.stderr or proc.stdout or "Thumbnail download failed")[-900:]
                return None, error
            files = [x for x in temp_dir.iterdir() if x.is_file() and x.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
            if not files:
                return None, "No thumbnail image was produced."
            output = files[0]
            if output.stat().st_size > MAX_FILE_SIZE:
                return None, "Thumbnail is larger than 500 MB."
            stem = safe_filename(requested_name, "thumbnail") if requested_name else "thumbnail"
            if Path(stem).suffix:
                stem = Path(stem).stem
            return {
                "data": output.read_bytes(),
                "filename": safe_filename(stem, "thumbnail") + ".jpg",
                "content_type": "image/jpeg"
            }, None
        except subprocess.TimeoutExpired:
            return None, "Thumbnail extraction timed out."
        except Exception as exc:
            return None, str(exc)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    quality_map = {
        "360p": "bestvideo*[height<=360]+bestaudio/best[height<=360]/best",
        "480p": "bestvideo*[height<=480]+bestaudio/best[height<=480]/best",
        "720p": "bestvideo*[height<=720]+bestaudio/best[height<=720]/best",
        "1080p": "bestvideo*[height<=1080]+bestaudio/best[height<=1080]/best",
        "1440p": "bestvideo*[height<=1440]+bestaudio/best[height<=1440]/best",
        "source": "bestvideo*+bestaudio/best"
    }
    fmt = quality_map.get(quality, quality_map["source"])
    if requested_format == "mp3":
        fmt = "bestaudio/best"
    elif requested_format == "webm":
        fmt = "bestvideo*[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best"

    temp_dir = Path(tempfile.mkdtemp(prefix="neo_drop_"))
    output_template = str(temp_dir / "%(title).120B.%(ext)s")
    command = base + [
        "--no-warnings", "--no-playlist", "--restrict-filenames",
        "--extractor-retries", "3", "--retries", "3", "--fragment-retries", "3",
        "--socket-timeout", "20", "--add-header", "User-Agent:" + USER_AGENT,
        "--referer", url, "-f", fmt, "-o", output_template, url
    ]

    ffmpeg = shutil.which("ffmpeg")
    if requested_format in {"mp4", "webm", "mp3"} and not ffmpeg:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, f"{requested_format.upper()} output needs ffmpeg. Install ffmpeg first."
    if requested_format == "mp4":
        command += ["--merge-output-format", "mp4"]
    elif requested_format == "webm":
        command += ["--merge-output-format", "webm"]
    elif requested_format == "mp3":
        command += ["-x", "--audio-format", "mp3"]

    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=900, check=False)
        if proc.returncode != 0:
            error = (proc.stderr or proc.stdout or "yt-dlp download failed")[-1200:]
            return None, error

        files = [x for x in temp_dir.iterdir() if x.is_file()]
        if not files:
            return None, "No output media file was produced."
        output = max(files, key=lambda x: x.stat().st_size)
        if output.stat().st_size > MAX_FILE_SIZE:
            return None, "Downloaded file is larger than 500 MB."

        ext = output.suffix.lower()
        stem = safe_filename(requested_name, output.stem) if requested_name else output.stem
        if Path(stem).suffix:
            stem = Path(stem).stem
        return {
            "data": output.read_bytes(),
            "filename": safe_filename(stem, "download") + ext,
            "content_type": mime_from_extension(ext)
        }, None
    except subprocess.TimeoutExpired:
        return None, "Media extraction timed out."
    except Exception as exc:
        return None, str(exc)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def make_direct_filename(final_url, requested_name, content_type, source_filename=""):
    original = Path(source_filename or Path(urlparse(final_url).path).name)
    original_name = original.name or "download"
    ext = original.suffix.lower() or extension_from_url(final_url) or extension_from_content_type(content_type)
    stem = original.stem or "download"
    if requested_name:
        stem = safe_filename(requested_name, stem)
        if Path(stem).suffix:
            stem = Path(stem).stem
    result = safe_filename(stem, "download")
    return result + ext


def cleanup_prepared():
    now = time.time()
    for token, item in list(PREPARED.items()):
        if now - item.get("created", now) > PREPARE_TTL:
            try:
                shutil.rmtree(item["dir"], ignore_errors=True)
            except Exception:
                pass
            PREPARED.pop(token, None)


def parallel_range_download(url, target, total, workers=PARALLEL_CHUNKS):
    """Download a known-size direct resource in independent byte ranges.
    Falls back to normal streaming when the origin does not honor Range."""
    if total <= 0 or total < 4 * CHUNK_SIZE:
        return False

    probe = None
    try:
        probe = upstream(url, range_probe=True)
        if probe.status_code != 206 or not probe.headers.get("Content-Range"):
            return False
        content_range = probe.headers.get("Content-Range", "")
        if not content_range.startswith("bytes "):
            return False
    finally:
        if probe is not None:
            probe.close()

    workers = max(2, min(int(workers), 8))
    ranges = []
    part = (total + workers - 1) // workers
    start = 0
    while start < total:
        end = min(total - 1, start + part - 1)
        ranges.append((start, end))
        start = end + 1

    with target.open("wb") as fh:
        fh.truncate(total)

    def fetch_range(item):
        start, end = item
        headers = direct_headers()
        headers["Range"] = f"bytes={start}-{end}"
        r = requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=TIMEOUT)
        if r.status_code != 206:
            r.close()
            raise RuntimeError(f"Range request returned HTTP {r.status_code}")
        offset = start
        try:
            with target.open("r+b") as fh:
                fh.seek(offset)
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        fh.write(chunk)
                        offset += len(chunk)
            if offset != end + 1:
                raise RuntimeError("Range response ended before the expected byte count")
            return True
        finally:
            r.close()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch_range, item) for item in ranges]
        for future in as_completed(futures):
            future.result()
    return target.stat().st_size == total


def download_direct_to_file(final_url, total, source_ext, content_type, target):
    if total and parallel_range_download(final_url, target, total):
        return
    response = upstream(final_url)
    if response.status_code >= 400:
        code = response.status_code
        response.close()
        raise RuntimeError(f"Source returned HTTP {code} during download.")
    received = 0
    try:
        with target.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue
                received += len(chunk)
                if received > MAX_FILE_SIZE:
                    raise RuntimeError("Source exceeded 500 MB.")
                fh.write(chunk)
    finally:
        response.close()
    if target.stat().st_size > MAX_FILE_SIZE:
        raise RuntimeError("Source file is larger than 500 MB.")


def prepare_download(data):
    cleanup_prepared()
    url = str(data.get("url", "")).strip()
    requested_format = str(data.get("format", "original")).lower().strip()
    quality = str(data.get("quality", "source")).lower().strip()
    requested_name = str(data.get("filename", "")).strip()
    if not is_http_url(url):
        return None, "A valid HTTP/HTTPS URL is required."
    if requested_format not in {"original", "mp4", "webm", "mp3", "thumbnail"}:
        return None, "Unsupported output format."

    direct = direct_probe(url)
    temp_dir = Path(tempfile.mkdtemp(prefix="neo_drop_prepare_", dir=PREPARED_DIR))
    try:
        if direct["ok"]:
            final_url = direct["url"]
            content_type = direct["content_type"]
            source_ext = extension_from_url(final_url) or extension_from_content_type(content_type)
            total = int(direct.get("size") or 0)
            if total > MAX_FILE_SIZE:
                raise RuntimeError("Source file is larger than 500 MB.")

            if requested_format == "thumbnail":
                if content_type.startswith("image/"):
                    requested_format = "original"
                elif content_type.startswith("video/"):
                    ffmpeg = shutil.which("ffmpeg")
                    if not ffmpeg: raise RuntimeError("Video thumbnail needs ffmpeg. Install ffmpeg first.")
                    source_file = temp_dir / ("source" + (source_ext or ".bin"))
                    download_direct_to_file(final_url, total, source_ext, content_type, source_file)
                    output_file = temp_dir / "thumbnail.jpg"
                    proc = subprocess.run([ffmpeg,"-y","-ss","0.5","-i",str(source_file),"-frames:v","1","-q:v","2",str(output_file)], capture_output=True, text=True, timeout=180, check=False)
                    if proc.returncode != 0 or not output_file.exists(): raise RuntimeError((proc.stderr or "Thumbnail extraction failed")[-1000:])
                    filename = safe_filename(requested_name or Path(urlparse(final_url).path).stem or "thumbnail", "thumbnail")
                    if Path(filename).suffix: filename = Path(filename).stem
                    return {"file":output_file,"filename":filename+".jpg","content_type":"image/jpeg","dir":temp_dir}, None

            direct_matches = (
                requested_format == "original"
                or (requested_format == "mp4" and (source_ext == ".mp4" or content_type == "video/mp4"))
                or (requested_format == "webm" and (source_ext == ".webm" or content_type == "video/webm"))
                or (requested_format == "mp3" and (source_ext == ".mp3" or content_type == "audio/mpeg"))
            )
            if direct_matches:
                output_file = temp_dir / (make_direct_filename(final_url, requested_name, content_type, direct.get("filename", "")))
                download_direct_to_file(final_url, total, source_ext, content_type, output_file)
                return {"file":output_file,"filename":output_file.name,"content_type":content_type,"dir":temp_dir}, None

            ffmpeg = shutil.which("ffmpeg")
            if requested_format not in {"mp4","webm","mp3"} or not ffmpeg:
                raise RuntimeError("This output needs ffmpeg. Choose ORIGINAL/DIRECT or install ffmpeg.")
            source_file = temp_dir / ("source" + (source_ext or ".bin"))
            download_direct_to_file(final_url, total, source_ext, content_type, source_file)
            out_ext = "." + requested_format
            output_file = temp_dir / ("converted" + out_ext)
            command = [ffmpeg,"-y","-i",str(source_file)]
            if requested_format == "mp3": command += ["-vn","-codec:a","libmp3lame","-q:a","2"]
            elif requested_format == "mp4": command += ["-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-movflags","+faststart"]
            else: command += ["-c:v","libvpx-vp9","-c:a","libopus","-deadline","realtime"]
            command += [str(output_file)]
            proc = subprocess.run(command,capture_output=True,text=True,timeout=900,check=False)
            if proc.returncode != 0 or not output_file.exists(): raise RuntimeError((proc.stderr or "ffmpeg conversion failed")[-1200:])
            filename = safe_filename(requested_name or output_file.stem, "download")
            if Path(filename).suffix: filename = Path(filename).stem
            final_file = temp_dir / (filename + out_ext)
            if output_file != final_file: output_file.replace(final_file); output_file = final_file
            return {"file":output_file,"filename":output_file.name,"content_type":mime_from_extension(out_ext),"dir":temp_dir}, None

        result, error = run_ytdlp_download(url, requested_format, quality, requested_name)
        if not result:
            raise RuntimeError(error or direct.get("error") or "Download failed.")
        output_file = temp_dir / result["filename"]
        output_file.write_bytes(result["data"])
        return {"file":output_file,"filename":result["filename"],"content_type":result["content_type"],"dir":temp_dir}, None
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, str(exc)

# ============================================================
# ROUTES
# ============================================================
@app.get("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")

@app.get("/api/health")
def health():
    return jsonify({
        "success": True,
        "service": "NEO-DROP",
        "status": "online",
        "yt_dlp": yt_dlp_available(),
        "max_file_mb": MAX_FILE_SIZE // (1024 * 1024)
    })

@app.post("/api/inspect")
def inspect():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()

    if not is_http_url(url):
        return jsonify({"success": False, "error": "A valid HTTP/HTTPS URL is required."}), 400

    direct = direct_probe(url)
    if direct["ok"]:
        if direct["size"] and direct["size"] > MAX_FILE_SIZE:
            return jsonify({"success": False, "error": "Source file is larger than 500 MB."}), 413
        return jsonify({
            "success": True,
            "method": "direct",
            "filename": direct["filename"],
            "content_type": direct["content_type"],
            "size": direct["size"],
            "host": direct["host"],
            "final_url": direct["url"],
            "media_mode": direct.get("media_mode", "file"),
            "preview_url": direct["url"] if direct["content_type"].startswith("image/") else "",
            "quality_sizes": {"source": direct["size"] or 0},
            "note": (
                "Direct media detected. SOURCE size is exact; quality-specific size is shown when the source exposes it."
                if direct.get("media_mode") in {"video", "photo", "audio"}
                else "Direct file detected. It will download unchanged when ORIGINAL / DIRECT is selected."
            )
        })

    page_media = page_media_probe(url)
    if page_media and page_media.get("ok"):
        if page_media.get("size") and page_media["size"] > MAX_FILE_SIZE:
            return jsonify({"success": False, "error": "Source file is larger than 500 MB."}), 413
        return jsonify({
            "success": True,
            "method": "page-meta",
            "filename": page_media.get("filename", "download"),
            "content_type": page_media.get("content_type", "application/octet-stream"),
            "size": page_media.get("size", 0),
            "host": urlparse(url).hostname or "",
            "final_url": page_media.get("url", ""),
            "preview_url": page_media.get("url", "") if page_media.get("content_type", "").startswith("image/") else "",
            "title": page_media.get("title", "MEDIA"),
            "media_mode": page_media.get("media_mode", "file"),
            "quality_sizes": {"source": page_media.get("size", 0) or 0},
            "note": "Public page metadata exposed a direct media resource."
        })

    info, extractor_error = run_ytdlp_info(url)
    if info:
        return jsonify({
            "success": True,
            "method": "yt-dlp",
            "filename": ytdlp_filename(info),
            "content_type": ytdlp_mime(info),
            "size": int(info.get("filesize") or info.get("filesize_approx") or 0),
            "host": urlparse(url).hostname or "",
            "title": info.get("title") or "MEDIA",
            "duration": info.get("duration") or 0,
            "thumbnail": info.get("thumbnail") or "",
            "media_mode": "video" if (info.get("vcodec") or "none") != "none" else ("audio" if (info.get("acodec") or "none") != "none" else "file"),
            "quality_sizes": ytdlp_quality_sizes(info),
            "note": "Supported page media detected. Size values are estimates when the source exposes format-size metadata."
        })

    message = direct.get("error", "Media could not be detected.")
    if extractor_error:
        message += " | extractor: " + extractor_error
    return jsonify({
        "success": False,
        "error": message,
        "yt_dlp_available": yt_dlp_available()
    }), 400

@app.post("/api/prepare")
def prepare_api():
    result, error = prepare_download(request.get_json(silent=True) or {})
    if not result:
        return jsonify({"success": False, "error": error or "Download preparation failed."}), 400
    token = uuid.uuid4().hex
    PREPARED[token] = {
        "dir": result["dir"], "file": str(result["file"]),
        "filename": result["filename"], "content_type": result["content_type"],
        "created": time.time()
    }
    return jsonify({
        "success": True,
        "filename": result["filename"],
        "size": Path(result["file"]).stat().st_size,
        "download_url": "/api/download-ready/" + token
    })

@app.get("/api/download-ready/<token>")
def download_ready(token):
    cleanup_prepared()
    item = PREPARED.get(token)
    if not item or not Path(item["file"]).exists():
        return jsonify({"success": False, "error": "Prepared download expired or was already removed."}), 404
    response = send_file(item["file"], mimetype=item["content_type"], as_attachment=True,
                         download_name=item["filename"], max_age=0)
    def cleanup():
        PREPARED.pop(token, None)
        shutil.rmtree(item["dir"], ignore_errors=True)
    response.call_on_close(cleanup)
    return response

@app.route("/api/download", methods=["GET", "POST"])
def download():
    # GET is intentionally supported so Android/Chrome can receive the file
    # as a normal browser attachment instead of buffering it into a JS Blob.
    if request.method == "GET":
        data = request.args.to_dict(flat=True)
    else:
        data = request.get_json(silent=True) or {}

    url = str(data.get("url", "")).strip()
    requested_format = str(data.get("format", "original")).lower().strip()
    quality = str(data.get("quality", "source")).lower().strip()
    requested_name = str(data.get("filename", "")).strip()

    if not is_http_url(url):
        return jsonify({"success": False, "error": "A valid HTTP/HTTPS URL is required."}), 400

    if requested_format not in {"original", "mp4", "webm", "mp3", "thumbnail"}:
        return jsonify({"success": False, "error": "Unsupported output format."}), 400

    direct = direct_probe(url)
    if not direct["ok"]:
        page_media = page_media_probe(url)
        if page_media and page_media.get("ok"):
            direct = page_media
    if direct["ok"]:
        final_url = direct["url"]
        content_type = direct["content_type"]
        source_ext = extension_from_url(final_url) or extension_from_content_type(content_type)
        if direct["size"] and direct["size"] > MAX_FILE_SIZE:
            return jsonify({"success": False, "error": "Source file is larger than 500 MB."}), 413

        # Direct images are downloaded as images. A thumbnail request on an
        # already-image URL is therefore also a normal image download.
        if requested_format == "thumbnail":
            if content_type.startswith("image/"):
                requested_format = "original"
            elif content_type.startswith("video/"):
                ffmpeg = shutil.which("ffmpeg")
                if not ffmpeg:
                    return jsonify({"success": False, "error": "Video thumbnail needs ffmpeg. Install ffmpeg first."}), 400
                temp_dir = Path(tempfile.mkdtemp(prefix="neo_drop_thumb_direct_"))
                try:
                    source_file = temp_dir / ("source" + (source_ext or ".bin"))
                    response = upstream(final_url)
                    if response.status_code >= 400:
                        code = response.status_code
                        response.close()
                        return jsonify({"success": False, "error": f"Source returned HTTP {code} during thumbnail extraction."}), 502
                    received = 0
                    with source_file.open("wb") as fh:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if not chunk: continue
                            received += len(chunk)
                            if received > MAX_FILE_SIZE:
                                raise RuntimeError("Source exceeded 500 MB.")
                            fh.write(chunk)
                    response.close()
                    output_file = temp_dir / "thumbnail.jpg"
                    proc = subprocess.run([ffmpeg, "-y", "-ss", "0.5", "-i", str(source_file), "-frames:v", "1", "-q:v", "2", str(output_file)], capture_output=True, text=True, timeout=180, check=False)
                    if proc.returncode != 0 or not output_file.exists():
                        return jsonify({"success": False, "error": (proc.stderr or "Thumbnail extraction failed")[-1000:]}), 500
                    stem = safe_filename(requested_name, Path(filename_from_response(response) or Path(urlparse(final_url).path).stem or "thumbnail").stem) if requested_name else Path(urlparse(final_url).path).stem or "thumbnail"
                    if Path(stem).suffix: stem = Path(stem).stem
                    result = send_file(output_file, mimetype="image/jpeg", as_attachment=True, download_name=safe_filename(stem, "thumbnail") + ".jpg", max_age=0)
                    result.call_on_close(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
                    return result
                except requests.RequestException as exc:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return jsonify({"success": False, "error": f"Could not download source: {exc}"}), 502
                except Exception as exc:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return jsonify({"success": False, "error": str(exc)}), 500
            else:
                return jsonify({"success": False, "error": "Thumbnail extraction is available for video/photo media or supported media pages."}), 400

        # If the source already matches the requested format, stream it.
        direct_matches = (
            requested_format == "original"
            or (requested_format == "mp4" and (source_ext == ".mp4" or content_type == "video/mp4"))
            or (requested_format == "webm" and (source_ext == ".webm" or content_type == "video/webm"))
            or (requested_format == "mp3" and (source_ext == ".mp3" or content_type == "audio/mpeg"))
        )

        if not direct_matches:
            # Convert a direct media file with ffmpeg when the user explicitly
            # selected another supported output format.
            ffmpeg = shutil.which("ffmpeg")
            if requested_format not in {"mp4", "webm", "mp3"} or not ffmpeg:
                return jsonify({
                    "success": False,
                    "error": "This direct URL cannot be converted here. Install ffmpeg or choose ORIGINAL/DIRECT."
                }), 400

            temp_dir = Path(tempfile.mkdtemp(prefix="neo_drop_convert_"))
            try:
                response = upstream(final_url)
                if response.status_code >= 400:
                    code = response.status_code
                    response.close()
                    return jsonify({"success": False, "error": f"Source returned HTTP {code} during download."}), 502

                source_file = temp_dir / ("source" + (source_ext or ".bin"))
                with source_file.open("wb") as fh:
                    received = 0
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        received += len(chunk)
                        if received > MAX_FILE_SIZE:
                            raise RuntimeError("Source exceeded 500 MB.")
                        fh.write(chunk)
                response.close()

                out_ext = "." + requested_format
                output_file = temp_dir / ("converted" + out_ext)
                command = [ffmpeg, "-y", "-i", str(source_file)]
                if requested_format == "mp3":
                    command += ["-vn", "-codec:a", "libmp3lame", "-q:a", "2"]
                elif requested_format == "mp4":
                    command += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-movflags", "+faststart"]
                else:
                    command += ["-c:v", "libvpx-vp9", "-c:a", "libopus", "-deadline", "realtime"]
                command += [str(output_file)]
                proc = subprocess.run(command, capture_output=True, text=True, timeout=900, check=False)
                if proc.returncode != 0 or not output_file.exists():
                    return jsonify({"success": False, "error": (proc.stderr or "ffmpeg conversion failed")[-1200:]}), 500
                if output_file.stat().st_size > MAX_FILE_SIZE:
                    return jsonify({"success": False, "error": "Converted file is larger than 500 MB."}), 413

                stem = safe_filename(requested_name, Path(urlparse(final_url).path).stem or "download")
                if Path(stem).suffix:
                    stem = Path(stem).stem
                filename = safe_filename(stem) + out_ext
                response = send_file(output_file, mimetype=mime_from_extension(out_ext), as_attachment=True, download_name=filename, max_age=0)
                response.call_on_close(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
                return response
            except requests.RequestException as exc:
                return jsonify({"success": False, "error": f"Could not download source: {exc}"}), 502
            except Exception as exc:
                return jsonify({"success": False, "error": str(exc)}), 500
            finally:
                # send_file keeps the file alive; cleanup is handled by call_on_close.
                if not 'response' in locals() or not hasattr(response, 'call_on_close'):
                    shutil.rmtree(temp_dir, ignore_errors=True)

        response = None
        try:
            response = upstream(final_url)
            if response.status_code >= 400:
                code = response.status_code
                response.close()
                return jsonify({"success": False, "error": f"Source returned HTTP {code} during download."}), 502

            total = response_size(response)
            if total and total > MAX_FILE_SIZE:
                response.close()
                return jsonify({"success": False, "error": "Source file is larger than 500 MB."}), 413

            filename = make_direct_filename(final_url, requested_name, content_type, direct.get("filename", ""))

            def generate():
                received = 0
                try:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        received += len(chunk)
                        if received > MAX_FILE_SIZE:
                            raise RuntimeError("Source exceeded 500 MB.")
                        yield chunk
                finally:
                    response.close()

            headers = {
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": content_type,
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "X-NeoDrop-Method": "direct",
                "X-NeoDrop-Quality": quality
            }
            if total:
                headers["Content-Length"] = str(total)
            return Response(generate(), headers=headers)
        except requests.RequestException as exc:
            if response is not None:
                response.close()
            return jsonify({"success": False, "error": f"Could not download source: {exc}"}), 502

    result, error = run_ytdlp_download(url, requested_format, quality, requested_name)
    if result:
        temp_dir = Path(tempfile.mkdtemp(prefix="neo_drop_result_"))
        output_file = temp_dir / result["filename"]
        try:
            output_file.write_bytes(result["data"])
            response = send_file(output_file, mimetype=result["content_type"], as_attachment=True,
                                 download_name=result["filename"], max_age=0)
            response.call_on_close(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
            return response
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    return jsonify({
        "success": False,
        "error": error or direct.get("error") or "Download failed.",
        "yt_dlp_available": yt_dlp_available()
    }), 400

@app.get("/manifest.webmanifest")
def manifest():
    return Response(json.dumps({
        "name":"NEO-DROP", "short_name":"NEO-DROP", "start_url":"/",
        "display":"standalone", "background_color":"#f5f0df", "theme_color":"#f5f0df",
        "icons":[]
    }), mimetype="application/manifest+json")

@app.get("/service-worker.js")
def service_worker():
    script = """
const CACHE='neo-drop-shell-v3';
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.add('/')).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET') return;
  e.respondWith(fetch(e.request).then(r=>{const copy=r.clone(); caches.open(CACHE).then(c=>c.put(e.request,copy)); return r;}).catch(()=>caches.match(e.request).then(r=>r||caches.match('/'))));
});
"""
    response = Response(script, mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-cache"
    return response

# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))

    print("=" * 60)
    print(" NEO-DROP // ALL-IN-ONE SERVER")
    print("=" * 60)
    print(f" http://127.0.0.1:{port}")
    print(" HTML is embedded directly inside server.py")
    print(" Direct media + optional yt-dlp page workflow enabled")
    print(f" yt-dlp available: {yt_dlp_available()}")
    print("=" * 60)

    app.run(host=host, port=port, debug=False, threaded=True)
