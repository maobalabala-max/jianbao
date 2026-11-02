(function(){
"use strict";
var D, LAB={}, GRP={}, CAT={}, ROWS=[], S={mech:null,supp:null,pq:"",pg:"cat",tf:{mech:"",ev:0,q:"",cat:""},page:0,sort:{k:"score",d:-1}};
var PAGE=50;
var app=document.getElementById("app");
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
var EVL=["无/推测","体外","动物/小型人体","多项人体RCT/荟萃"];
function refHtml(ids){
  if(!ids||!ids.length) return "";
  return '<ol class="refs">'+ids.map(function(id){var r=D.refs[String(id)];if(!r)return "";
    return "<li>"+esc(r.first)+"（"+esc(r.year)+"）"+esc(r.title)+". <i>"+esc(r.journal)+"</i>. "+
      '<a href="https://pubmed.ncbi.nlm.nih.gov/'+r.pmid+'/" target="_blank" rel="noopener">PMID '+r.pmid+"</a>"+
      (r.doi?' · <a href="https://doi.org/'+esc(r.doi)+'" target="_blank" rel="noopener">DOI</a>':"")+"</li>";}).join("")+"</ol>";
}
function flags(m){
  var h="";
  if(m.disputed) h+='<span class="flag f-dis" title="'+esc(m.disputed)+'">有争议</span>';
  if(m.needsSource) h+='<span class="flag f-need">需补充来源</span>';
  return h;
}
function band(v){return v>=67?"b4":v>=30?"b3":v>=15?"b2":v>0?"b1":"b0";}
var LEG='<div class="legend"><span><i style="background:var(--b4)"></i>≥67</span><span><i style="background:var(--b3)"></i>30–66</span><span><i style="background:var(--b2)"></i>15–29</span><span><i style="background:var(--b1)"></i>&lt;15</span></div>';
function safeTags(s){return s.safety.map(function(w){return '<span class="flag f-warn">⚠ '+esc(w)+"</span>";}).join("");}
function sre(m){return '<span class="dots">强度 <b>'+m.strength+'</b> · 证据 <b>'+m.evidence+'</b> · 可达 <b>'+m.reach+"</b></span>";}
function setTab(v){[].forEach.call(document.querySelectorAll(".tabs a"),function(a){a.classList.toggle("on",a.dataset.view===v);});}

/* ---------- 按机制 ---------- */
function viewMech(){
  var counts={};ROWS.forEach(function(r){counts[r.mech]=(counts[r.mech]||0)+1;});
  if(!S.mech){var best=null;Object.keys(counts).forEach(function(k){if(!best||counts[k]>counts[best])best=k;});S.mech=best;}
  var h='<section class="card"><h2>选择一个机制</h2><div class="mgroups">';
  D.taxonomy.forEach(function(g){
    h+='<div class="mg"><h4>'+esc(g.group)+"</h4>";
    g.items.forEach(function(it){var n=counts[it[0]]||0;
      h+='<button class="chip'+(S.mech===it[0]?" on":"")+(n?"":" empty")+'" data-mech="'+it[0]+'">'+esc(it[1])+'<span class="n">'+n+"</span></button>";});
    h+="</div>";});
  h+="</div></section>";
  var rs=ROWS.filter(function(r){return r.mech===S.mech;}).sort(function(a,b){return b.score-a.score;});
  h+='<section class="card"><p class="kicker">'+esc(GRP[S.mech])+'</p><div class="mtitle"><h2>'+esc(LAB[S.mech])+' <span class="muted small">'+rs.length+' 条</span></h2>'+LEG+'</div>';
  if(!rs.length) h+='<p class="muted">暂无归入此机制的补充剂。</p>';
  rs.forEach(function(r,i){var b=band(r.score);
    h+='<div class="row"><div class="rk">'+(i+1)+'</div><div class="nm"><a href="#supp/'+r.s.id+'">'+esc(r.s.zh)+"</a><small>"+esc(r.s.en)+" · "+esc(CAT[r.s.cat])+"</small></div>"+
      '<div class="bar '+b+'" title="综合分 '+r.score+'"><i style="width:'+Math.max(r.score,2)+'%"></i></div><div class="sc '+b+'">'+r.score+"</div>"+
      '<div class="sub3">'+sre(r)+" "+(r.s.primary===r.mech?'<span class="flag f-prim">主要机制</span>':"")+flags(r)+
      '<div class="note">'+esc(r.note)+"</div>"+(r.disputed?'<div class="disp">争议：'+esc(r.disputed)+"</div>":"")+
      "<details><summary>适用前提与参考文献（"+r.refs.length+"）</summary>"+'<div class="small muted">适用前提：'+esc(r.s.applic)+"</div>"+(r.s.safety.length?'<div>'+safeTags(r.s)+"</div>":"")+refHtml(r.refs)+"</details></div></div>";});
  h+="</section>";
  app.innerHTML=h;
  [].forEach.call(app.querySelectorAll("[data-mech]"),function(b){b.onclick=function(){S.mech=b.dataset.mech;viewMech();};});
}

/* ---------- 雷达图 ---------- */
function radar(s){
  var SHORT=["氧化/炎症","免疫","能量/线粒体","神经内分泌","肠道","结构/修复","其他"];var groups=D.taxonomy.map(function(g,i){return SHORT[i]||g.group;});
  var vals=D.taxonomy.map(function(g){var ids=g.items.map(function(i){return i[0];});var v=0;
    s.mechs.forEach(function(m){if(ids.indexOf(m.mech)>=0&&m.score>v)v=m.score;});return v;});
  var W=420,H=330,cx=210,cy=168,R=104,n=groups.length;
  function pt(i,r){var a=-Math.PI/2+i*2*Math.PI/n;return [cx+r*Math.cos(a),cy+r*Math.sin(a)];}
  var o='<svg viewBox="0 0 '+W+" "+H+'" role="img" aria-label="'+esc(s.zh)+' 各机制大类最高综合分雷达图">';
  [25,50,75,100].forEach(function(l){o+='<polygon class="rg'+(l===100?" o":"")+'" points="'+groups.map(function(_,i){return pt(i,R*l/100).join(",");}).join(" ")+'"/>';});
  groups.forEach(function(g,i){var p=pt(i,R);o+='<line class="rg" x1="'+cx+'" y1="'+cy+'" x2="'+p[0]+'" y2="'+p[1]+'"/>';
    var q=pt(i,R+22),anc=Math.abs(q[0]-cx)<8?"middle":(q[0]>cx?"start":"end");
    o+='<text x="'+q[0]+'" y="'+(q[1]+4)+'" class="rl" text-anchor="'+anc+'">'+esc(g)+"</text>";});
  o+='<polygon class="rp" points="'+vals.map(function(v,i){return pt(i,R*v/100).join(",");}).join(" ")+'"/>';
  vals.forEach(function(v,i){if(v>0){var p=pt(i,R*v/100);o+='<circle class="rd" cx="'+p[0]+'" cy="'+p[1]+'" r="3.5"/><text class="rv" x="'+(p[0]+6)+'" y="'+(p[1]-6)+'">'+v+"</text>";}});
  o+='<text x="'+cx+'" y="'+(cy-R*0.5-2)+'" class="rt" text-anchor="middle">50</text>';
  return o+"</svg>";
}
function pips(v){var h='<div class="pips">';for(var i=1;i<=3;i++)h+="<i"+(i<=v?' class="f"':"")+"></i>";return h+"</div>";}

/* ---------- 按补充剂 ---------- */
function viewSupp(){
  if(!S.supp) S.supp=D.supplements[0].id;
  var s=D.supplements.filter(function(x){return x.id===S.supp;})[0]||D.supplements[0];
  var h='<section class="card"><h2>选择补充剂 <span class="muted small">共 '+D.supplements.length+' 种</span></h2>'+
    '<div class="filters"><input type="search" id="pq" placeholder="搜索中文/英文名" value="'+esc(S.pq)+'">'+
    '<label>分组 <select id="pg"><option value="cat"'+(S.pg==="cat"?" selected":"")+'>按类别</option><option value="mech"'+(S.pg==="mech"?" selected":"")+'>按主要机制大类</option></select></label></div><div id="plist"></div></section>';
  var top=Math.max.apply(null,s.mechs.map(function(m){return m.score;}));
  h+='<section class="card"><p class="kicker">'+esc(CAT[s.cat])+'</p><div class="shead"><div><h2>'+esc(s.zh)+'</h2><div class="en">'+esc(s.en)+'</div></div><div class="topscore"><b class="sc '+band(top)+'">'+top+'</b><span>最高综合分 · '+s.mechs.length+' 条机制</span></div></div>';
  h+='<div class="sgrid"><div class="radar">'+radar(s)+'<p class="cap">各机制大类中的最高综合分（0–100）</p></div><div>';
  h+='<dl class="kv"><dt>类别</dt><dd>'+esc(CAT[s.cat])+'</dd><dt>常见形式</dt><dd>'+esc(s.forms)+"</dd><dt>主要机制</dt><dd>"+esc(LAB[s.primary])+"</dd><dt>常用剂量</dt><dd>"+esc(s.dose)+"</dd><dt>适用前提</dt><dd>"+esc(s.applic)+"</dd><dt>安全提示</dt><dd>"+(safeTags(s)||'<span class="muted">—</span>')+"</dd></dl>";
  if(s.suppRefs&&s.suppRefs.length) h+='<details><summary>补充文献（适用前提/安全性）</summary>'+refHtml(s.suppRefs)+"</details>";
  h+="</div></div>";
  h+='<div class="mtitle" style="margin-top:22px"><h3 style="margin:0">各机制评分</h3>'+LEG+'</div>';
  s.mechs.slice().sort(function(a,b){return b.score-a.score;}).forEach(function(m){var b=band(m.score);
    h+='<div class="mrow"><div class="mhead"><span class="t"><a href="#mech/'+m.mech+'">'+esc(LAB[m.mech])+'</a> <span class="muted small">'+esc(GRP[m.mech])+"</span></span>"+
      '<span><b class="scb sc '+b+'">'+m.score+'</b><span class="muted small"> / 100</span></span></div>'+
      '<div class="bar '+b+'"><i style="width:'+Math.max(m.score,2)+'%"></i></div>'+
      '<div class="sre"><div>强度 '+m.strength+pips(m.strength)+"</div><div>证据 "+m.evidence+"（"+EVL[m.evidence]+"）"+pips(m.evidence)+"</div><div>可达性 "+m.reach+pips(m.reach)+"</div></div>"+
      (s.primary===m.mech?'<span class="flag f-prim">主要机制</span>':"")+flags(m)+
      '<div class="small" style="margin-top:4px">'+esc(m.note)+"</div>"+(m.disputed?'<div class="disp">争议：'+esc(m.disputed)+"</div>":"")+refHtml(m.refs)+"</div>";});
  h+="</section>";
  app.innerHTML=h;
  drawPicker(s.id);
  document.getElementById("pq").oninput=function(e){S.pq=e.target.value;drawPicker(s.id);};
  document.getElementById("pg").onchange=function(e){S.pg=e.target.value;drawPicker(s.id);};
}
function drawPicker(cur){
  var q=S.pq.trim().toLowerCase(), groups=[], map={};
  if(S.pg==="cat") D.categories.forEach(function(c){map[c[0]]={t:c[1],a:[]};groups.push(map[c[0]]);});
  else D.taxonomy.forEach(function(g){map[g.group]={t:g.group,a:[]};groups.push(map[g.group]);});
  D.supplements.forEach(function(x){
    if(q&&(x.zh+" "+x.en).toLowerCase().indexOf(q)<0) return;
    var k=S.pg==="cat"?x.cat:GRP[x.primary]; if(map[k]) map[k].a.push(x);});
  var h="",n=0;
  groups.forEach(function(g){ if(!g.a.length) return; n+=g.a.length;
    h+='<div class="pgrp"><h4>'+esc(g.t)+' <span class="n">'+g.a.length+'</span></h4>'+g.a.map(function(x){
      return '<a class="chip'+(x.id===cur?" on":"")+'" href="#supp/'+x.id+'" title="'+esc(x.en)+'">'+esc(x.zh)+'</a>';}).join("")+"</div>";});
  document.getElementById("plist").innerHTML=h||'<p class="muted small">无匹配结果。</p>';
}

/* ---------- 总表 ---------- */
function viewTable(){
  var f=S.tf;
  var h='<section class="card"><div class="filters"><label>机制 <select id="fm"><option value="">全部</option>';
  D.taxonomy.forEach(function(g){h+='<optgroup label="'+esc(g.group)+'">';g.items.forEach(function(it){h+='<option value="'+it[0]+'"'+(f.mech===it[0]?" selected":"")+">"+esc(it[1])+"</option>";});h+="</optgroup>";});
  h+='</select></label><label>最低证据 <select id="fe">'+[0,1,2,3].map(function(v){return '<option value="'+v+'"'+(f.ev===v?" selected":"")+">≥ "+v+"（"+EVL[v]+"）</option>";}).join("")+
    '</select></label><label>类别 <select id="fc"><option value="">全部</option>'+D.categories.map(function(c){return '<option value="'+c[0]+'"'+(f.cat===c[0]?" selected":"")+">"+esc(c[1])+"</option>";}).join("")+'</select></label><input type="search" id="fq" placeholder="搜索名称" value="'+esc(f.q)+'"><span class="muted small" id="cnt"></span></div><div class="tw"><table><thead><tr>';
  var cols=[["zh","补充剂",""],["cat","类别","hm"],["mech","机制",""],["strength","强度","num"],["evidence","证据","num"],["reach","可达","num"],["score","综合分","num"],["flags","标记",""]];
  cols.forEach(function(c){h+='<th data-k="'+c[0]+'" class="'+c[2]+'">'+c[1]+(S.sort.k===c[0]?' <span class="ar">'+(S.sort.d>0?"▲":"▼")+"</span>":"")+"</th>";});
  h+='</tr></thead><tbody id="tb"></tbody></table></div><div class="pager" id="pager"></div><p class="small muted">点击表头排序；点击补充剂名查看详情。</p></section>';
  app.innerHTML=h;
  function draw(){
    var q=f.q.trim().toLowerCase();
    var rs=ROWS.filter(function(r){return (!f.mech||r.mech===f.mech)&&(!f.cat||r.s.cat===f.cat)&&r.evidence>=f.ev&&(!q||(r.s.zh+r.s.en).toLowerCase().indexOf(q)>=0);});
    var k=S.sort.k,d=S.sort.d;
    rs.sort(function(a,b){var x,y;
      if(k==="zh"){x=a.s.zh;y=b.s.zh;return d*x.localeCompare(y,"zh");}
      if(k==="mech"){return d*LAB[a.mech].localeCompare(LAB[b.mech],"zh");}
      if(k==="cat"){return d*CAT[a.s.cat].localeCompare(CAT[b.s.cat],"zh")||b.score-a.score;}
      if(k==="flags"){x=(a.disputed?1:0)+(a.needsSource?1:0);y=(b.disputed?1:0)+(b.needsSource?1:0);}
      else{x=a[k];y=b[k];}
      return d*(x-y)||b.score-a.score;});
    var pages=Math.max(1,Math.ceil(rs.length/PAGE)); if(S.page>=pages) S.page=pages-1;
    var all=rs; rs=rs.slice(S.page*PAGE,(S.page+1)*PAGE);
    var pg="";
    if(pages>1){for(var i=0;i<pages;i++) pg+='<button class="chip'+(i===S.page?" on":"")+'" data-p="'+i+'">'+(i*PAGE+1)+"–"+Math.min((i+1)*PAGE,all.length)+"</button>";}
    document.getElementById("pager").innerHTML=pg;
    [].forEach.call(document.querySelectorAll("#pager [data-p]"),function(b){b.onclick=function(){S.page=+b.dataset.p;draw();};});
    document.getElementById("tb").innerHTML=rs.map(function(r){
      return '<tr><td><a href="#supp/'+r.s.id+'">'+esc(r.s.zh)+"</a></td><td class=\"muted hm\">"+esc(CAT[r.s.cat])+"</td><td>"+esc(LAB[r.mech])+(r.s.primary===r.mech?' <span class="flag f-prim">主</span>':"")+'</td><td class="num">'+r.strength+'</td><td class="num">'+r.evidence+'</td><td class="num">'+r.reach+
        '</td><td class="num '+band(r.score)+'"><b class="sc '+band(r.score)+'">'+r.score+'</b><span class="minibar"><i style="width:'+r.score+'%"></i></span></td><td>'+flags(r)+"</td></tr>";}).join("");
    document.getElementById("cnt").textContent="共 "+all.length+" 条";
  }
  draw();
  document.getElementById("fm").onchange=function(e){f.mech=e.target.value;S.page=0;draw();};
  document.getElementById("fe").onchange=function(e){f.ev=+e.target.value;S.page=0;draw();};
  document.getElementById("fc").onchange=function(e){f.cat=e.target.value;S.page=0;draw();};
  document.getElementById("fq").oninput=function(e){f.q=e.target.value;S.page=0;draw();};
  [].forEach.call(app.querySelectorAll("th"),function(th){th.onclick=function(){var k=th.dataset.k;
    if(S.sort.k===k)S.sort.d=-S.sort.d;else{S.sort.k=k;S.sort.d=(k==="zh"||k==="mech")?1:-1;}S.page=0;viewTable();};});
}

/* ---------- 评分说明 ---------- */
function viewRubric(){
  var dis=ROWS.filter(function(r){return r.disputed;}).length,need=ROWS.filter(function(r){return r.needsSource;}).length;
  var nRef=Object.keys(D.refs).length;
  app.innerHTML='<section class="card rub"><h2>评分说明</h2>'+
  '<p class="small"><b>数据规模：</b>'+D.supplements.length+' 种补充剂、'+ROWS.length+' 条“补充剂 × 机制”记录、'+nRef+' 篇 PubMed 文献；最后更新 '+esc(D.updated)+'（数据版本 '+esc(D.version)+'）。</p>'+
  "<p>每一条记录是“一种补充剂 × 一种机制”。同一补充剂可有多条记录，各自独立评分。三个维度均为 0–3 分：</p>"+
  '<div class="tw"><table><thead><tr><th>分值</th><th>强度（作用是否直接、有效）</th><th>证据（该机制/相关效应的最高证据）</th><th>可达性（常规口服剂量能否在体内达到有效浓度）</th></tr></thead><tbody>'+
  "<tr><td>0</td><td>无作用或纯推测</td><td>无证据/推测</td><td>基本不可能达到</td></tr>"+
  "<tr><td>1</td><td>间接、微弱，或需远超生理的浓度</td><td>仅体外（细胞）研究</td><td>吸收很差，组织浓度远低于体外有效浓度</td></tr>"+
  "<tr><td>2</td><td>中等，作用明确但幅度有限</td><td>动物研究，或少量/小样本人体试验</td><td>部分可达（如仅血液、或仅在局部肠道）</td></tr>"+
  "<tr><td>3</td><td>直接、强效，为该机制的典型干预</td><td>多项人体 RCT 或荟萃分析且结论基本一致</td><td>常规剂量可稳定达到有效水平</td></tr>"+
  "</tbody></table></div>"+
  "<h3>综合分公式</h3><p><b>"+esc(D.formula)+"</b>。27 = 3×3×3 为满分。采用乘法是有意为之：任何一个维度为 0，综合分即为 0；体外很强但吸收不了的成分（如姜黄素）会被显著拉低。可能取值为 0、4、7、11、15、22、30、33、44、67、100 等离散档位，档位之间的细微差别不应过度解读。</p><p class='small'>页面配色按综合分分档：</p>"+LEG+
  "<h3>不计入评分的字段</h3><ul><li><b>适用前提</b>：功能医学式的“谁更可能获益”说明（如“主要对缺乏者有效”）。高分≠所有人都需要。</li>"+
  '<li><b>安全/相互作用</b>：以 <span class="flag f-warn">⚠ 警示标签</span> 单独展示，不影响分数。</li>'+
  '<li><b>争议标记</b>：<span class="flag f-dis">有争议</span> 表示分数本身在文献中存在明显分歧（当前 '+dis+' 条）；<span class="flag f-need">需补充来源</span> 表示该条记录缺少可核实的直接支持文献，证据分已相应下调（当前 '+need+" 条）。</li></ul>"+
  "<h3>注意事项</h3><ul>"+
  "<li>评分为基于所列文献与综述的主观判断，主要用于横向比较“机制有多靠谱”，并非疗效排名。</li>"+
  "<li>“证据”一栏评价的是该机制或与之直接相关的效应；人体结局获益不一定经由所列机制实现。</li>"+
  "<li>许多多酚类机制主要来自体外实验，且所用浓度远高于口服后血药浓度。</li>"+
  "<li>益生菌、β-葡聚糖、胶原等的效果高度依赖具体菌株/来源/制剂，评分代表“该类别中证据较好的产品”。</li>"+
  "<li>所有文献均通过 PubMed 核对 PMID 存在且标题与内容对应；文献列表并非系统综述。</li>"+
  "<li>收录范围为常用补充剂，并非穷尽；同一补充剂的不同制剂/剂量差异可能很大。</li><li>“类别”按成分来源/性质划分（维生素、矿物质、植物提取物、内源性代谢物等），仅用于浏览，不影响评分。</li><li>主要机制（标“主”）指该补充剂最常被引用的作用机制，不一定是综合分最高的一条。</li></ul>"+
  '<p class="warn-line" style="font-size:.95rem"><b>仅供个人参考，不构成医疗建议。</b>服用任何补充剂前，尤其在服药、妊娠/哺乳、有慢性病或即将手术时，请咨询医生或药师。</p></section>';
}

/* ---------- 路由 ---------- */
function route(){
  var h=(location.hash||"#mech").slice(1).split("/"),v=h[0];
  if(v==="supp"){if(h[1])S.supp=h[1];setTab("supp");viewSupp();}
  else if(v==="table"){setTab("table");viewTable();}
  else if(v==="rubric"){setTab("rubric");viewRubric();}
  else{if(h[1]&&LAB[h[1]])S.mech=h[1];setTab("mech");viewMech();}
  var nav=document.getElementById("nav"),y=nav?nav.offsetTop:0;
  if(window.scrollY>y) window.scrollTo(0,y);
}
fetch("data.json",{cache:"no-cache"}).then(function(r){return r.json();}).then(function(d){
  D=d;
  d.categories.forEach(function(c){CAT[c[0]]=c[1];});
  d.taxonomy.forEach(function(g){g.items.forEach(function(it){LAB[it[0]]=it[1];GRP[it[0]]=g.group;});});
  d.supplements.forEach(function(s){s.mechs.forEach(function(m){var r=Object.assign({},m);r.s=s;ROWS.push(r);});});
  var nm=0;d.taxonomy.forEach(function(g){nm+=g.items.length;});
  var sv=[d.supplements.length,d.nRecords,Object.keys(d.refs).length,nm];
  [].forEach.call(document.querySelectorAll("#stats b"),function(b,i){b.textContent=sv[i];});
  var nav=document.getElementById("nav");
  function stk(){nav.classList.toggle("stuck",window.scrollY>nav.offsetTop-1);}
  window.addEventListener("scroll",stk,{passive:true});stk();
  document.getElementById("ver").textContent=d.version;document.getElementById("upd").textContent=d.updated;
  window.addEventListener("hashchange",route);route();
}).catch(function(e){app.innerHTML='<p class="card">数据加载失败：'+esc(e.message)+"</p>";});
})();
