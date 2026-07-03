import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const urls = {
  "FAQ": "https://imc-prosperity.notion.site/faq?pvs=25",
  "Rules": "https://imc-prosperity.notion.site/rules?pvs=25",
  "Trading glossary": "https://imc-prosperity.notion.site/trading-glossary?pvs=25",
  "Programming resources": "https://imc-prosperity.notion.site/programming-resources?pvs=25",
  "Writing an Algorithm in Python": "https://imc-prosperity.notion.site/writing-an-algorithm-in-python?pvs=25",
  "Tutorial Round - Simulator Practice": "https://imc-prosperity.notion.site/tutorial-round-simulator-practice?pvs=25",
  "What is Prosperity": "https://imc-prosperity.notion.site/what-is-prosperity?pvs=25",
  "Who is IMC": "https://imc-prosperity.notion.site/who-is-imc-?pvs=25"
};

const outputDir = path.resolve("../prosperity-4-wiki");

(async () => {
    // RUN HEADFUL TO BYPASS DETECTION
    const browser = await chromium.launch({ headless: false });
    
    for (const [title, url] of Object.entries(urls)) {
        console.log(`Scraping ${title}...`);
        const context = await browser.newContext({
            userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        });
        const page = await context.newPage();
        
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
        console.log(`Waiting 15s for ${title}...`);
        await page.waitForTimeout(15000);
        
        const content = await page.evaluate(() => {
            let el = document.querySelector('.notion-page-content');
            if(!el) el = document.querySelector('main');
            if(!el) el = document.body;
            return el ? el.innerText : '';
        });
        
        const filename = title.replace(/[^a-zA-Z0-9 -]/g, '').replace(/ /g, '_') + '.md';
        const filepath = path.join(outputDir, filename);
        
        fs.writeFileSync(filepath, `# ${title}\n\n${content}`);
        console.log(`Saved ${filepath}. Size: ${content.length}`);
        
        await context.close();
    }
    await browser.close();
})();
