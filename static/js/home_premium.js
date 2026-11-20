(function(){
  var els=document.querySelectorAll('.p-reveal');
  if(!('IntersectionObserver' in window)){els.forEach(function(e){e.classList.add('in')});return;}
  var io=new IntersectionObserver(function(en){en.forEach(function(x){if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target);}})},{threshold:.12,rootMargin:'0px 0px -40px 0px'});
  els.forEach(function(e){io.observe(e)});
})();
