import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const urls = {
  "What is Prosperity": "https://imc-prosperity.notion.site/what-is-prosperity?pvs=25",
  "Who is IMC": "https://imc-prosperity.notion.site/who-is-imc-?pvs=25",
  "Storyline": "https://imc-prosperity.notion.site/storyline?pvs=25",
  "Round Schedule": "https://imc-prosperity.notion.site/round-schedule?pvs=25",
  "Game Mechanics Overview": "https://imc-prosperity.notion.site/game-mechanics-overview?pvs=25",
  "Rules": "https://imc-prosperity.notion.site/rules?pvs=25",
  "FAQ": "https://imc-prosperity.notion.site/faq?pvs=25",
  "Trading glossary": "https://imc-prosperity.notion.site/trading-glossary?pvs=25",
  "Programming resources": "https://imc-prosperity.notion.site/programming-resources?pvs=25",
  "Writing an Algorithm in Python": "https://imc-prosperity.notion.site/writing-an-algorithm-in-python?pvs=25",
  "Tutorial Round - Simulator Practice": "https://imc-prosperity.notion.site/tutorial-round-simulator-practice?pvs=25"
};

const outputDir = path.resolve("../prosperity-4-wiki");
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

(async () => {
    // Launch headless Chromium
    const browser = await chromium.launch();
    
    // Iterate over URLs
    for (const [title, url] of Object.entries(urls)) {
        console.log(`Scraping ${title}...`);
        const page = await browser.newPage();
        
        // Go to the URL and wait until hydration / network traffic calms down
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
        
        // Unconditionally wait 15 seconds for Notion's client side rendering
        await page.waitForTimeout(15000);
        
        // Extract the full innerText of the target element or full body as a fallback
        const content = await page.evaluate(() => {
            const getStructureText = (root) => {
                if(!root) return '';
                // basic extraction relying on Notion DOM or just innerText
                return root.innerText;
            };
            let el = document.querySelector('.notion-page-content');
            if(!el) el = document.querySelector('main');
            if(!el) el = document.body;
            return getStructureText(el);
        });
        
        // Create filename and sanitize it
        const filename = title.replace(/[^a-zA-Z0-9 -]/g, '').replace(/ /g, '_') + '.md';
        const filepath = path.join(outputDir, filename);
        
        // Write the result
        fs.writeFileSync(filepath, `# ${title}\n\n${content}`);
        console.log(`Saved ${filepath}`);
        
        await page.close();
    }
    
    await browser.close();
})();
