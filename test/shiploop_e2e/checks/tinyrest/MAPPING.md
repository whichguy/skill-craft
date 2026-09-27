# Oracle mapping

Each original test is covered by an oracle test of the same name. Suite parents cover the same group of behaviours as their children. Behaviour that the original reached by calling an internal function is checked through the CLI, HTTP responses, and the database file.

| Original file | Original test | Oracle test |
| --- | --- | --- |
| src/app.test.ts | createApp | .oracle/app.test.mjs › createApp |
| src/app.test.ts | GET / | .oracle/app.test.mjs › createApp > GET / |
| src/app.test.ts | GET /test.html | .oracle/app.test.mjs › createApp > GET /test.html |
| src/app.test.ts | GET /file.html | .oracle/app.test.mjs › createApp > GET /file.html |
| src/app.test.ts | OPTIONS /posts | .oracle/app.test.mjs › createApp > OPTIONS /posts |
| src/app.test.ts | GET /posts | .oracle/app.test.mjs › createApp > GET /posts |
| src/app.test.ts | GET /posts?_embed=comments | .oracle/app.test.mjs › createApp > GET /posts?_embed=comments |
| src/app.test.ts | GET /posts/1 | .oracle/app.test.mjs › createApp > GET /posts/1 |
| src/app.test.ts | GET /posts/-1 | .oracle/app.test.mjs › createApp > GET /posts/-1 |
| src/app.test.ts | GET /posts/1?_embed=comments | .oracle/app.test.mjs › createApp > GET /posts/1?_embed=comments |
| src/app.test.ts | GET /comments | .oracle/app.test.mjs › createApp > GET /comments |
| src/app.test.ts | GET /comments?postId=1 | .oracle/app.test.mjs › createApp > GET /comments?postId=1 |
| src/app.test.ts | GET /object | .oracle/app.test.mjs › createApp > GET /object |
| src/app.test.ts | GET /object/1 | .oracle/app.test.mjs › createApp > GET /object/1 |
| src/app.test.ts | GET /not-found | .oracle/app.test.mjs › createApp > GET /not-found |
| src/app.test.ts | POST /posts | .oracle/app.test.mjs › createApp > POST /posts |
| src/app.test.ts | POST /posts/1 | .oracle/app.test.mjs › createApp > POST /posts/1 |
| src/app.test.ts | POST /posts/-1 | .oracle/app.test.mjs › createApp > POST /posts/-1 |
| src/app.test.ts | POST /object | .oracle/app.test.mjs › createApp > POST /object |
| src/app.test.ts | POST /object/1 | .oracle/app.test.mjs › createApp > POST /object/1 |
| src/app.test.ts | POST /not-found | .oracle/app.test.mjs › createApp > POST /not-found |
| src/app.test.ts | PUT /posts | .oracle/app.test.mjs › createApp > PUT /posts |
| src/app.test.ts | PUT /posts/1 | .oracle/app.test.mjs › createApp > PUT /posts/1 |
| src/app.test.ts | PUT /object | .oracle/app.test.mjs › createApp > PUT /object |
| src/app.test.ts | PUT /object/1 | .oracle/app.test.mjs › createApp > PUT /object/1 |
| src/app.test.ts | PUT /posts/-1 | .oracle/app.test.mjs › createApp > PUT /posts/-1 |
| src/app.test.ts | PUT /not-found | .oracle/app.test.mjs › createApp > PUT /not-found |
| src/app.test.ts | PATCH /posts | .oracle/app.test.mjs › createApp > PATCH /posts |
| src/app.test.ts | PATCH /posts/1 | .oracle/app.test.mjs › createApp > PATCH /posts/1 |
| src/app.test.ts | PATCH /object | .oracle/app.test.mjs › createApp > PATCH /object |
| src/app.test.ts | PATCH /object/1 | .oracle/app.test.mjs › createApp > PATCH /object/1 |
| src/app.test.ts | PATCH /posts/-1 | .oracle/app.test.mjs › createApp > PATCH /posts/-1 |
| src/app.test.ts | PATCH /not-found | .oracle/app.test.mjs › createApp > PATCH /not-found |
| src/app.test.ts | DELETE /posts | .oracle/app.test.mjs › createApp > DELETE /posts |
| src/app.test.ts | DELETE /posts/1 | .oracle/app.test.mjs › createApp > DELETE /posts/1 |
| src/app.test.ts | DELETE /object | .oracle/app.test.mjs › createApp > DELETE /object |
| src/app.test.ts | DELETE /object/1 | .oracle/app.test.mjs › createApp > DELETE /object/1 |
| src/app.test.ts | DELETE /posts/-1 | .oracle/app.test.mjs › createApp > DELETE /posts/-1 |
| src/app.test.ts | DELETE /not-found | .oracle/app.test.mjs › createApp > DELETE /not-found |
| src/app.test.ts | GET /posts?_where=... uses JSON query | .oracle/app.test.mjs › createApp > GET /posts?_where=... uses JSON query |
| src/app.test.ts | GET /posts?_where=... overrides query params | .oracle/app.test.mjs › createApp > GET /posts?_where=... overrides query params |
| src/app.test.ts | POST /posts with array body returns 400 | .oracle/app.test.mjs › createApp > POST /posts with array body returns 400 |
| src/app.test.ts | PATCH /posts/1 with string body returns 400 | .oracle/app.test.mjs › createApp > PATCH /posts/1 with string body returns 400 |
| src/app.test.ts | PUT /posts/1 with null body returns 400 | .oracle/app.test.mjs › createApp > PUT /posts/1 with null body returns 400 |
| src/service.test.ts | findById | .oracle/service.test.mjs › findById |
| src/service.test.ts | find | .oracle/service.test.mjs › find |
| src/service.test.ts | {"where":{"title":{"eq":"b"}}} | .oracle/service.test.mjs › find > {"where":{"title":{"eq":"b"}}} |
| src/service.test.ts | {"where":{"author":{"name":{"eq":"bar"}}}} | .oracle/service.test.mjs › find > {"where":{"author":{"name":{"eq":"bar"}}}} |
| src/service.test.ts | {"where":{},"sort":"-views"} | .oracle/service.test.mjs › find > {"where":{},"sort":"-views"} |
| src/service.test.ts | {"where":{},"page":2,"perPage":2} | .oracle/service.test.mjs › find > {"where":{},"page":2,"perPage":2} |
| src/service.test.ts | create | .oracle/service.test.mjs › create |
| src/service.test.ts | update | .oracle/service.test.mjs › update |
| src/service.test.ts | patch | .oracle/service.test.mjs › patch |
| src/service.test.ts | updateById | .oracle/service.test.mjs › updateById |
| src/service.test.ts | patchById | .oracle/service.test.mjs › patchById |
| src/service.test.ts | destroy | .oracle/service.test.mjs › destroy |
| src/service.test.ts | nullifies foreign keys | .oracle/service.test.mjs › destroy > nullifies foreign keys |
| src/service.test.ts | deletes dependent resources | .oracle/service.test.mjs › destroy > deletes dependent resources |
| src/service.test.ts | ignores unknown resources | .oracle/service.test.mjs › destroy > ignores unknown resources |
| src/paginate.test.ts | paginate | .oracle/paginate.test.mjs › paginate |
| src/paginate.test.ts | page=1 perPage=2 items=5 -> [1,2] | .oracle/paginate.test.mjs › paginate > page=1 perPage=2 items=5 -> [1,2] |
| src/paginate.test.ts | page=2 perPage=2 items=5 -> [3,4] | .oracle/paginate.test.mjs › paginate > page=2 perPage=2 items=5 -> [3,4] |
| src/paginate.test.ts | page=9 perPage=2 items=5 -> clamp to last | .oracle/paginate.test.mjs › paginate > page=9 perPage=2 items=5 -> clamp to last |
| src/paginate.test.ts | page=0 perPage=2 items=3 -> clamp to first | .oracle/paginate.test.mjs › paginate > page=0 perPage=2 items=3 -> clamp to first |
| src/paginate.test.ts | items=[] page=1 perPage=2 -> stable empty pagination | .oracle/paginate.test.mjs › paginate > items=[] page=1 perPage=2 -> stable empty pagination |
| src/paginate.test.ts | perPage=0 -> clamp perPage to 1 | .oracle/paginate.test.mjs › paginate > perPage=0 -> clamp perPage to 1 |
| src/parse-where.test.ts | parseWhere | .oracle/parse-where.test.mjs › parseWhere |
| src/parse-where.test.ts | views:gt=100&title:eq=a | .oracle/parse-where.test.mjs › parseWhere > views:gt=100&title:eq=a |
| src/parse-where.test.ts | title=hello | .oracle/parse-where.test.mjs › parseWhere > title=hello |
| src/parse-where.test.ts | author.name:lt=c&author.id:ne=2 | .oracle/parse-where.test.mjs › parseWhere > author.name:lt=c&author.id:ne=2 |
| src/parse-where.test.ts | views:gt=100&views:lt=300 | .oracle/parse-where.test.mjs › parseWhere > views:gt=100&views:lt=300 |
| src/parse-where.test.ts | name:eq=Alice | .oracle/parse-where.test.mjs › parseWhere > name:eq=Alice |
| src/parse-where.test.ts | views:gt=100&published:eq=true&ratio:lt=0.5&deleted:eq=null | .oracle/parse-where.test.mjs › parseWhere > views:gt=100&published:eq=true&ratio:lt=0.5&deleted:eq=null |
| src/parse-where.test.ts | views:foo=100&title:eq=a | .oracle/parse-where.test.mjs › parseWhere > views:foo=100&title:eq=a |
| src/parse-where.test.ts | views:foo=100 | .oracle/parse-where.test.mjs › parseWhere > views:foo=100 |
| src/parse-where.test.ts | views_gt=100&title_eq=a | .oracle/parse-where.test.mjs › parseWhere > views_gt=100&title_eq=a |
| src/parse-where.test.ts | first_name_eq=Alice&author.first_name_ne=Bob | .oracle/parse-where.test.mjs › parseWhere > first_name_eq=Alice&author.first_name_ne=Bob |
| src/parse-where.test.ts | first_name=Alice | .oracle/parse-where.test.mjs › parseWhere > first_name=Alice |
| src/parse-where.test.ts | views_gt=100&views:lt=300 | .oracle/parse-where.test.mjs › parseWhere > views_gt=100&views:lt=300 |
| src/parse-where.test.ts | id:in=1,3 | .oracle/parse-where.test.mjs › parseWhere > id:in=1,3 |
| src/parse-where.test.ts | title_in=hello,world | .oracle/parse-where.test.mjs › parseWhere > title_in=hello,world |
| src/parse-where.test.ts | title:contains=ello | .oracle/parse-where.test.mjs › parseWhere > title:contains=ello |
| src/parse-where.test.ts | title:startsWith=hel | .oracle/parse-where.test.mjs › parseWhere > title:startsWith=hel |
| src/parse-where.test.ts | title:endsWith=rld | .oracle/parse-where.test.mjs › parseWhere > title:endsWith=rld |
| src/matches-where.test.ts | matchesWhere | .oracle/matches-where.test.mjs › matchesWhere |
| src/matches-where.test.ts | {"a":{"eq":10}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"eq":10}} |
| src/matches-where.test.ts | {"a":{"eq":11}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"eq":11}} |
| src/matches-where.test.ts | {"c":{"ne":"y"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"ne":"y"}} |
| src/matches-where.test.ts | {"c":{"ne":"x"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"ne":"x"}} |
| src/matches-where.test.ts | {"a":{"lt":11}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"lt":11}} |
| src/matches-where.test.ts | {"a":{"lt":10}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"lt":10}} |
| src/matches-where.test.ts | {"a":{"lte":10}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"lte":10}} |
| src/matches-where.test.ts | {"a":{"lte":9}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"lte":9}} |
| src/matches-where.test.ts | {"b":{"gt":19}} | .oracle/matches-where.test.mjs › matchesWhere > {"b":{"gt":19}} |
| src/matches-where.test.ts | {"b":{"gt":20}} | .oracle/matches-where.test.mjs › matchesWhere > {"b":{"gt":20}} |
| src/matches-where.test.ts | {"b":{"gte":20}} | .oracle/matches-where.test.mjs › matchesWhere > {"b":{"gte":20}} |
| src/matches-where.test.ts | {"b":{"gte":21}} | .oracle/matches-where.test.mjs › matchesWhere > {"b":{"gte":21}} |
| src/matches-where.test.ts | {"a":{"gt":0},"b":{"lt":30}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"gt":0},"b":{"lt":30}} |
| src/matches-where.test.ts | {"a":{"gt":10},"b":{"lt":30}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"gt":10},"b":{"lt":30}} |
| src/matches-where.test.ts | {"or":[{"a":{"lt":0}},{"b":{"gt":19}}]} | .oracle/matches-where.test.mjs › matchesWhere > {"or":[{"a":{"lt":0}},{"b":{"gt":19}}]} |
| src/matches-where.test.ts | {"or":[{"a":{"lt":0}},{"b":{"gt":20}}]} | .oracle/matches-where.test.mjs › matchesWhere > {"or":[{"a":{"lt":0}},{"b":{"gt":20}}]} |
| src/matches-where.test.ts | {"nested":{"a":{"eq":10}}} | .oracle/matches-where.test.mjs › matchesWhere > {"nested":{"a":{"eq":10}}} |
| src/matches-where.test.ts | {"nested":{"b":{"lt":20}}} | .oracle/matches-where.test.mjs › matchesWhere > {"nested":{"b":{"lt":20}}} |
| src/matches-where.test.ts | {"a":{"in":[10,11]}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"in":[10,11]}} |
| src/matches-where.test.ts | {"a":{"in":[1,2]}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"in":[1,2]}} |
| src/matches-where.test.ts | {"c":{"in":["x","y"]}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"in":["x","y"]}} |
| src/matches-where.test.ts | {"c":{"in":["y","z"]}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"in":["y","z"]}} |
| src/matches-where.test.ts | {"a":{"in":[10,11],"gt":9}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"in":[10,11],"gt":9}} |
| src/matches-where.test.ts | {"a":{"in":[10,11],"gt":10}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"in":[10,11],"gt":10}} |
| src/matches-where.test.ts | {"a":{"foo":10}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"foo":10}} |
| src/matches-where.test.ts | {"a":{"foo":10,"eq":10}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"foo":10,"eq":10}} |
| src/matches-where.test.ts | {"missing":{"foo":1}} | .oracle/matches-where.test.mjs › matchesWhere > {"missing":{"foo":1}} |
| src/matches-where.test.ts | {"c":{"contains":"x"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"contains":"x"}} |
| src/matches-where.test.ts | {"c":{"contains":"X"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"contains":"X"}} |
| src/matches-where.test.ts | {"c":{"contains":"z"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"contains":"z"}} |
| src/matches-where.test.ts | {"a":{"contains":"1"}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"contains":"1"}} |
| src/matches-where.test.ts | {"c":{"contains":1}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"contains":1}} |
| src/matches-where.test.ts | {"c":{"startsWith":"x"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"startsWith":"x"}} |
| src/matches-where.test.ts | {"c":{"startsWith":"X"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"startsWith":"X"}} |
| src/matches-where.test.ts | {"c":{"startsWith":"z"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"startsWith":"z"}} |
| src/matches-where.test.ts | {"a":{"startsWith":"1"}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"startsWith":"1"}} |
| src/matches-where.test.ts | {"c":{"startsWith":1}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"startsWith":1}} |
| src/matches-where.test.ts | {"c":{"endsWith":"x"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"endsWith":"x"}} |
| src/matches-where.test.ts | {"c":{"endsWith":"X"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"endsWith":"X"}} |
| src/matches-where.test.ts | {"c":{"endsWith":"z"}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"endsWith":"z"}} |
| src/matches-where.test.ts | {"a":{"endsWith":"1"}} | .oracle/matches-where.test.mjs › matchesWhere > {"a":{"endsWith":"1"}} |
| src/matches-where.test.ts | {"c":{"endsWith":1}} | .oracle/matches-where.test.mjs › matchesWhere > {"c":{"endsWith":1}} |
| src/adapters/normalized-adapter.test.ts | read removes $schema and normalizes ids | .oracle/normalized-adapter.test.mjs › read removes $schema and normalizes ids |
| src/adapters/normalized-adapter.test.ts | write always overwrites $schema | .oracle/normalized-adapter.test.mjs › write always overwrites $schema |
