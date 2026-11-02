const { chromium } = require(process.env.PLACEMENT_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const base = process.env.PLACEMENT_BASE || 'http://127.0.0.1:3001';
const checks = [];
const check = (name, value) => { assert.ok(value, name); checks.push(name); console.log('PASS',name); };
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.PLACEMENT_CHROMIUM ? {executablePath:process.env.PLACEMENT_CHROMIUM} : {})});
  const errors = [], failed=[];
  try {
    for (const [role,email] of [['officer','admin@college.edu'],['student','student@college.edu'],['recruiter','hr@northstar.example']]) {
      const context = await browser.newContext({viewport:{width:1440,height:1050}});
      const page = await context.newPage();
      page.on('pageerror',e=>errors.push(e.message));
      page.on('response',r=>{if(r.status()>=500)failed.push(`${r.status()} ${r.url()}`)});
      await page.goto(base+'/login/');
      await page.screenshot({path:path.join(__dirname,'artifacts/login.png')});
      await page.getByRole('button',{name:role==='officer'?'Placement officer':role==='student'?'Student':'Recruiter',exact:true}).click();
      check(role+' demo credentials',await page.locator('[name=username]').inputValue()===email);
      await Promise.all([page.waitForURL(base+'/'),page.getByRole('button',{name:'Sign in',exact:true}).click()]);
      check(role+' signed in',(await page.title()).includes('Overview'));
      await page.screenshot({path:path.join(__dirname,`artifacts/${role}-dashboard.png`),fullPage:true});
      const paths=['/jobs/','/applications/','/interviews/','/profile/','/password/'];
      if(role==='officer')paths.push('/people/students/','/people/companies/','/reports/');
      for(const route of paths){const r=await page.goto(base+route);check(role+' '+route,r.status()===200);}
      if(role==='officer') {
        const csv=await context.request.get(base+'/reports/?export=csv');check('CSV export',(await csv.text()).includes('Roll number'));
        const pdf=await context.request.get(base+'/reports/?export=pdf');check('PDF export',(await pdf.body()).subarray(0,4).toString()==='%PDF');
        await page.screenshot({path:path.join(__dirname,'artifacts/officer-reports.png'),fullPage:true});
      }
      await page.goto(base+'/jobs/?q=no-such-role');check(role+' empty search',await page.getByRole('heading',{name:'No opportunities found'}).isVisible());
      await page.setViewportSize({width:390,height:844});
      for(const route of ['/','/jobs/','/applications/','/interviews/','/profile/']){
        await page.goto(base+route);
        check(role+' mobile overflow '+route,await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
      }
      await page.goto(base+'/');
      await page.getByRole('button',{name:'Toggle navigation'}).click();
      check(role+' mobile navigation',await page.getByRole('button',{name:'Toggle navigation'}).getAttribute('aria-expanded')==='true');
      await page.keyboard.press('Escape');
      await page.screenshot({path:path.join(__dirname,`artifacts/${role}-mobile.png`),fullPage:true});
      await context.close();
    }
    check('No browser JavaScript errors',errors.length===0);
    check('No server errors',failed.length===0);
    require('node:fs').writeFileSync(path.join(__dirname,'artifacts/smoke-results.json'),JSON.stringify({passed:checks.length,checks,errors,failed},null,2));
    console.log(`${checks.length} checks passed.`);
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
