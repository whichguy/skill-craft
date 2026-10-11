/* The stand-in for the artifact database in the static copy of a run (export.py writes it into run-review.html).
   window.__RR_DATA is {collection: [{id, data}]}, set by the script before this one. It is read only: a write resolves and
   changes nothing, and the page (which checks window.__RR_STATIC) says so. No network and no storage. */
(function(){
  var D=window.__RR_DATA||{};
  function copy(v){return JSON.parse(JSON.stringify(v));}
  function snap(c){return {docs:(D[c]||[]).map(function(x){return {id:x.id,data:function(){return copy(x.data);}};})};}
  function doc(path){
    var p=String(path).split("/"),f=(D[p[0]]||[]).filter(function(x){return x.id===p[1];})[0];
    return {get:function(){return Promise.resolve({exists:!!f,data:function(){return f?copy(f.data):null;}});},
            set:function(){return Promise.resolve();},update:function(){return Promise.resolve();}};
  }
  function Query(c){this.c=c;}
  Query.prototype.orderBy=function(){return this;};
  Query.prototype.onSnapshot=function(ok){var c=this.c;setTimeout(function(){ok(snap(c));},0);return function(){};};
  Query.prototype.doc=function(id){return doc(this.c+"/"+id);};
  Query.prototype.add=function(){return Promise.resolve({id:"static"});};
  var db={collection:function(c){return new Query(c);},doc:doc};
  window.claude={use:function(name){return Promise.resolve(name==="db"?db:null);}};
})();
