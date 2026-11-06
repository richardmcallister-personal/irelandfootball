// Language layer. English is the page as written. For Irish, the Worker's head snippet sets window.MU_LANG and hides the body; this file
// loads /i18n/ga.json, swaps text in place as pages render (nothing in the pages themselves changes) and adds the picker to the header.
// Names of people, clubs and grounds, and data from outside sources, stay as they are. Words go in site/i18n/ga.json.
(function(){
  var LANG=window.MU_LANG||"en", D=document;
  function picker(){var h=D.querySelector("header.mu"); if(!h||h.querySelector(".langpick"))return;
    var n=D.createElement("nav"); n.className="langpick"; n.setAttribute("aria-label",LANG==="ga"?"Teanga":"Language"); n.setAttribute("data-noi18n","");
    [["en","English"],["ga","Gaeilge"]].forEach(function(x){var a=D.createElement("a"); a.textContent=x[1]; a.lang=x[0]; var u=new URL(location.href); u.searchParams.set("lang",x[0]); a.href=u.pathname+u.search+u.hash; if(x[0]===LANG)a.setAttribute("aria-current","true"); n.appendChild(a)});
    h.appendChild(n)}
  function ready(f){if(D.readyState==="loading")D.addEventListener("DOMContentLoaded",f); else f()}
  ready(picker);
  if(LANG!=="ga")return;

  var X={}, C={}, P=[], B={}, done=new WeakMap(), blockDone=new WeakSet();
  var DAYS={Mon:"Luan",Tue:"Máirt",Wed:"Céad",Thu:"Déar",Fri:"Aoine",Sat:"Sath",Sun:"Domh",Monday:"Dé Luain",Tuesday:"Dé Máirt",Wednesday:"Dé Céadaoin",Thursday:"Déardaoin",Friday:"Dé hAoine",Saturday:"Dé Sathairn",Sunday:"Dé Domhnaigh"};
  var MON={Jan:"Ean",Feb:"Feabh",Mar:"Márta",Apr:"Aib",May:"Beal",Jun:"Meith",Jul:"Iúil",Aug:"Lún",Sep:"MFómh",Sept:"MFómh",Oct:"DFómh",Nov:"Samh",Dec:"Noll",January:"Eanáir",February:"Feabhra",March:"Márta",April:"Aibreán",June:"Meitheamh",July:"Iúil",August:"Lúnasa",September:"Meán Fómhair",October:"Deireadh Fómhair",November:"Samhain",December:"Nollaig"};
  var DATE=/^(?:([A-Z][a-z]+),? )?(\d{1,2}) ([A-Z][a-z]+)(?: (\d{4}))?((?: v .+)?)$/;
  var LETTERS={W:"B",D:"C",L:"Ca",P:"I",F:"Ar",A:"In"};
  function cap(s){return s.charAt(0).toUpperCase()+s.slice(1)}
  function date(s){var m=s.match(DATE); if(!m||!MON[m[3]]||(m[1]&&!DAYS[m[1]]))return null; return (m[1]?DAYS[m[1]]+", ":"")+m[2]+" "+MON[m[3]]+(m[4]?" "+m[4]:"")+(m[5]?" v "+tr(m[5].slice(3),1):"")}
  // tr: English to Irish, or the text unchanged. mid=1 keeps a country in lower case for use inside a phrase.
  function tr(s,mid){
    if(C[s]!=null)return mid?C[s]:cap(C[s]);
    if(X[s]!=null)return X[s];
    var d=date(s); if(d)return d;
    if(s.indexOf(" · ")>0){var parts=s.split(" · "), out=parts.map(function(p){return tr(p)}); return out.join(" · ")}
    var v=s.match(/^(.+) v (.+)$/); if(v){var rt=tr(v[2],1); if(rt!==v[2])return tr(v[1])+" v "+rt}
    for(var i=0;i<P.length;i++){var m=s.match(P[i][0]); if(m)return P[i][1].replace(/\{([Tt])(\d)\}/g,function(_,k,n){return tr(m[+n],k==="t"?1:0)}).replace(/\$(\d)/g,function(_,n){return m[+n]||""}).replace(/\s+$/,"")}
    return s}
  function node(n){var p=n.parentElement; if(!p||/^(SCRIPT|STYLE|TEXTAREA|NOSCRIPT|MARK)$/.test(p.tagName)||p.closest("[data-noi18n]"))return;
    var v=n.nodeValue; if(done.get(n)===v||!/[A-Za-z]/.test(v))return;
    var t=v.trim(), r;
    if(p.tagName==="OPTION"&&/^[A-Z]{2}$/.test(p.value)&&NAMES){try{r=NAMES.of(p.value)}catch(e){}}
    if(!r&&t.length<3&&LETTERS[t]&&(p.tagName==="TH"||/\b(rw|rd|rl)\b/.test(p.className)))r=LETTERS[t];
    if(!r)r=tr(t);
    var nv=r===t?v:v.replace(t,function(){return r}); done.set(n,nv); if(nv!==v)n.nodeValue=nv}
  // A paragraph with links inside: swapped whole, keeping its child elements at {0}, {1}…
  function block(el){if(blockDone.has(el))return; var key=el.textContent.replace(/\s+/g," ").trim(), tpl=B[key]; if(!tpl)return; blockDone.add(el);
    var kids=[].slice.call(el.children), frag=D.createDocumentFragment(); tpl.split(/(\{\d+\})/).forEach(function(b){var m=b.match(/^\{(\d+)\}$/); if(m&&kids[+m[1]])frag.appendChild(kids[+m[1]]); else if(!m&&b)frag.appendChild(D.createTextNode(b))});
    el.textContent=""; el.appendChild(frag); var w=D.createTreeWalker(el,NodeFilter.SHOW_TEXT),n; while((n=w.nextNode()))done.set(n,n.nodeValue);
    [].forEach.call(el.children,function(c){walk(c)})}
  var ATT=["placeholder","title","aria-label","alt"];
  function attrs(e){for(var i=0;i<ATT.length;i++){var a=ATT[i],v=e.getAttribute&&e.getAttribute(a); if(v&&e.closest&&!e.closest("[data-noi18n]")){var r=tr(v.trim()); if(r!==v.trim())e.setAttribute(a,r)}}}
  function walk(root){
    if(root.nodeType===3){node(root);return} if(root.nodeType!==1)return;
    [].forEach.call(root.matches&&root.matches("p,.big")?[root]:[],block);
    if(root.querySelectorAll){[].forEach.call(root.querySelectorAll("p,.big"),block)}
    attrs(root); if(root.querySelectorAll)[].forEach.call(root.querySelectorAll("[placeholder],[title],[aria-label],[alt]"),attrs);
    var w=D.createTreeWalker(root,NodeFilter.SHOW_TEXT),n; while((n=w.nextNode()))node(n)}
  var NAMES=null; try{NAMES=new Intl.DisplayNames(["ga"],{type:"region"})}catch(e){}
  function show(){D.documentElement.classList.remove("i18n-wait")}
  var failsafe=setTimeout(show,2500);
  fetch("/i18n/ga.json").then(function(r){return r.json()}).then(function(J){
    X=J.exact; C=J.countries; B=J.blocks; P=J.patterns.map(function(p){return [new RegExp(p[0]),p[1]]});
    new MutationObserver(function(L){L.forEach(function(m){
      if(m.type==="characterData")node(m.target);
      else if(m.type==="attributes"){if(m.target.getAttribute(m.attributeName)&&ATT.indexOf(m.attributeName)>=0)attrs(m.target)}
      else [].forEach.call(m.addedNodes,walk)})}).observe(D.documentElement,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:ATT});
    ready(function(){walk(D.documentElement); clearTimeout(failsafe); show()});
  }).catch(show);
})();
