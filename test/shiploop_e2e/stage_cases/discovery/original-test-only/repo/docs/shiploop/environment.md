# Environment

Seeded by the E2E harness from the case's own checks; discovery did not run.

## Commands

```sh
npm test
node -e "const {withService,ticketBody}=require('./test/helpers');const a=require('assert');withService({},async(api)=>{const t=(await api.post('/tickets',ticketBody())).body;a.strictEqual(t.assignee,null);const p=await api.put('/tickets/'+t.id+'/assignee',{assignee:'check.agent'});a.ok(p.status>=200&&p.status<300,'assign '+p.status);a.strictEqual((await api.get('/tickets/'+t.id)).body.assignee,'check.agent');a.strictEqual((await api.put('/tickets/'+t.id+'/assignee',{assignee:'x'.repeat(65)})).status,400);a.strictEqual((await api.get('/tickets/'+t.id)).body.assignee,'check.agent');const u=await api.put('/tickets/'+t.id+'/assignee',{assignee:null});a.ok(u.status>=200&&u.status<300,'unassign '+u.status);a.strictEqual((await api.get('/tickets/'+t.id)).body.assignee,null)}).then(()=>process.exit(0),e=>{console.error(e);process.exit(1)})"
```
