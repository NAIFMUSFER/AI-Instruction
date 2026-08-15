/* ============================================================
   public/app/boot/a11y-baseline.js — أساس الوصولية — كلاسيكي عمداً كي لا يعتمد على تحميل Three.js
   مُستخرَج من public/index.html بـ tools/frontend_shell.js (F-09/F-11).
   كلاسيكي عمداً: يعمل قبل الوحدات ولا يعتمد على تحميلها.
   ============================================================ */
(function(){
  try{
    /* مساحة العمل المولَّدة تحمل تسميات إنجليزية داخل مستند lang="ar":
       نُعلن لغتها بدل أن نُحرّر كتلة مولَّدة. */
    var EN=['acsWorkspace','wsModal','wsToasts','rvPanel','rvView','bxPanel',
            'dcPanel','pqPanel'];
    for(var i=0;i<EN.length;i++){
      var e=document.getElementById(EN[i]);
      if(e&&!e.getAttribute('lang')) e.setAttribute('lang','en');
    }
    /* حالة aria تتبع أصناف CSS التي تبدّلها المعالِجات القديمة. */
    var sync=function(){
      var t=document.querySelectorAll('.tabs button[role=tab]'),j;
      for(j=0;j<t.length;j++)
        t[j].setAttribute('aria-selected',
          t[j].className.indexOf('active')>=0?'true':'false');
      var c=document.querySelectorAll('#camBar button[aria-pressed]');
      for(j=0;j<c.length;j++)
        c[j].setAttribute('aria-pressed',
          (' '+c[j].className+' ').indexOf(' on ')>=0?'true':'false');
      var p=document.getElementById('panelToggle'),l=document.getElementById('left');
      if(p&&l) p.setAttribute('aria-expanded',
        (' '+l.className+' ').indexOf(' open ')>=0?'true':'false');
    };
    sync();
    if(typeof MutationObserver!=='undefined'){
      var mo=new MutationObserver(sync), k;
      var w=document.querySelectorAll('.tabs button[role=tab],#camBar button[aria-pressed]');
      for(k=0;k<w.length;k++) mo.observe(w[k],{attributes:true,attributeFilter:['class']});
      var lp=document.getElementById('left');
      if(lp) mo.observe(lp,{attributes:true,attributeFilter:['class']});
      var nm=document.getElementById('noteModal');
      if(nm) mo.observe(nm,{attributes:true,attributeFilter:['class']});
    }
    /* الحوارات: Escape يغلق، وTab محبوس داخل الحوار، والتركيز يعود لفاتحه.
       مكتوب هنا بلا وحدات حتى يبقى صالحاً في المسار المتدهور. */
    var FOCUSABLE='a[href],button:not([disabled]),input:not([disabled]),'
      +'select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
    function trap(el,ev){
      var items=[],all=el.querySelectorAll(FOCUSABLE),i;
      for(i=0;i<all.length;i++) if(all[i].offsetParent!==null) items.push(all[i]);
      if(!items.length) return;
      var f=items[0], l=items[items.length-1];
      if(ev.shiftKey&&document.activeElement===f){ ev.preventDefault(); l.focus(); }
      else if(!ev.shiftKey&&document.activeElement===l){ ev.preventDefault(); f.focus(); }
    }
    function dialog(el, close){
      if(!el) return;
      el.setAttribute('data-acs-dialog','1');
      el.addEventListener('keydown',function(ev){
        if(ev.key==='Escape'){ ev.stopPropagation(); close(); }
        else if(ev.key==='Tab'){ trap(el,ev); }
      });
    }
    var nmEl=document.getElementById('noteModal'), nmBack=null;
    if(nmEl){
      var wasOn=(' '+nmEl.className+' ').indexOf(' on ')>=0;
      dialog(nmEl,function(){ nmEl.className=nmEl.className.replace(/\bon\b/g,''); });
      if(typeof MutationObserver!=='undefined'){
        new MutationObserver(function(){
          var on=(' '+nmEl.className+' ').indexOf(' on ')>=0;
          if(on===wasOn) return;
          wasOn=on;
          nmEl.setAttribute('aria-hidden', on?'false':'true');
          if(on){ nmBack=document.activeElement; }
          else if(nmBack&&nmBack.focus){ var r=nmBack; nmBack=null;
            try{ r.focus(); }catch(e){} }
        }).observe(nmEl,{attributes:true,attributeFilter:['class']});
      }
    }
    var alt=document.getElementById('acsA11yAlt'), altBack=null;
    function altClose(){
      if(!alt) return;
      alt.className=alt.className.replace(/\bon\b/g,'');
      alt.setAttribute('aria-hidden','true');
      if(altBack&&altBack.focus){ var r=altBack; altBack=null; try{ r.focus(); }catch(e){} }
    }
    function altOpen(){
      if(!alt) return;
      altBack=document.activeElement;
      alt.className=alt.className+' on';
      alt.removeAttribute('aria-hidden');
      var c=document.getElementById('acsA11yClose'); if(c) c.focus();
    }
    dialog(alt, altClose);
    var ob=document.getElementById('acsA11yOpen');
    if(ob) ob.addEventListener('click', altOpen);
    var cb=document.getElementById('acsA11yClose');
    if(cb) cb.addEventListener('click', altClose);
    window.ACS=window.ACS||{};
    window.ACS.a11yBaselineReady=true;
  }catch(e){ /* الأساس تحسين لا يجوز أن يكسر الصفحة */ }
})();

