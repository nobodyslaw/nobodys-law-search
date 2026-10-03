import os
import re
import subprocess
from pathlib import Path

QA_PAGE_ID = os.environ.get(
    "QA_NOTION_PAGE_ID",
    "3c4a36e22f8980ad8aadd30fbefa7920",
)
ODAIBAKO_URL = "https://odaibako.net/u/Nobodys_Law"
ODAIBAKO_IMAGE = "582_20260823202844.png"

index = Path("index.html")
backup = index.read_bytes() if index.exists() else None

env = os.environ.copy()
env["NOTION_PAGE_ID"] = QA_PAGE_ID

try:
    try:
        subprocess.run(["python", "build.py"], check=True, env=env)
    except subprocess.CalledProcessError:
        print(
            "WARNING: Q&A page could not be fetched from Notion; "
            "keeping the existing qa.html unchanged."
        )
    else:
        html = index.read_text(encoding="utf-8")

        # Social preview for the public Q&A page (X / Open Graph).
        social_url = "https://nobodyslaw.github.io/nobodys-law-search/qa.html"
        social_image = "https://nobodyslaw.github.io/nobodys-law-search/582_20260823202440.png"
        social_meta = f'''<meta name="description" content="Nobody's Law Q＆A">
<meta property="og:type" content="website">
<meta property="og:title" content="Nobody's Law Q＆A">
<meta property="og:description" content="Nobody's Law Q＆A">
<meta property="og:url" content="{social_url}">
<meta property="og:image" content="{social_image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Nobody's Law Q＆A">
<meta name="twitter:description" content="Nobody's Law Q＆A">
<meta name="twitter:image" content="{social_image}">
'''
        html = html.replace('</head>', social_meta + '</head>', 1)

        # Remove the search-guidance callout.
        html = re.sub(
            r'<aside[^>]*>\s*ctrl/cmd\+F でキーワード検索ができます。ご活用ください。.*?アプリ版/スマートフォンでは検索機能を使用できませんので、ご注意ください。\s*</(?:p>)?\s*</aside>',
            '',
            html,
            count=1,
            flags=re.S,
        )
        html = re.sub(
            r'<aside[^>]*>\s*ctrl/cmd\+F でキーワード検索ができます。ご活用ください。\s*</aside>',
            '',
            html,
            count=1,
            flags=re.S,
        )

        # Convert Notion links that point to another block on this same Q&A page
        # into local HTML anchors. Notion emits these as /p/<page>#<block-id>.
        def internal_link(m):
            block_id = m.group(1).replace('-', '')
            return f'href="#block-{block_id}"'

        html = re.sub(
            r'href="(?:https://(?:www\.)?notion\.so)?/p/[^"]*#([0-9a-fA-F-]{32,36})"',
            internal_link,
            html,
        )
        html = re.sub(
            r'href="https://app\.notion\.com/p/[^"]*#([0-9a-fA-F-]{32,36})"',
            internal_link,
            html,
        )
        html = re.sub(
            r'(<a href="#block-[^"]+")\s+target="_blank"\s+rel="noopener"',
            r'\1',
            html,
        )

        # One Notion link currently loses its block fragment in the API.
        html = re.sub(
            r'(一部機械のキャラクターを作成する場合は、)<a href="https://app\.notion\.com/p/Nobody-s-Law-Q-A-3c4a36e22f8980ad8aadd30fbefa7920"[^>]*>(<strong>こちら</strong>)</a>',
            r'\1<a href="#block-3c4a36e22f8980798c02c0aac01a7c2d">\2</a>',
            html,
            count=1,
        )

        # Keep internal targets near the top with one smooth movement.
        # Open containing toggles first, wait for layout to settle, then scroll once.
        old_scroll = "target.scrollIntoView({behavior:'smooth',block:'start'});window.setTimeout(()=>window.scrollBy({top:-105,left:0,behavior:'smooth'}),180);history.replaceState"
        new_scroll = "requestAnimationFrame(()=>requestAnimationFrame(()=>{target.scrollIntoView({behavior:'smooth',block:'start'});history.replaceState(null,'',a.getAttribute('href'))}));return"
        html = html.replace(old_scroll, new_scroll)
        html = html.replace(
            "target.scrollIntoView({behavior:'smooth',block:'center'});history.replaceState(null,'',a.getAttribute('href'))",
            "requestAnimationFrame(()=>requestAnimationFrame(()=>{target.scrollIntoView({behavior:'smooth',block:'start'});history.replaceState(null,'',a.getAttribute('href'))}));return",
        )

        # CSS scroll offset gives Notion-like breathing room without a second JS scroll.
        anchor_css = '<style id="qa-anchor-style">[id^="block-"]{scroll-margin-top:86px}.toggle-body>p{line-height:2;margin-top:18px;margin-bottom:22px}</style>'
        html = html.replace('</head>', anchor_css + '</head>', 1)

        odaibako = (
            '<div style="width:100%;max-width:760px;margin:18px 0 24px">'
            f'<a href="{ODAIBAKO_URL}" target="_blank" rel="noopener" '
            'style="display:block;width:100%;margin:0;text-decoration:none;line-height:0;border-radius:8px;overflow:hidden">'
            f'<img src="{ODAIBAKO_IMAGE}" alt="お題箱はこちら" '
            'style="display:block;width:100%;height:auto;max-width:none;max-height:none;object-fit:contain;margin:0;padding:0;border:0">'
            '</a>'
            '<div style="margin-top:7px;text-align:center;font-size:13px;color:#777;line-height:1.5">'
            'クリック/タップでお題箱に飛びます'
            '</div>'
            '</div>'
        )
        html, count = re.subn(
            r'<blockquote[^>]*>\s*<strong>お題箱はこちら</strong>\s*</blockquote>',
            odaibako,
            html,
            count=1,
        )
        Path("qa.html").write_text(html, encoding="utf-8")
        print(f"Patched Odaibako image={bool(count)}")
        print("Fixed internal Q&A cross-links and smooth target positioning")
        print("Built searchable Q&A page -> qa.html")
finally:
    if backup is None:
        if index.exists():
            index.unlink()
    else:
        index.write_bytes(backup)
