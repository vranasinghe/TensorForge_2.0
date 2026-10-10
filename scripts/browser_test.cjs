/* Real browser checks and a short, silent demonstration recording. */
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const output=path.join(root,'experiments','browser');
fs.mkdirSync(output,{recursive:true});

async function main(){
  const errors=[];
  const report={method:'isolated headless Chrome, actual private frontend and backend',checks:[],browser_version:null};
  const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXECUTABLE||undefined});
  report.browser_version=browser.version();
  const context=await browser.newContext({viewport:{width:1365,height:950},httpCredentials:{username:process.env.DEMO_USERNAME||'demo',password:process.env.DEMO_PASSWORD||'local-demo-password'},...(process.env.NO_VIDEO?{}:{recordVideo:{dir:output,size:{width:1365,height:950}}}),acceptDownloads:true});
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('request',r=>{if(r.headers()['x-api-key'])errors.push('Backend API key leaked to browser request');});
  try{
    await page.goto(process.env.DEMO_URL||'http://127.0.0.1:8501',{waitUntil:'networkidle'});
    await page.getByText('Model ready',{exact:true}).waitFor({timeout:30000});
    assert(!await page.content().then(s=>s.includes('local-demo-key')));
    await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
    report.checks.push('authenticated page, actual readiness, no backend key in browser');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('#channel').evaluate(e=>e===document.activeElement),true);
    report.checks.push('keyboard focus reaches the ticket controls');
    for(const [channel,subject,text] of [
      ['chat','','My food has not arrived. Please refund me.'],
      ['email','Forgotten bag','මගේ බෑග් එක කාර් එකේ අමතක වුණා.'],
      ['chat','','என் உணவு வரவில்லை. பணம் திருப்பி தாருங்கள்.'],
    ]){
      await page.locator('#channel').selectOption(channel);
      await page.locator('#subject').fill(subject);
      await page.locator('#text').fill(text);
      await page.locator('#classify').click();
      await page.locator('#result .route').waitFor();
      await page.locator('#classify').waitFor({state:'visible'});
      await page.waitForFunction(()=>!document.querySelector('#classify').disabled);
      assert.match(await page.locator('#result').innerText(),/Primary confidence/);
      assert.equal(await page.locator('#message').innerText(),'');
      await page.waitForTimeout(700);
    }
    report.checks.push('English, Sinhala and Tamil ticket entry and backend responses');
    await page.screenshot({path:path.join(output,'classified.png'),fullPage:true});
    const csv='ticket_id,channel,subject,text\nbrowser-1,chat,,"My food is late\nand I need a refund"\nbrowser-2,email,Lost bag,මගේ බෑග් එක අමතක වුණා\n';
    await page.locator('#csv').setInputFiles({name:'browser-tickets.csv',mimeType:'text/csv',buffer:Buffer.from(csv,'utf8')});
    await page.locator('#submit-batch').click();
    await page.getByText('Succeeded · 2 / 2 tickets',{exact:true}).waitFor({timeout:30000});
    assert.equal(await page.locator('#progress').getAttribute('value'),'2');
    const downloaded=page.waitForEvent('download');
    await page.locator('#download').click();
    const download=await downloaded;
    await download.saveAs(path.join(output,'predictions.csv'));
    const predictions=fs.readFileSync(path.join(output,'predictions.csv'),'utf8');
    assert(predictions.includes('browser-1')&&predictions.includes('browser-2'));
    report.checks.push('quoted multiline Unicode CSV upload, async progress and actual CSV download');
    await page.screenshot({path:path.join(output,'batch.png'),fullPage:true});
    await page.locator('#cancel').click();
    await page.getByText('Batch discarded.',{exact:true}).waitFor();
    assert.equal(await page.locator('#progress').getAttribute('value'),'0');
    assert.equal(await page.locator('#job-detail').innerText(),'');
    await page.locator('#submit-batch').click();
    await page.getByText('Succeeded · 2 / 2 tickets',{exact:true}).waitFor({timeout:30000});
    await page.locator('#cancel').click();
    await page.getByText('Batch discarded.',{exact:true}).waitFor();
    report.checks.push('discard completed batch and submit another batch');
    await page.locator('#text').fill('   ');
    await page.locator('#classify').click();
    await page.waitForFunction(()=>!document.querySelector('#classify').disabled);
    assert.match(await page.locator('#message').innerText(),/schema/);
    report.checks.push('invalid whitespace input displayed without browser crash');
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
    const bounds=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth}));
    assert(bounds.scroll<=bounds.viewport+1,'Horizontal overflow on mobile');
    report.checks.push('390px responsive layout without horizontal overflow');
    let releasePoll, markHeld, markReturned;
    const held=new Promise(resolve=>{markHeld=resolve});
    const released=new Promise(resolve=>{releasePoll=resolve});
    const returned=new Promise(resolve=>{markReturned=resolve});
    const statusPattern=/\/api\/batch\/jobs\/[a-f0-9-]+$/;
    await page.route(statusPattern,async route=>{
      if(route.request().method()!=='GET'){await route.continue();return;}
      const response=await route.fetch();
      markHeld();await released;
      await route.fulfill({response});markReturned();
    });
    await page.locator('#submit-batch').click();
    await held;
    await page.locator('#cancel').click();
    await page.locator('#cancel').waitFor({state:'hidden'});
    await page.getByText('Batch discarded.',{exact:true}).waitFor();
    releasePoll();await returned;await page.waitForTimeout(250);
    assert.equal(await page.locator('#job-label').innerText(),'Batch discarded.');
    assert.equal(await page.locator('#job-detail').innerText(),'');
    assert(await page.locator('#download').isHidden());
    await page.unroute(statusPattern);
    report.checks.push('late polling response after DELETE cannot restore a discarded batch');
    assert.deepEqual(errors,[]);
    report.checks.push('no uncaught browser exceptions');
  }finally{
    const video=page.video();
    await context.close();
    if(video&&!process.env.NO_VIDEO){await video.saveAs(path.join(root,'output','rideeat_demo.webm'));await video.delete();}
    await browser.close();
    report.errors=errors;
    fs.writeFileSync(path.join(output,'verification.json'),JSON.stringify(report,null,2));
  }
  console.log(JSON.stringify(report,null,2));
}
main().catch(e=>{console.error(e);process.exit(1);});
