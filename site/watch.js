// Where to watch: the official rights holders for the visitor's country (watch.json, from UEFA's own broadcaster list, built by
// tools/build_watch.py). Country: the visitor's choice (saved in this browser), else the country the Worker stamps as
// <meta name="mu-country">, else Ireland. Friendlies are sold game by game, so they show nothing rather than a guess.
(function(){
  var KEY="mu:country", P=null;
  function load(){if(!P)P=fetch("/watch.json").then(function(r){return r.json()}); return P}
  function country(){var c=null; try{c=localStorage.getItem(KEY)}catch(e){} if(!c){var m=document.querySelector('meta[name="mu-country"]'); c=m&&m.content} return (c||"IE").toUpperCase()}
  function esc(t){return String(t).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
  function render(el,m){
    if(!el)return; if(!/nations league/i.test(m.comp||"")){el.hidden=true;return}
    load().then(function(J){
      var cc=country(), C=J.countries[cc], src=J.sources.nl, checked=new Date(J.checked+"T12:00:00Z").toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric",timeZone:"UTC"});
      var opts=Object.keys(J.countries).sort(function(a,b){return J.countries[a].n.localeCompare(J.countries[b].n)}).map(function(c){return '<option value="'+c+'"'+(c===cc?' selected':'')+'>'+esc(J.countries[c].n)+'</option>'}).join("")+'<option value="--"'+(C?'':' selected')+'>Somewhere else</option>';
      var who=C&&C.nl, note=C&&C.nlNote||"";
      el.hidden=false;
      el.innerHTML='<div class="wh"><b>Where to watch</b><label><span class="sr">Country</span><select>'+opts+'</select></label></div>'+
        (who&&who.length?'<p class="wl">'+who.map(function(b){return '<span class="bc">'+esc(b)+'</span>'}).join(" ")+'</p>'+(note?'<p class="sub wn">'+esc(note)+'</p>':''):'<p class="sub wn">Not in the list. See the official list below.</p>')+
        '<p class="sub ws">'+(who&&who.length>1?"Rights holders in "+esc(C.n)+". Which of them shows this game is set nearer the time. ":"")+'From <a href="'+src.u+'" target="_blank" rel="noopener">'+esc(src.t)+'</a>, checked '+checked+'.</p>';
      el.querySelector("select").addEventListener("change",function(e){try{localStorage.setItem(KEY,e.target.value)}catch(x){} render(el,m)});
    }).catch(function(){el.hidden=true});
  }
  window.MUWatch={render:render};
})();
