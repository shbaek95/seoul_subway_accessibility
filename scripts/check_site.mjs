// 실제 브라우저에서 지도·차트·지역 선택과 모바일 레이아웃을 검사합니다.
import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import path from 'node:path';
const require=createRequire(import.meta.url);
let chromium;
try{({chromium}=require('playwright'));}catch{({chromium}=require('../../seoul_rent_api/node_modules/playwright'));}
const base=process.argv[2]||'http://127.0.0.1:8093';
const tag=base.startsWith('https:')?'deployed':'local';
await fs.mkdir('.local',{recursive:true});await fs.mkdir('reports',{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
const errors=[],failed=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)failed.push({url:r.url(),status:r.status()});});
try{
 const response=await page.goto(base,{waitUntil:'networkidle'});assert.equal(response.status(),200);
 await page.waitForSelector('html[data-ready="true"]',{timeout:30000});
 assert.equal(await page.locator('#density-map path[data-code]').count(),426);
 assert.equal(await page.locator('#access-map path[data-code]').count(),426);
 assert.equal(await page.locator('#dong-select option').count(),426);
 assert.ok(await page.locator('#scatter circle').count()>0);
 const first=await page.locator('#dong-select option').first().getAttribute('value');
 await page.locator('#dong-select').selectOption(first);assert.ok((await page.locator('#selected').innerText()).includes('사직동'));
 const mapPath=page.locator('#density-map path[data-code]').nth(40);
 await mapPath.scrollIntoViewIfNeeded();
 const position=await mapPath.evaluate(e=>{const b=e.getBBox(),matrix=e.getScreenCTM();for(let iy=1;iy<40;iy++)for(let ix=1;ix<40;ix++){const p=new DOMPoint(b.x+b.width*ix/40,b.y+b.height*iy/40);if(e.isPointInFill(p)){const screen=p.matrixTransform(matrix);if(document.elementFromPoint(screen.x,screen.y)===e)return {x:screen.x,y:screen.y};}}throw Error('지도 내부 클릭 좌표를 찾지 못함');});
 await page.mouse.click(position.x,position.y);
 const clicked=await page.locator('#density-map path[data-code]').nth(40).getAttribute('data-code');assert.equal(await page.locator('#dong-select').inputValue(),clicked);
 await page.locator('#scatter circle').nth(10).focus();await page.keyboard.press('Enter');
 const scatter=await page.locator('#scatter circle').nth(10).getAttribute('data-code');assert.equal(await page.locator('#dong-select').inputValue(),scatter);
 await page.locator('#search').fill('종로구');assert.ok(await page.locator('#results-body tr').count()>0);assert.ok((await page.locator('#row-count').innerText()).includes('17개'));
 await page.locator('#search').fill('');
 const payload=await page.request.get(base+'/results.geojson');assert.equal(payload.status(),200);const geo=await payload.json();assert.equal(geo.features.length,426);
 for(const asset of ['app.js','style.css','summary.json','sources.json','validation.json','results.csv','report.md'])assert.equal((await page.request.get(base+'/'+asset)).status(),200,asset);
 await page.locator('#dong-select').selectOption(first);await page.evaluate(()=>scrollTo(0,0));
 await page.screenshot({path:'.local/'+tag+'-desktop.png',fullPage:true});
 // 대표 이미지는 실제 사이트의 제목·핵심 수치·지도·선택 결과가 읽히는 가로 화면입니다.
 await page.setViewportSize({width:1600,height:1000});await page.goto(base+'?view=summary',{waitUntil:'networkidle'});await page.waitForSelector('html[data-ready="true"]');
 await page.screenshot({path:'reports/representative.png',fullPage:false});
 await page.setViewportSize({width:390,height:844});await page.goto(base,{waitUntil:'networkidle'});await page.waitForSelector('html[data-ready="true"]');await page.evaluate(()=>scrollTo(0,0));
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'모바일 가로 넘침');
 await page.locator('#dong-select').selectOption(clicked);assert.equal(await page.locator('#dong-select').inputValue(),clicked);
 await page.screenshot({path:'.local/'+tag+'-mobile.png',fullPage:true});
 // public 외부 파일이 Pages에서 공개되지 않는지 확인합니다.
 if(tag==='deployed')for(const target of ['/.env','/.git/config','/README.md','/scripts/analyze.py','/data/raw/2024년_인구_다사_100M.csv'])assert.equal((await page.request.get(base+target)).status(),404,target);
 assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);
 const checks={base,desktop:[1440,1100],mobile:[390,844],maps:426,options:426,selection:'지도 클릭·키보드·드롭다운 통과',scatter:'통과',search:'통과',assets:'통과',mobileOverflow:false,browserErrors:errors,failedResponses:failed,representative:'reports/representative.png'};
 await fs.writeFile('reports/browser-'+tag+'.json',JSON.stringify(checks,null,2));console.log(JSON.stringify(checks,null,2));
}finally{await browser.close();}
