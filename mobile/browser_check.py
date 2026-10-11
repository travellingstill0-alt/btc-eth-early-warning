"""Real Chromium viewport checks against the running local preview."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('docs/mobile'); out.mkdir(exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':360,'height':800},is_mobile=True,has_touch=True)
    page.goto('http://127.0.0.1:8501',wait_until='domcontentloaded')
    page.get_by_text('BTC / ETH Watch',exact=True).wait_for(timeout=30000)
    page.get_by_text('Independent early warnings',exact=True).wait_for(timeout=180000)
    for width,height in [(360,800),(412,915),(768,1024),(1280,800)]:
        page.set_viewport_size({'width':width,'height':height})
        page.wait_for_timeout(500)
        overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        exceptions=page.locator('[data-testid="stException"]').count()
        results.append(dict(width=width,height=height,horizontal_overflow=overflow,exceptions=exceptions))
        page.screenshot(path=str(out/f'preview-{width}.png'),full_page=True)
        assert not overflow and not exceptions, results[-1]
    browser.close()
(out/'viewport-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
