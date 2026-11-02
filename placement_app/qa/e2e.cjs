// Run only against a disposable database/server. This script creates demo records.
const {chromium}=require(process.env.PLACEMENT_PLAYWRIGHT||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.PLACEMENT_BASE;
if(!base || !process.env.PLACEMENT_QA_ISOLATED)throw new Error('Set PLACEMENT_BASE and PLACEMENT_QA_ISOLATED=1 for an isolated QA server.');
const checks=[];
function check(name,condition){assert.ok(condition,name);checks.push(name);console.log('PASS',name)}
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLACEMENT_CHROMIUM?{executablePath:process.env.PLACEMENT_CHROMIUM}:{})});
 const errors=[];
 try{
  async function pageFor(email){
   const context=await browser.newContext({baseURL:base,viewport:{width:1440,height:1000}});
   const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
   await page.goto(base+'/login/');
   await page.locator('[name=username]').fill(email);await page.locator('[name=password]').fill('Campus@2027!');
   await Promise.all([page.waitForURL(base+'/'),page.getByRole('button',{name:'Sign in',exact:true}).click()]);
   return page;
  }
  async function submit(page,button,url){await Promise.all([page.waitForURL(url),page.getByRole('button',{name:button,exact:true}).click()])}
  const recruiter=await pageFor('hr@northstar.example');
  const officer=await pageFor('admin@college.edu');
  const title='QA Graduate Product Engineer';
  await recruiter.goto(base+'/jobs/new/');
  await recruiter.locator('[name=title]').fill(title);await recruiter.locator('[name=location]').fill('Pune · Hybrid');
  await recruiter.locator('[name=package]').fill('15');await recruiter.locator('[name=min_cgpa]').fill('7');await recruiter.locator('[name=max_backlogs]').fill('0');
  await recruiter.locator('[name=branches][value=CSE]').check();await recruiter.locator('[name=deadline]').fill(new Date(Date.now()+21*86400000).toISOString().slice(0,10));
  await recruiter.locator('[name=description]').fill('A QA-only opening to verify the full campus recruitment journey.');
  await recruiter.getByRole('button',{name:'Save opportunity',exact:true}).click();
  await recruiter.waitForURL(/\/jobs\/\d+\//);const jobUrl=recruiter.url();
  check('Recruiter creates opening pending review',await recruiter.getByText('Awaiting approval',{exact:true}).isVisible());
  await officer.goto(jobUrl);await officer.getByRole('button',{name:'Approve & open',exact:true}).click();
  await officer.getByText('Opening status updated.',{exact:true}).waitFor();check('Officer approves opening',true);
  const studentContext=await browser.newContext({baseURL:base,viewport:{width:1440,height:1000}});const student=await studentContext.newPage();student.on('pageerror',e=>errors.push(e.message));
  await student.goto(base+'/register/');
  const fields={role:'student',display_name:'Maya QA',email:'maya.qa@example.test',roll_no:'QA27001',branch:'CSE',cgpa:'8.60',graduation_year:'2027',password1:'NewCampus@2027!',password2:'NewCampus@2027!'};
  for(const [name,value]of Object.entries(fields)){
   const field=student.locator(`[name=${name}]`);if(['role','branch'].includes(name))await field.selectOption(value);else await field.fill(value);
  }
  await submit(student,'Create account',base+'/');
  check('Student registration awaits approval',await student.getByText('Account pending review',{exact:true}).isVisible());
  await officer.goto(base+'/people/students/?q=maya.qa');await officer.getByRole('button',{name:'Approve',exact:true}).click();
  await student.goto(jobUrl);await student.locator('[name=cover_note]').fill('I love building useful software.');
  await submit(student,'Send application',base+'/applications/');
  check('Student applies and sees persisted application',await student.getByText(title,{exact:true}).isVisible());
  await student.goto(base+'/profile/');
  await student.locator('[name=resume]').setInputFiles(path.join(__dirname,'artifacts/resume-sample.pdf'));
  await student.getByRole('button',{name:'Save profile',exact:true}).click();
  await student.getByText('Profile saved.',{exact:true}).waitFor();
  check('Resume upload succeeds without resetting approval',!(await student.getByText('Account pending review',{exact:true}).count()));
  await recruiter.goto(base+'/applications/?q=maya');
  const resumeResponse=await recruiter.request.get(await recruiter.getByRole('link',{name:'Download resume',exact:false}).getAttribute('href'));
  check('Recruiter can download applicant resume',resumeResponse.status()===200&&(await resumeResponse.body()).subarray(0,4).toString()==='%PDF');
  await recruiter.getByRole('button',{name:'Shortlist',exact:true}).click();
  await recruiter.getByRole('button',{name:'Confirm',exact:true}).click();
  await recruiter.getByText('Application updated.',{exact:true}).waitFor();
  // Find the candidate within the retained filter.
  let row=recruiter.getByRole('row').filter({hasText:'Maya QA'});
  await row.getByRole('link',{name:'Schedule',exact:true}).click();
  await recruiter.locator('[name=starts_at]').fill(new Date(Date.now()+7*86400000).toISOString().slice(0,10)+'T11:00');
  await recruiter.locator('[name=mode]').selectOption('Online');await recruiter.locator('[name=venue]').fill('https://example.com/qa-meeting');
  await recruiter.locator('[name=notes]').fill('Please bring your portfolio.');
  await submit(recruiter,'Save interview',base+'/interviews/');
  check('Recruiter schedules interview',await recruiter.getByText('Maya QA',{exact:true}).isVisible());
  await student.goto(base+'/interviews/');
  check('Student sees interview and joining link',await student.getByRole('link',{name:'Join meeting',exact:false}).isVisible());
  await recruiter.goto(base+'/applications/?q=maya');
  row=recruiter.getByRole('row').filter({hasText:'Maya QA'});
  await row.getByRole('button',{name:'Select candidate',exact:true}).click();await recruiter.getByRole('button',{name:'Confirm',exact:true}).click();
  await recruiter.getByText('Application updated.',{exact:true}).waitFor();
  await student.goto(base+'/applications/');
  check('Student sees selection',await student.getByText('Selected',{exact:true}).count()>0);
  const confirmation=await student.request.get(await student.getByRole('link',{name:'Confirmation',exact:false}).getAttribute('href'));
  check('Selection confirmation PDF downloads',confirmation.status()===200&&(await confirmation.body()).subarray(0,4).toString()==='%PDF');
  fs.writeFileSync(path.join(__dirname,'artifacts/selection-confirmation.pdf'),await confirmation.body());
  await officer.goto(base+'/reports/?branch=CSE');
  check('Report includes newly selected student',await officer.getByRole('row').filter({hasText:'Maya QA'}).getByText('Placed',{exact:true}).isVisible());
  const exportResponse=await officer.request.get(base+'/reports/?export=csv&branch=CSE');
  check('CSV includes saved selection',(await exportResponse.text()).includes('Maya QA'));
  await student.getByRole('button',{name:'Sign out',exact:true}).click();
  await student.locator('[name=username]').fill('maya.qa@example.test');await student.locator('[name=password]').fill('NewCampus@2027!');
  await submit(student,'Sign in',base+'/');
  await student.goto(base+'/applications/');check('Selection persists after signing out and back in',await student.getByRole('link',{name:'Confirmation',exact:false}).isVisible());
  await student.screenshot({path:path.join(__dirname,'artifacts/e2e-selected.png'),fullPage:true});
  check('No E2E browser errors',errors.length===0);
  fs.writeFileSync(path.join(__dirname,'artifacts/e2e-results.json'),JSON.stringify({passed:checks.length,checks,errors},null,2));
  console.log(`${checks.length} E2E checks passed.`);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
