// Use only with the isolated, seeded review database; this mutates its demo workflows.
const {chromium}=require(process.env.PLACEMENT_PLAYWRIGHT||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const base=process.env.PLACEMENT_BASE;
if(!base||!process.env.PLACEMENT_QA_ISOLATED)throw Error('An isolated review server is required.');
const checks=[];
function check(name,ok){assert.ok(ok,name);checks.push(name);console.log('PASS',name)}
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLACEMENT_CHROMIUM?{executablePath:process.env.PLACEMENT_CHROMIUM}:{})});
 try{
  async function signedIn(email){
   const ctx=await browser.newContext({baseURL:base,viewport:{width:1440,height:1000}});
   const page=await ctx.newPage();await page.goto(base+'/login/');
   await page.locator('[name=username]').fill(email);await page.locator('[name=password]').fill('Campus@2027!');
   await Promise.all([page.waitForURL(base+'/'),page.getByRole('button',{name:'Sign in',exact:true}).click()]);return page;
  }
  async function post(page,url,data){
   const token=await page.locator('[name=csrfmiddlewaretoken]').first().getAttribute('value');
   return page.request.post(url,{form:{csrfmiddlewaretoken:token,...data},maxRedirects:0});
  }
  const officer=await signedIn('admin@college.edu');
  const student=await signedIn('student@college.edu');
  const north=await signedIn('hr@northstar.example');
  const orbit=await signedIn('hr@orbit.example');
  // Validate two previously crashing malformed filter cases through HTTP.
  for(const value of ['²','9'.repeat(100)]){
   const r=await officer.goto(base+'/applications/?job='+encodeURIComponent(value));
   check('Malformed job filter returns 200: '+value.slice(0,8),r.status()===200);
   check('Malformed job filter yields empty scope',await officer.getByRole('heading',{name:'No applications to show'}).isVisible());
  }
  check('Authenticated response prevents caching',(await officer.request.get('/reports/?export=csv')).headers()['cache-control'].includes('no-store'));
  // A role switch must disable fields which no longer apply.
  const signup=await browser.newPage();await signup.goto(base+'/register/');
  await signup.locator('[name=cgpa]').fill('12');await signup.locator('[name=roll_no]').fill('CS27001');
  await signup.locator('[name=role]').selectOption('company');
  check('Recruiter signup disables hidden academic fields',await signup.locator('[name=cgpa]').isDisabled()&&await signup.locator('[name=roll_no]').isDisabled());
  await signup.locator('[name=website]').fill('invalid');await signup.locator('[name=role]').selectOption('student');
  check('Student signup disables hidden company website',await signup.locator('[name=website]').isDisabled());
  // Hidden mobile navigation cannot receive keyboard focus.
  await student.setViewportSize({width:390,height:844});await student.goto(base+'/');
  check('Collapsed mobile sidebar is inert',await student.locator('#sidebar').evaluate(e=>e.inert));
  const toggle=student.getByRole('button',{name:'Toggle navigation'});await toggle.click();
  check('Expanded mobile sidebar is interactive',!(await student.locator('#sidebar').evaluate(e=>e.inert)));
  check('Opening menu moves keyboard focus into it',await student.evaluate(()=>document.getElementById('sidebar').contains(document.activeElement)));
  await student.keyboard.press('Escape');
  check('Escape closes menu and restores focus',await toggle.evaluate(e=>e===document.activeElement)&&await student.locator('#sidebar').evaluate(e=>e.inert));
  await student.setViewportSize({width:1440,height:1000});
  check('Desktop sidebar becomes interactive after resize',!(await student.locator('#sidebar').evaluate(e=>e.inert)));
  // Duplicate requests use the actual server/database transaction boundary.
  await student.goto(base+'/jobs/');
  const target=student.getByRole('heading',{name:'Data & Analytics Associate',exact:true}).getByRole('link');
  await target.click();const jobPath=new URL(student.url()).pathname;
  const duplicate=await Promise.all([post(student,jobPath+'apply/',{cover_note:'Concurrent QA'}),post(student,jobPath+'apply/',{cover_note:'Concurrent QA'})]);
  check('Simultaneous duplicate applications both complete safely',duplicate.every(r=>r.status()===302));
  await student.goto(base+'/applications/');
  check('Simultaneous apply creates exactly one visible application',await student.getByRole('row').filter({hasText:'Data & Analytics Associate'}).count()===1);
  // Two recruiters cannot reserve the same student for overlapping interviews.
  await north.goto(base+'/applications/?q=Aarav');await orbit.goto(base+'/applications/?q=Aarav');
  const orbitRow=orbit.getByRole('row').filter({hasText:'Cloud Engineering Associate'});
  const state=await orbitRow.locator('form').filter({has:orbit.getByRole('button',{name:'Shortlist',exact:true})}).getAttribute('action');
  check('Other application shortlisted', (await post(orbit,state,{status:'shortlisted'})).status()===302);
  await orbit.goto(base+'/applications/?q=Aarav');
  const northSchedule=await north.getByRole('row').filter({hasText:'Graduate Software Engineer'}).getByRole('link',{name:'Reschedule',exact:true}).getAttribute('href');
  const orbitSchedule=await orbit.getByRole('row').filter({hasText:'Cloud Engineering Associate'}).getByRole('link',{name:'Schedule',exact:true}).getAttribute('href');
  const when=new Date(Date.now()+12*86400000).toISOString().slice(0,10)+'T11:00';
  const payload={starts_at:when,duration:45,mode:'Online',venue:'https://example.com/concurrent-review',notes:'Concurrent review'};
  const results=await Promise.all([post(north,northSchedule,payload),post(orbit,orbitSchedule,payload)]);
  check('Concurrent interview reservations admit one request',results.filter(r=>r.status()===302).length===1);
  check('Concurrent interview conflict returns a form error',results.filter(r=>r.status()===200).length===1);
  const rejected=results.find(r=>r.status()===200);
  check('Conflict response explains the student overlap',(await rejected.text()).includes('another interview during that time'));
  await student.goto(base+'/interviews/');
  check('Only one concurrent meeting appears for student',await student.getByRole('link',{name:'Join meeting',exact:false}).count()===1);
  for(const [p,url] of [[north,northSchedule],[orbit,orbitSchedule]]){
   const r=await post(p,url,{...payload,starts_at:new Date(Date.now()+13*86400000).toISOString().slice(0,10)+'T11:00',venue:'https://[invalid'});
   check('Malformed meeting URL becomes validation feedback',r.status()===200&&(await r.text()).includes('Enter a valid public http:// or https:// meeting URL without credentials.'));
  }
  const filtered=base+'/applications/?q=Aarav&job='+jobPath.split('/')[2];await north.goto(filtered);
  const chip=north.locator('.status-chip').first();check('Application status chips retain search and job scope',(await chip.getAttribute('href')).includes('q=Aarav')&&(await chip.getAttribute('href')).includes('job='));
  fs.writeFileSync(path.join(__dirname,'artifacts/review-browser-results.json'),JSON.stringify({passed:checks.length,checks},null,2));
  console.log(`${checks.length} review browser checks passed.`);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
