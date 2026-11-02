(function(){
"use strict";
var D, LAB={}, GRP={}, ROWS=[], S={mech:null,supp:null,tf:{mech:"",ev:0,q:""},sort:{k:"score",d:-1}};
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
  h+='<section class="card"><h2>'+esc(LAB[S.mech])+' <span class="muted small">· '+esc(GRP[S.mech])+"</span></h2>";
  if(!rs.length) h+='<p class="muted">本样本（20 种）中暂无归入此机制的补充剂。</p>';
  rs.forEach(function(r){
    h+='<div class="row"><div class="nm"><a href="#supp/'+r.s.id+'">'+esc(r.s.zh)+"</a><small>"+esc(r.s.en)+"</small></div>"+
      '<div class="bar" title="综合分 '+r.score+'"><i style="width:'+Math.max(r.score,2)+'%"></i></div><div class="sc">'+r.score+"</div>"+
      '<div class="sub3">'+sre(r)+" "+(r.s.primary===r.mech?'<span class="flag f-prim">主要机制</span>':"")+flags(r)+
      "<div>"+esc(r.note)+"</div>"+(r.disputed?'<div class="small" style="color:var(--dis)">争议：'+esc(r.disputed)+"</div>":"")+
      '<div class="small muted">适用前提：'+esc(r.s.applic)+"</div>"+
      "<details><summary>参考文献（"+r.refs.length+"）</summary>"+refHtml(r.refs)+"</details></div></div>";});
  h+="</section>";
  app.innerHTML=h;
  [].forEach.call(app.querySelectorAll("[data-mech]"),function(b){b.onclick=function(){S.mech=b.dataset.mech;viewMech();};});
}

/* ---------- 雷达图 ---------- */
function radar(s){
  var SHORT=["氧化/炎症","免疫","能量/线粒体","神经内分泌","肠道","结构/修复","其他"];var groups=D.taxonomy.map(function(g,i){return SHORT[i]||g.group;});
  var vals=D.taxonomy.map(function(g){var ids=g.items.map(function(i){return i[0];});var v=0;
    s.mechs.forEach(function(m){if(ids.indexOf(m.mech)>=0&&m.score>v)v=m.score;});return v;});
  var W=400,H=320,cx=200,cy=165,R=100,n=groups.length;
  function pt(i,r){var a=-Math.PI/2+i*2*Math.PI/n;return [cx+r*Math.cos(a),cy+r*Math.sin(a)];}
  var o='<svg viewBox="0 0 '+W+" "+H+'" role="img" aria-label="'+esc(s.zh)+' 各机制大类最高综合分雷达图">';
  [25,50,75,100].forEach(function(l){o+='<polygon fill="none" stroke="#e4e7ec" points="'+groups.map(function(_,i){return pt(i,R*l/100).join(",");}).join(" ")+'"/>';});
  groups.forEach(function(g,i){var p=pt(i,R);o+='<line x1="'+cx+'" y1="'+cy+'" x2="'+p[0]+'" y2="'+p[1]+'" stroke="#e4e7ec"/>';
    var q=pt(i,R+22),anc=Math.abs(q[0]-cx)<8?"middle":(q[0]>cx?"start":"end");
    o+='<text x="'+q[0]+'" y="'+(q[1]+4)+'" font-size="11" fill="#475467" text-anchor="'+anc+'">'+esc(g)+"</text>";});
  o+='<polygon fill="rgba(20,184,166,.22)" stroke="#0f766e" stroke-width="2" points="'+vals.map(function(v,i){return pt(i,R*v/100).join(",");}).join(" ")+'"/>';
  vals.forEach(function(v,i){if(v>0){var p=pt(i,R*v/100);o+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="3.5" fill="#0f766e"/><text x="'+(p[0]+5)+'" y="'+(p[1]-5)+'" font-size="10" fill="#0f766e">'+v+"</text>";}});
  o+='<text x="'+cx+'" y="'+(cy-R*0.5-2)+'" font-size="9" fill="#98a2b3" text-anchor="middle">50</text>';
  return o+"</svg>";
}
function pips(v){var h='<div class="pips">';for(var i=1;i<=3;i++)h+="<i"+(i<=v?' class="f"':"")+"></i>";return h+"</div>";}

/* ---------- 按补充剂 ---------- */
function viewSupp(){
  if(!S.supp) S.supp=D.supplements[0].id;
  var s=D.supplements.filter(function(x){return x.id===S.supp;})[0]||D.supplements[0];
  var h='<section class="card"><h2>选择补充剂</h2><div class="slist">';
  D.supplements.forEach(function(x){h+='<a class="chip'+(x.id===s.id?" on":"")+'" href="#supp/'+x.id+'">'+esc(x.zh)+"</a>";});
  h+="</div></section>";
  h+='<section class="card"><h2>'+esc(s.zh)+' <span class="muted small">'+esc(s.en)+"</span></h2>";
  h+='<div class="sgrid"><div class="radar">'+radar(s)+'<p class="small muted" style="text-align:center;margin:0">雷达图：各机制大类中的最高综合分（0–100）</p></div><div>';
  h+='<dl class="kv"><dt>常见形式</dt><dd>'+esc(s.forms)+"</dd><dt>主要机制</dt><dd>"+esc(LAB[s.primary])+"</dd><dt>常用剂量</dt><dd>"+esc(s.dose)+"</dd><dt>适用前提</dt><dd>"+esc(s.applic)+"</dd><dt>安全提示</dt><dd>"+
    s.safety.map(function(w){return '<span class="flag f-warn">⚠ '+esc(w)+"</span>";}).join("")+"</dd></dl>";
  if(s.suppRefs&&s.suppRefs.length) h+='<details><summary>补充文献（适用前提/安全性）</summary>'+refHtml(s.suppRefs)+"</details>";
  h+="</div></div>";
  h+="<h3>各机制评分</h3>";
  s.mechs.slice().sort(function(a,b){return b.score-a.score;}).forEach(function(m){
    h+='<div class="mrow"><div class="mhead"><span class="t"><a href="#mech/'+m.mech+'">'+esc(LAB[m.mech])+'</a> <span class="muted small">'+esc(GRP[m.mech])+"</span></span>"+
      '<span><b style="font-size:1.1rem">'+m.score+'</b><span class="muted small"> / 100</span></span></div>'+
      '<div class="bar"><i style="width:'+Math.max(m.score,2)+'%"></i></div>'+
      '<div class="sre"><div>强度 '+m.strength+pips(m.strength)+"</div><div>证据 "+m.evidence+"（"+EVL[m.evidence]+"）"+pips(m.evidence)+"</div><div>可达性 "+m.reach+pips(m.reach)+"</div></div>"+
      (s.primary===m.mech?'<span class="flag f-prim">主要机制</span>':"")+flags(m)+
      '<div class="small">'+esc(m.note)+"</div>"+(m.disputed?'<div class="small" style="color:var(--dis)">争议：'+esc(m.disputed)+"</div>":"")+refHtml(m.refs)+"</div>";});
  h+="</section>";
  app.innerHTML=h;
}

/* ---------- 总表 ---------- */
function viewTable(){
  var f=S.tf;
  var h='<section class="card"><div class="filters"><label>机制 <select id="fm"><option value="">全部</option>';
  D.taxonomy.forEach(function(g){h+='<optgroup label="'+esc(g.group)+'">';g.items.forEach(function(it){h+='<option value="'+it[0]+'"'+(f.mech===it[0]?" selected":"")+">"+esc(it[1])+"</option>";});h+="</optgroup>";});
  h+='</select></label><label>最低证据 <select id="fe">'+[0,1,2,3].map(function(v){return '<option value="'+v+'"'+(f.ev===v?" selected":"")+">≥ "+v+"（"+EVL[v]+"）</option>";}).join("")+
    '</select></label><input type="search" id="fq" placeholder="搜索名称" value="'+esc(f.q)+'"><span class="muted small" id="cnt"></span></div><div class="tw"><table><thead><tr>';
  var cols=[["zh","补充剂",""],["mech","机制",""],["strength","强度","num"],["evidence","证据","num"],["reach","可达","num"],["score","综合分","num"],["flags","标记",""]];
  cols.forEach(function(c){h+='<th data-k="'+c[0]+'" class="'+c[2]+'">'+c[1]+(S.sort.k===c[0]?' <span class="ar">'+(S.sort.d>0?"▲":"▼")+"</span>":"")+"</th>";});
  h+='</tr></thead><tbody id="tb"></tbody></table></div><p class="small muted">点击表头排序；点击补充剂名查看详情。</p></section>';
  app.innerHTML=h;
  function draw(){
    var q=f.q.trim().toLowerCase();
    var rs=ROWS.filter(function(r){return (!f.mech||r.mech===f.mech)&&r.evidence>=f.ev&&(!q||(r.s.zh+r.s.en).toLowerCase().indexOf(q)>=0);});
    var k=S.sort.k,d=S.sort.d;
    rs.sort(function(a,b){var x,y;
      if(k==="zh"){x=a.s.zh;y=b.s.zh;return d*x.localeCompare(y,"zh");}
      if(k==="mech"){return d*LAB[a.mech].localeCompare(LAB[b.mech],"zh");}
      if(k==="flags"){x=(a.disputed?1:0)+(a.needsSource?1:0);y=(b.disputed?1:0)+(b.needsSource?1:0);}
      else{x=a[k];y=b[k];}
      return d*(x-y)||b.score-a.score;});
    document.getElementById("tb").innerHTML=rs.map(function(r){
      return '<tr><td><a href="#supp/'+r.s.id+'">'+esc(r.s.zh)+"</a></td><td>"+esc(LAB[r.mech])+(r.s.primary===r.mech?' <span class="flag f-prim">主</span>':"")+'</td><td class="num">'+r.strength+'</td><td class="num">'+r.evidence+'</td><td class="num">'+r.reach+
        '</td><td class="num"><b>'+r.score+'</b><span class="minibar"><i style="width:'+r.score+'%"></i></span></td><td>'+flags(r)+"</td></tr>";}).join("");
    document.getElementById("cnt").textContent="共 "+rs.length+" 条";
  }
  draw();
  document.getElementById("fm").onchange=function(e){f.mech=e.target.value;draw();};
  document.getElementById("fe").onchange=function(e){f.ev=+e.target.value;draw();};
  document.getElementById("fq").oninput=function(e){f.q=e.target.value;draw();};
  [].forEach.call(app.querySelectorAll("th"),function(th){th.onclick=function(){var k=th.dataset.k;
    if(S.sort.k===k)S.sort.d=-S.sort.d;else{S.sort.k=k;S.sort.d=(k==="zh"||k==="mech")?1:-1;}viewTable();};});
}

/* ---------- 评分说明 ---------- */
function viewRubric(){
  var dis=ROWS.filter(function(r){return r.disputed;}).length,need=ROWS.filter(function(r){return r.needsSource;}).length;
  app.innerHTML='<section class="card rub"><h2>评分说明</h2>'+
  "<p>每一条记录是“一种补充剂 × 一种机制”。同一补充剂可有多条记录，各自独立评分。三个维度均为 0–3 分：</p>"+
  '<div class="tw"><table><thead><tr><th>分值</th><th>强度（作用是否直接、有效）</th><th>证据（该机制/相关效应的最高证据）</th><th>可达性（常规口服剂量能否在体内达到有效浓度）</th></tr></thead><tbody>'+
  "<tr><td>0</td><td>无作用或纯推测</td><td>无证据/推测</td><td>基本不可能达到</td></tr>"+
  "<tr><td>1</td><td>间接、微弱，或需远超生理的浓度</td><td>仅体外（细胞）研究</td><td>吸收很差，组织浓度远低于体外有效浓度</td></tr>"+
  "<tr><td>2</td><td>中等，作用明确但幅度有限</td><td>动物研究，或少量/小样本人体试验</td><td>部分可达（如仅血液、或仅在局部肠道）</td></tr>"+
  "<tr><td>3</td><td>直接、强效，为该机制的典型干预</td><td>多项人体 RCT 或荟萃分析且结论基本一致</td><td>常规剂量可稳定达到有效水平</td></tr>"+
  "</tbody></table></div>"+
  "<h3>综合分公式</h3><p><b>"+esc(D.formula)+"</b>。27 = 3×3×3 为满分。采用乘法是有意为之：任何一个维度为 0，综合分即为 0；体外很强但吸收不了的成分（如姜黄素）会被显著拉低。可能取值为 0、4、7、11、15、22、30、33、44、67、100 等离散档位，档位之间的细微差别不应过度解读。</p>"+
  "<h3>不计入评分的字段</h3><ul><li><b>适用前提</b>：功能医学式的“谁更可能获益”说明（如“主要对缺乏者有效”）。高分≠所有人都需要。</li>"+
  '<li><b>安全/相互作用</b>：以 <span class="flag f-warn">⚠ 警示标签</span> 单独展示，不影响分数。</li>'+
  '<li><b>争议标记</b>：<span class="flag f-dis">有争议</span> 表示分数本身在文献中存在明显分歧（当前样本 '+dis+' 条）；<span class="flag f-need">需补充来源</span> 表示该条记录缺少可核实的直接支持文献，证据分已相应下调（当前 '+need+" 条）。</li></ul>"+
  "<h3>注意事项</h3><ul>"+
  "<li>评分为基于所列文献与综述的主观判断，主要用于横向比较“机制有多靠谱”，并非疗效排名。</li>"+
  "<li>“证据”一栏评价的是该机制或与之直接相关的效应；人体结局获益不一定经由所列机制实现。</li>"+
  "<li>许多多酚类机制主要来自体外实验，且所用浓度远高于口服后血药浓度。</li>"+
  "<li>益生菌、β-葡聚糖、胶原等的效果高度依赖具体菌株/来源/制剂，评分代表“该类别中证据较好的产品”。</li>"+
  "<li>所有文献均通过 PubMed 核对 PMID 存在且标题与内容对应；文献列表并非系统综述。</li>"+
  "<li>这是 20 种补充剂的样本版本，机制分类中部分条目（如抗糖化、渗透调节）暂无收录。</li></ul>"+
  '<p class="warn-line" style="font-size:.95rem"><b>仅供个人参考，不构成医疗建议。</b>服用任何补充剂前，尤其在服药、妊娠/哺乳、有慢性病或即将手术时，请咨询医生或药师。</p></section>';
}

/* ---------- 路由 ---------- */
function route(){
  var h=(location.hash||"#mech").slice(1).split("/"),v=h[0];
  if(v==="supp"){if(h[1])S.supp=h[1];setTab("supp");viewSupp();}
  else if(v==="table"){setTab("table");viewTable();}
  else if(v==="rubric"){setTab("rubric");viewRubric();}
  else{if(h[1]&&LAB[h[1]])S.mech=h[1];setTab("mech");viewMech();}
  window.scrollTo(0,0);
}
fetch("data.json",{cache:"no-cache"}).then(function(r){return r.json();}).then(function(d){
  D=d;
  d.taxonomy.forEach(function(g){g.items.forEach(function(it){LAB[it[0]]=it[1];GRP[it[0]]=g.group;});});
  d.supplements.forEach(function(s){s.mechs.forEach(function(m){var r=Object.assign({},m);r.s=s;ROWS.push(r);});});
  document.getElementById("ver").textContent=d.version;document.getElementById("upd").textContent=d.updated;
  window.addEventListener("hashchange",route);route();
}).catch(function(e){app.innerHTML='<p class="card">数据加载失败：'+esc(e.message)+"</p>";});
})();
