/** Frontend-only contract fixture. NOT a real backend or scoring validation. */
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
const server = await createServer({server:{port:5174,host:'127.0.0.1'}});
await server.listen();
const executablePath = process.env.SIMTROUBLE_CHROMIUM;
const browser = await chromium.launch({headless:true, ...(executablePath ? {executablePath}: {}), args:['--no-sandbox','--in-process-gpu','--ignore-gpu-blocklist','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const base = process.env.SIMTROUBLE_URL ?? 'http://127.0.0.1:5174';
const out = fileURLToPath(new URL('../qa/', import.meta.url)); await fs.mkdir(out,{recursive:true});
const fixtureScene = {
 case_id:'ST-001',version:'0.4.0',title:'机械臂抓取异常',task:'观察夹爪与工件的运动，采集证据并说明你的诊断依据。',
 camera:{position:[8,6,9],target:[0,1.1,0],zoom:76},workcell:{robot_origin:[-1.5,0,0],workpiece_position:[1.3,0.34,0.55],target_position:[2.5,0.1,-1]},
 timeline:[{id:'ready',label:'准备',status:'READY',duration_ms:1000,joint_angles:[0,20,-30,10],gripper_opening:1,object_attached:false},{id:'descend',label:'夹爪下降',status:'EXECUTING',duration_ms:1000,joint_angles:[20,30,-50,15],gripper_opening:1,object_attached:false},{id:'grasp',label:'尝试抓取',status:'GRASP_ATTEMPT',duration_ms:1000,joint_angles:[20,45,-65,20],gripper_opening:0,object_attached:false},{id:'lift',label:'夹爪抬升',status:'FAILURE_OBSERVED',duration_ms:1000,joint_angles:[20,20,-30,20],gripper_opening:0,object_attached:false}],public_observations:['夹爪已执行闭合。','工件仍停留在工作台。','工件未随夹爪移动。']
};
let createCount=0, diagnosticPosts=0;
async function setup(page) {
 let session={contract_version:'0.4.0',session_id:`fixture-${++createCount}`,case_public_state:{evidence_options:[{id:'E01',type:'gripper_state'},{id:'E02',type:'object_pose'},{id:'E03',type:'target_pose'}]},public_stage:'READY',released_evidence:[],current_hypothesis:null,hypotheses:[],allowed_actions:['observe_scene','inspect_evidence']};
 let reportReads=0;
 const json=(route,data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
 await page.route('**/api/**', async route=>{
  const req=route.request(), path=new URL(req.url()).pathname;
  if(path.endsWith('/auth/me')) return json(route,{user:{user_id:'fixture-user',username:'fixture',display_name:'测试学员'},expires_at:1800000000,csrf_token:'x'.repeat(32)});
  if(path.endsWith('/scene')) return json(route,fixtureScene);
  if(path.endsWith('/sessions')) return json(route,session);
  if(path.endsWith('/evidence')) {
   const {evidence_id:id}=req.postDataJSON();
   if(id==='E03')return json(route,{detail:'invalid_session_stage'},409);
   const e={...session.case_public_state.evidence_options.find(e=>e.id===id),content:id==='E01'?{command:'已发送',grasp_success:false}:{planned_x_mm:0,actual_x_mm:70,delta_x_mm:70}};
   session.released_evidence.push(e);session.allowed_actions=['inspect_evidence',session.hypotheses.length?'revise_hypothesis':'submit_hypothesis'];
   return json(route,{evidence:e,session});
  }
  if(path.endsWith('/hypotheses')) {
   const {hypothesis}=req.postDataJSON();session.hypotheses.push(hypothesis);session.current_hypothesis=hypothesis;session.public_stage='INVESTIGATING';
   session.allowed_actions=['inspect_evidence','revise_hypothesis',...(session.hypotheses.length>1?['submit_diagnosis']:[])];return json(route,session);
  }
  if(path.endsWith('/tutor')) {
   await new Promise(r=>setTimeout(r,200));return json(route,{tutor:{message:'请比较计划位置与实际测量值，再修正你的假设。',suggested_action:'inspect_evidence'},session,tutor_mode:'rule_fallback'});
  }
  if(path.endsWith('/diagnosis')) { diagnosticPosts++;session.public_stage='SUBMITTED';session.allowed_actions=['reflect'];return json(route,session); }
  if(path.endsWith('/report')) {
   if(++reportReads===1)return json(route,{detail:'report_not_ready'},409);
   session.public_stage='REVIEWED';
   return json(route,{contract_version:'0.4.0',rubric_version:'fixture',session_id:session.session_id,case_id:'ST-001',diagnosis:{submitted:{diagnosis_type:'object_pose_mismatch',reasoning:'位姿测量显示偏移。'},assessment:'correct',reference_explanation:'测量结果支持工件位姿偏移。'},evidence_used:['E01','E02'],dimension_results:Object.fromEntries(['hypothesis','evidence','efficiency','updating','safety'].map(d=>[d,{status:d==='safety'?'not_assessed':'scored',score:d==='safety'?null:90,weight:.2,rationale:d==='safety'?'本次未提供安全评价机会。':'能够根据新证据修正推理。',rule_ids:[],trace_indices:[]} ])),overall:{score:90,coverage:.8,included_dimensions:['hypothesis','evidence','efficiency','updating']},feedback_summary:'你完成了基于证据的假设修正。',next_learning_step:'尝试用另一条证据排除替代解释。',tutor_mode:'rule_fallback'});
  }
  return json(route,session);
 });
}
async function go(page,key){await page.locator(`[data-step="${key}"]`).click();}
async function assertPageQuality(page) {
 const result=await page.evaluate(()=>{
  const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const nodes=[...document.querySelectorAll('body *')];
  const english=nodes.filter(e=>visible(e)&&e.children.length===0&&/[A-Za-z]{2,}/.test(e.textContent||'')).map(e=>(e.textContent||'').trim());
  const ids=nodes.map(e=>e.id).filter(Boolean);const duplicateIds=[...new Set(ids.filter((id,i)=>ids.indexOf(id)!==i))];
  const unlabeled=nodes.filter(e=>visible(e)&&e.matches('button,input,textarea,select')&&!((e.getAttribute('aria-label')||e.textContent||e.getAttribute('title')||'').trim())&&!document.querySelector(`label[for="${e.id}"]`)).map(e=>e.id||e.tagName);
  return {english,duplicateIds,unlabeled};
 });
 assert.deepEqual(result,{english:[],duplicateIds:[],unlabeled:[]});
}
try {
 console.log("browser launched");
 const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));await setup(page);await page.goto(base,{waitUntil:"domcontentloaded"});console.log("page loaded");
 await page.waitForFunction(()=>document.querySelector('#tutor-status').textContent==='可用');
 await assertPageQuality(page);
 await go(page,'diagnosis'); assert.equal(await page.locator('#diagnosis-submit').isDisabled(),true);
 await go(page,'evidence');assert.equal(await page.locator('.evidence-values').count(),0);
 await page.locator('[data-evidence-id=E01]').click();await page.locator('.evidence-values').waitFor();
 await page.locator('[data-evidence-id=E01]').click();assert.equal(await page.locator('.evidence-values').isHidden(),true);
 await page.locator('[data-evidence-id=E01]').click();await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(out,'desktop-evidence.png')});
 const sid=await page.locator('#session-code').getAttribute('title');
 await go(page,'hypothesis');await page.locator('#hypothesis-input').fill('尚未提交的推理草稿');await go(page,'evidence');await page.locator('[data-evidence-id=E02]').click();await page.waitForFunction(()=>document.querySelector('#learning-progress').textContent.startsWith('2'));
 await go(page,'hypothesis');assert.equal(await page.locator('#hypothesis-input').inputValue(),'尚未提交的推理草稿');
 await page.locator('#hypothesis-submit').click();await page.waitForFunction(()=>document.querySelector('#hypothesis-count').textContent.startsWith('1'));
 await page.locator('#hypothesis-input').fill('位姿测量显示工件发生偏移。');await page.locator('#hypothesis-submit').click();await page.waitForFunction(()=>document.querySelector('#hypothesis-count').textContent.startsWith('2'));
 await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(out,'desktop-hypothesis.png')});
 await page.locator('#assistant-open').click();await page.locator('#tutor-input').fill('应该如何比较测量值？');await page.locator('#tutor-submit').click();await page.locator('#assistant-close').click();
 await page.waitForFunction(()=>document.querySelectorAll('.tutor-message.tutor').length===1);assert.equal(await page.locator('#assistant-dialog').evaluate(d=>d.open),false);
 await page.locator('#assistant-open').click();await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(out,'desktop-assistant.png')});await page.keyboard.press('Escape');await page.waitForFunction(()=>document.activeElement.id==='assistant-open');assert.equal(await page.evaluate(()=>document.activeElement.id),'assistant-open');
 await go(page,'evidence');await page.locator('[data-evidence-id=E03]').click();await page.locator('#learning-error').waitFor();assert.match(await page.locator('#learning-error').textContent(),/当前学习阶段/);
 await go(page,'diagnosis');await page.locator('#diagnosis-type').selectOption('object_pose_mismatch');await page.locator('#diagnosis-reasoning').fill('位姿测量显示偏移。');await page.locator('input[value=E02]').check();
 await go(page,'evidence');await go(page,'diagnosis');assert.equal(await page.locator('#diagnosis-reasoning').inputValue(),'位姿测量显示偏移。');assert.equal(await page.locator('input[value=E02]').isChecked(),true);
 await page.locator('#diagnosis-submit').click();await page.locator('#report-retry').waitFor();assert.equal(await page.locator('#diagnosis-submit').isDisabled(),true);
 await page.locator('#report-retry').click();await page.locator('#report-panel').waitFor();assert.equal(diagnosticPosts,1);assert.match(await page.locator('[data-dimension=safety]').textContent(),/未评估/);
 await assertPageQuality(page);await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(out,'desktop-report.png'),fullPage:true});await page.locator('#report-back').click();assert.equal(await page.locator('#cad-viewport canvas').isVisible(),true);assert.equal(await page.locator('#session-code').getAttribute('title'),sid);
 await page.locator('#reset-button').click();assert.match(await page.locator('#learning-progress').textContent(),/2 \/ 3/);
 for(const size of [{width:1366,height:768},{width:1440,height:900},{width:768,height:1024},{width:390,height:844}]) {
  await page.setViewportSize(size);await go(page,'evidence');await page.waitForTimeout(100);
  const layout=await page.evaluate(()=>({client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,next:document.querySelector('#step-next').getBoundingClientRect().bottom,height:innerHeight}));assert.equal(layout.scroll,layout.client);if(size.width>=1100)assert.ok(layout.next<=layout.height);
  if(size.width===390)await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(out,'mobile-evidence.png'),fullPage:true});
 }
 assert.deepEqual(errors,[]);
 console.log('PASS: frontend fixture – permissions, evidence disclosure/folding/errors, hypothesis draft + revision, assistant close/reopen + focus, citations persistence, report retry without duplicate POST, session-preserving replay, 4 viewport widths, no page errors.');
 await page.close();
 // Production failure state: no fake data is injected by the app itself.
 const offline=await browser.newPage();await offline.route('**/api/**',r=>{const path=new URL(r.request().url()).pathname;if(path.endsWith('/auth/me'))return r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({user:{user_id:'fixture-user',username:'fixture',display_name:'测试学员'},expires_at:1800000000,csrf_token:'x'.repeat(32)})});return r.fulfill({status:503,body:'unavailable'});});await offline.goto(base);await offline.getByText('场景加载失败',{exact:true}).waitFor();console.log('PASS: scene API failure displays a recoverable Chinese error.');
} finally {await browser.close();await server.close();}
