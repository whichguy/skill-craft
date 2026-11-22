# annotations: run -> list of dict(file,line,n,drop,dnote,uses[(title,ev,quote)])
# drop: yes|no|unclear ; ev: yes|no
ANN = {}
IGN = {}
def A(run, file, line, drop, dnote, uses, n=0, pos=None):
    ANN.setdefault(run, []).append(dict(file=file, line=line, n=n, drop=drop, dnote=dnote, uses=uses, pos=pos))
def I(run, file, line):
    IGN.setdefault(run, []).append((file, line))

# ---- pilot ----
r='g-ratchet-sol-high'
A(r,'startup.cjs',28,'no','repoTests helper passes env {...process.env, ...env}; harness h.npm adds only npm_config_*; nothing removed',
  [('C-258','yes',"assert.match(result.output, /(?:# tests|ℹ tests) [1-9]\\d*|Subtest:/)"),
   ('C-259','yes',"assert.equal(result.code, 0, result.output); assert.match(result.output, /(?:# tests|ℹ tests) [1-9]\\d*|Subtest:/)"),
   ('C-260','no',"result of repoTests is not inspected; only operator data directory compared"),
   ('U-29','no',"assert.equal(result.code, 0, result.output); assert.match(result.output, /node\\s+[^\\n]*--test\\b/) (command-echo line, not a count)")])

r='p1-stand-in-rules'
A(r,'check-npm-discovery.cjs',21,'no','spawnSync has no env option (standalone script; acceptance.json runs it as plain `node acceptance/check-npm-discovery.cjs C-61|C-62`, not under node --test)',
  [('C-61','yes',"assert.ok(cases.some(test => test.file === 'test/meter.test.js' && test.name === name), `npm test did not run ...`) (cases parsed from a custom reporter's `case ` lines)"),
   ('C-62','yes',"assert.ok(cases.some(test => test.file === file && test.name.startsWith(`C-${id} `)), `npm test did not run the C-${id} coverage case ...`)")])

r='p1-ticket-assignment'
dn="support.cjs environment(): {...process.env} minus PORT,DATA_FILE,NOTIFY_FILE,MAX_BODY_BYTES,WORKER_INTERVAL_MS,LOG_REQUESTS,NODE_OPTIONS (not NODE_TEST_CONTEXT); override {NODE_OPTIONS:'--test-reporter=tap'}"
U74=[('C-74','yes',"assert.ok(newNames.length && oldNames.length, 'Expected named TAP cases in both suites'); assert.deepEqual([...]filter(name => !actual.has(name)), [], 'Missing cases in npm test output')")]
A(r,'compatibility.cjs',79,'no',dn,U74,n=0)
A(r,'compatibility.cjs',79,'no',dn,U74,n=1)
A(r,'compatibility.cjs',80,'no',dn,U74)
A(r,'compatibility.cjs',100,'no',dn,[('C-76','yes',"assert.ok(tapNames(result.stdout).length > 0, 'No original tests ran'); assert.doesNotMatch(result.stdout, /^not ok /m)")])
A(r,'delivery.cjs',289,'no',dn.replace(",NODE_OPTIONS","").replace("; override {NODE_OPTIONS:'--test-reporter=tap'}","; no env override"),
  [('C-154','yes',"assert.match(ceiling.stdout, /^\\s*ok \\d+ - doubles from one second and stops at five minutes$/m)")])

r='p1-ticket-due-times'
dn="harness.cjs cleanEnv(): {...process.env} minus PORT,DATA_FILE,NOTIFY_FILE,RESPONSE_HOURS,WORKER_INTERVAL_MS,MAX_BODY_BYTES,LOG_REQUESTS,DUE_TIMES,DUE_HOURS_*,NODE_OPTIONS,ACCEPTANCE_* (not NODE_TEST_CONTEXT)"
A(r,'cli-release.cjs',251,'no',dn,[('C-216','no',"exited(result, 0); assert.doesNotMatch(result.stdout, /^not ok\\b/m)")])
A(r,'cli-release.cjs',274,'no',dn,[('C-217','yes',"const passing = passingFiles(result.stdout); for (const file of suites) assert.ok(passing.has(file), 'no passing test case in ' + file)")])
A(r,'cli-release.cjs',283,'no',dn+"; override env {NODE_OPTIONS: reporter}",[('C-218','yes',"assert.ok(baselineTestFiles().some(... passing.has(file)), 'npm test did not report passing baseline cases'); for (const file of suites) assert.ok(passing.has(file), ...)")])
A(r,'http.cjs',86,'no',dn,[('C-86','no',"exited(await run(t, 'npm', ['test'], ...), 0)")])

r='p1e-stand-in-rules'
A(r,'package.cases.cjs',21,'yes',"runPackageTests(): env = {...process.env, NODE_OPTIONS...}; `delete env.NODE_TEST_CONTEXT;` before spawnSync",
  [('C-60','yes',"assert.match(output, /^TAP version \\d+$/m) (assertNodeRunner)"),
   ('C-61','yes',"assert.ok(calls.length, 'npm test never exercised parseOrders') (probe observations from the child)"),
   ('C-62','yes',"assert.ok(calls.length, 'npm test never exercised total')"),
   ('C-63','yes',"assertExistingMeterTests: assert.match(output, /^ok \\d+ - meter counts ticks and resets$/m); assertOrderTestsRan"),
   ('U-8','yes',"assertExistingMeterTests(stockRun.output); assertOrderTestsRan(observedRun.output)")])
I(r,'package.cases.cjs',0)

for r in ['p1e2-stand-in-rules','p2-orders-cross-field','p2-orders-limit-never-trips','p2-orders-one-rule-missing','p2-orders-tested-only']:
    A(r,'workflow.cjs',26,'yes',"npmTest(): nestedEnvironment = {...process.env,...}; `delete nestedEnvironment.NODE_TEST_CONTEXT;` before run('npm',['test'])",
      [('C-66','yes',"assert.match(result.stdout, /ratchet: node:test ran a test/, result.stderr) (custom reporter line)"),
       ('C-67','yes',"observeNpmTests: evidence set from trace written by an observer required in the child; assert.deepStrictEqual(expected.filter(name => !evidence.has(name)), [], ...)"),
       ('C-68','yes',"assertSuccess(npmTest()); assertBothSuites(observeNpmTests(t)): assert.ok(evidence.has('meter'), 'npm test did not exercise the meter directly')"),
       ('U-12','yes',"assertSuccess(npmTest()); assertBothSuites(observeNpmTests(t))")])
    I(r,'npm-observer.cjs',80)

DN_TA="support.cjs env(): {...process.env}, then `delete result.NODE_TEST_CONTEXT;` (default env of run() as well as explicit env())"
for r in ['p1e2-ticket-assignment','p2-assign-filter-after-page']:
    A(r,'delivery.cases.cjs',248,'yes',DN_TA,[('C-72','yes',"assert.match(output(cap), /(?:ok \\d+ -|✔) doubles from one second and stops at five minutes/)")])
    A(r,'regression.cases.cjs',205,'yes',DN_TA+"; npmTest(): run('npm',['test'],{env: env()})",
      [('C-183','no',"assert.doesNotMatch(process.stdout + process.stderr, /MODULE_NOT_FOUND|.../) only"),
       ('C-184','yes',"assert.ok(passingTests(full.stdout).length >= 117, 'the original suite did not run in full')"),
       ('C-185','yes',"discoveredCoverage(full.stdout + full.stderr) -> discoveredAssignment: assert.ok(tests.some(name => /assign/i.test(name) && passingTests(full)...), 'npm test did not discover the assignment coverage')"),
       ('U-16','yes',"assert.ok(passingTests(full).length > 117, 'no new tests ran alongside the baseline')")])
    A(r,'regression.cases.cjs',225,'yes',DN_TA+"; run() default env: env(); discoveredAssignment() helper",
      [('C-185','yes',"assert.ok(tests.length > 0, 'no new node:test cases executed')"),
       ('U-16','yes',"assert.ok(tests.length > 0, 'no new node:test cases executed')")])
r='p2-assign-filter-or'
A(r,'delivery.cases.cjs',248,'yes',DN_TA,[('C-72','yes',"assert.match(output(cap), /(?:ok \\d+ -|✔) doubles from one second and stops at five minutes/)")])
A(r,'regression.cases.cjs',215,'yes',DN_TA+"; npmTest(): run('npm',['test'],{env: env()})",
  [('C-183','no',"assert.doesNotMatch(process.stdout + process.stderr, /MODULE_NOT_FOUND|.../) only"),
   ('C-184','yes',"originalSuitePassed(output(npmTest())) -> assertDiscovered: assert.ok(cases.length > 0, 'no node:test cases executed in ...')"),
   ('C-185','yes',"discoveredCoverage(full); assertDiscovered(full, originalTestFiles)"),
   ('U-16','yes',"originalSuitePassed(full); discoveredAssignment(full)")])
A(r,'regression.cases.cjs',236,'yes',DN_TA+"; run() default env: env(); assertDiscovered() helper",
  [('C-184','yes',"assert.ok(cases.length > 0, 'no node:test cases executed in ' + files.join(', '))"),
   ('C-185','yes',"assert.ok(cases.length > 0, ...); assert.deepEqual(missing, [], 'tests missing from npm test: ...')"),
   ('U-16','yes',"assert.ok(cases.length > 0, ...)")])

DN_DT="support.cjs environment(): {...process.env} minus PORT,DATA_FILE,NOTIFY_FILE,WORKER_INTERVAL_MS,MAX_BODY_BYTES,LOG_REQUESTS,DUE_TIMES,DUE_HOURS_*,RESPONSE_HOURS,NODE_OPTIONS (not NODE_TEST_CONTEXT); command() always passes env: environment(env)"
for r in ['p1e2-ticket-due-times','p2-due-priority-moves-due']:
    A(r,'operator.cjs',287,'no',DN_DT,[('C-232','yes',"const names = new Set(executedNames(result.stdout)); assert(names.size, result.stderr || result.stdout)")])
    A(r,'operator.cjs',298,'no',DN_DT,[('C-232','no',"for (const name of executedNames(baseline.stdout)) assert(names.has(name), ...) (subset check, vacuous on empty output; the sibling npm child in the same test has assert(names.size))")])
    A(r,'operator.cjs',303,'no',DN_DT,[('C-232','yes',"assert(cases.length, `no runnable tests in ${file}`)")])
    A(r,'operator.cjs',313,'no',DN_DT,[('C-233','no',"assert.equal(result.status, 0, failures.join('\\n') + ...) only")])
    A(r,'use-cases.cjs',427,'no',DN_DT,[('U-15','yes',"const tests = (output) => Number(/^# tests (\\d+)$/m.exec(output)?.[1]); assert(tests(result.stdout) > tests(original.stdout), 'npm test did not discover additional tests')")])
    A(r,'use-cases.cjs',429,'no',DN_DT,[('U-15','yes',"assert(tests(result.stdout) > tests(original.stdout), 'npm test did not discover additional tests')")])
r='p2-due-version-two'
A(r,'operator.cjs',313,'no',DN_DT,[('C-233','no',"assert.equal(result.status, 0, failures.join('\\n') + ...) only")])
UU=lambda q:[('C-232',q[0],q[1]),('U-15',q[0],q[1])]
A(r,'suite.cjs',29,'no',DN_DT+"; assertNpmDiscovery() in suite.cjs",UU(('yes',"const names = new Set(executedNames(result.stdout)); assert(names.size, result.stderr || result.stdout)")))
A(r,'suite.cjs',34,'no',DN_DT,UU(('yes',"assert(originalNames.length, original.stderr || original.stdout)")))
A(r,'suite.cjs',40,'no',DN_DT,UU(('yes',"assert(cases.length, `no runnable tests in ${file}`)")))

r='p3-node-chess-engine-sol-high'
DN_CH="fixtures.cjs subprocessOptions(): env = {...process.env, ...options.env}; `delete env.NODE_TEST_CONTEXT;` (used by command() and the spawnSync call)"
A(r,'suite.cjs',42,'yes',DN_CH+"; npmTest() helper",
  [('C-2','no',"npmTest({ cwd, env }) result not inspected (execFileSync throws on non-zero exit)"),
   ('C-89','no',"assert.doesNotThrow(() => npmTest())"),
   ('U-13','no',"npmTest() result not inspected (the same test then calls auditCoverage, which has evidence checks on separate runs)")])
A(r,'suite.cjs',86,'yes',DN_CH+"; productTestEvents() helper",
  [('C-80','yes',"assert.ok(productTestEvents().length > 0, 'no chess rule tests ran under test/')")]+
  [(i,'yes',"auditCoverage: assert.ok(passed.size > 0, 'the built-in runner reported no passing chess tests under test/'); assert.ok(caughtRegression, ...)") for i in ['C-81','C-82','C-83','C-84','C-85','C-86','C-87','C-88']]+
  [('U-13','yes',"auditCoverage([...]): assert.ok(passed.size > 0, 'the built-in runner reported no passing chess tests under test/')")])
I(r,'run.cjs',14)

r='p3-shared-expenses-sol-high'
A(r,'suite.cases.cjs',24,'yes',"runBuiltInSuite(): env = {...process.env}; `delete env.NODE_TEST_CONTEXT;` then launch(['--test',...], { env })",
  [('C-83','yes',"assert.ok(events.some(entry => entry.type === 'test:pass' && Number.isInteger(entry.line)), 'Expected a registered node:test test...')"),
   ('C-84','yes',"assert.ok(events.length > 0, 'Expected discovered test files')"),
   ('C-85','yes',"assert.ok(testCount(output) > 0, output)"),
   ('C-86','yes',"trace of HTTP activity from observer in the child: assert.deepEqual(missing, []) over publicCoverage(trace) (requires child-run traffic; no count/summary)"),
   ('U-19','yes',"assert.ok(testCount(output) > 0, output); assert.ok(events.some(entry => entry.type === 'test:pass' && ...))")],
  pos=r"launch\(args, \{ env \}\)")
I(r,'suite.cases.cjs',50)

r='p3-ticket-assignment-sol-high'
DN_SH="support.cjs npmEnv(): {...env(settings), npm_config_*}; env() = {...process.env} minus ENV_KEYS which include 'NODE_TEST_CONTEXT'"
A(r,'compatibility.cjs',49,'yes',DN_SH+"; npmTests() helper",
  [('C-196','yes',"assert.match(result.stdout, /# tests [1-9]\\d*\\b/)"),
   ('C-198','yes',"observedTests(): assert.deepEqual(omitted, [], 'New assignment cases missing from npm test execution') over executed `ok N -` lines"),
   ('C-199','yes',"assert.match(output, /# tests [1-9]\\d*\\b/)"),
   ('U-25','yes',"observedTests(result, ...); assert.match(passed(result), /# fail 0\\b/)")])
A(r,'effects.cjs',330,'yes',DN_SH,[('C-80','yes',"assert.match(passed(memory), /^\\s*ok \\d+ - without a file, deliveries are kept in memory$/m)")])
A(r,'effects.cjs',389,'yes',DN_SH,[('C-87','yes',"assert.match(output, /^\\s*ok \\d+ - doubles from one second and stops at five minutes$/m)")])

r='p3-ticket-assignment-sol-medium'
DN_SM="harness.cjs: spawn(..., { env: { ...env, ...settings } }) where env = { ...process.env, PORT:'0', DATA_FILE:'', NOTIFY_FILE:'', WORKER_INTERVAL_MS:'0', MAX_BODY_BYTES:'', LOG_REQUESTS:'' } (NODE_TEST_CONTEXT kept)"
A(r,'operations.cjs',29,'no',DN_SM+"; npmTest() helper",
  [('C-124','no',"await npmTest(copy); then assert.ok(!fs.existsSync(.../node_modules)) (output() asserts exit status 0 only)"),
   ('C-125','no',"fallback branch (when no Node 22): await npmTest() (exit status only)"),
   ('C-160','yes',"assert.match(tap, /^(?:#|ℹ) fail 0$/m); assert.match(tap, /^(?:#|ℹ) pass [1-9]\\d*$/m)"),
   ('C-161','yes',"proveNewTestsDiscovered(tap): assert.ok(tap.includes(name), 'expected npm test to discover ...'); assert.match(tap, /^(?:#|ℹ) fail 0$/m)"),
   ('U-16','yes',"ops.proveNewTestsDiscovered(await ops.npmTest())")])
A(r,'operations.cjs',205,'no',DN_SM,[('C-125','no',"if (runtime) output(await commandAsync(['--test'], { executable: runtime })) (exit status only; only when a Node 22 binary exists)")])

r='p3-ticket-due-times-sol-high'
A(r,'events.cjs',289,'yes',"ctx.run(..., { NODE_TEST_CONTEXT: undefined }): support.cjs environment() deletes keys whose override value is undefined",
  [('C-203','yes',"assert.match(result.stdout, /ok \\d+ - doubles from one second and stops at five minutes/)")])
A(r,'operations.cjs',123,'no',"npm(args) -> ctx.run('npm', args, {}, checkout); support.cjs environment(): {...process.env, TZ, PORT, WORKER_INTERVAL_MS} minus DATA_FILE,NOTIFY_FILE,MAX_BODY_BYTES,LOG_REQUESTS,DUE_TIMES,DUE_TIMES_RECOVERY_FILE,NODE_OPTIONS,hours keys; no NODE_TEST_CONTEXT override here",
  [('C-96','no',"equal(suite.code, 0, suite.stdout + suite.stderr)")])
A(r,'operations.cjs',442,'yes',"ctx.run(..., { NODE_TEST_CONTEXT: undefined }): environment() deletes keys whose override value is undefined",
  [('C-274','yes',"const counts = /(?:#|ℹ) tests\\s+(\\d+)/.exec(result.stdout); assert.ok(counts && Number(counts[1]) > added.length, result.stdout)")])
I(r,'operations.cjs',430)
A(r,'scenarios.cjs',851,'yes',"ctx.run(..., { NODE_TEST_CONTEXT: undefined }): environment() deletes keys whose override value is undefined",
  [('U-21','yes',"assert.match(suite.stdout, /deadline|due times|prepar/i) (text match on test-name words in the child's output) after equal(suite.code, 0)")])

r='smoke-standin-sol-high'
DN_SS="project-clauses.cjs command(): env = {...process.env, ...extraEnv}; `delete env.NODE_TEST_CONTEXT;` before spawnSync"
A(r,'project-clauses.cjs',17,'yes',DN_SS+"; projectCoverage() helper",
  [(i,'yes',"assert.ok(cases.length, `npm test reported no node:test cases for ${probe}`) (cases from a custom reporter's ORDERS_CASE lines); assertsFixture: assert.ok(witnesses.size, ...)") for i in ['C-53','C-54','C-55']])
A(r,'project-clauses.cjs',78,'yes',DN_SS,[('C-56','yes',"assert.equal(status, 0, output); reportsCount(output, 'fail', 0)")])
A(r,'project-clauses.cjs',88,'yes',DN_SS,[('C-58','yes',"reportsCount(output, 'pass', 2); reportsCount(output, 'fail', 0)")])
I(r,'run-clause.cjs',21)

# ---- lens ----
r='p1L-stand-in-rules'
DN_L1="project.cjs run(): env = {...baseEnv(process.env), npm_config_update_notifier}; `delete env.NODE_TEST_CONTEXT;` (all calls go through run())"
A(r,'project.cjs',55,'yes',DN_L1+"; traceDiscoveredSuite()",
  [('C-78','yes',"records = traceRecords(child stdout); coverage checks over records of parseOrders calls made inside the child's tests"),
   ('C-79','yes',"records from the child's trace; assert.deepEqual(missing, [], 'Total cases absent from the discovered project tests')")])
A(r,'project.cjs',60,'yes',DN_L1+"; projectSuite()",
  [('C-80','yes',"assertExistingMeterChecks: assert.match(output, /^ok \\d+ - meter counts ticks and resets$/m)"),
   ('U-8','yes',"assertExistingMeterChecks(result.stdout)")])
A(r,'project.cjs',72,'yes',DN_L1,
  [('C-80','yes',"assert.ok(records.some(({ kind }) => kind === 'parse'), 'No discovered node:test case calls parseOrders')"),
   ('U-8','yes',"assert.ok(records.some(({ kind }) => kind === 'parse'), ...)")])
A(r,'project.cjs',161,'yes',DN_L1,[('C-77','yes',"assert.match(result.stdout, /^# Subtest: meter counts ticks and resets$/m)")])
I(r,'run.cjs',7)

r='p1L-ticket-assignment'
DN_L2="support.cjs environment(): {...process.env, ...{PORT,WORKER_INTERVAL_MS,DATA_FILE,NOTIFY_FILE,MAX_BODY_BYTES,LOG_REQUESTS,NODE_OPTIONS,NODE_TEST_CONTEXT: undefined}, npm_config_*}; spawn/spawnSync omit undefined env values (all calls pass env: environment(...))"
A(r,'journeys.cjs',336,'yes',DN_L2,[('U-11','yes',"assert.ok(names.length > 0); for (const name of names) assert.ok(run.stdout.includes(' - ' + name), name)")])
A(r,'journeys.cjs',338,'yes',DN_L2,[('U-11','yes',"const names = onlyNew.split('\\n').filter(line => /^ok \\d+ - /.test(line)); assert.ok(names.length > 0)")])
A(r,'operator.cjs',497,'yes',DN_L2+"; suite(t) helper",
  [('C-149','yes',"assert.match(npm.stdout, /# pass [1-9]\\d*/)"),
   ('C-150','yes',"for (const name of tests) assert.ok(npm.stdout.includes(' - ' + name), name) (tests non-empty asserted)"),
   ('C-151','no',"assert.equal(exit.code, 0, ...) for two concurrent suite runs; no output check")])
A(r,'operator.cjs',524,'yes',DN_L2,[('C-150','yes',"assert.ok(tests.length > 0) over `ok N -` lines of the child's output")])
A(r,'support.cjs',133,'yes',DN_L2+"; failingTestCommand() helper",
  [('U-11','yes',"assert.notEqual(code, 0); assert.match(run.stdout, /an intentional failing assertion/)"),
   ('C-150','yes',"assert.notEqual(code, 0); assert.match(run.stdout, /an intentional failing assertion/)")])

r='p1L-ticket-due-times'
DN_L3="support.cjs environment(): {...process.env} minus NODE_OPTIONS,PORT,DATA_FILE,NOTIFY_FILE,WORKER_INTERVAL_MS,MAX_BODY_BYTES,LOG_REQUESTS,DUE_TIMES,hours settings (not NODE_TEST_CONTEXT); nodeRun() passes env: environment(options.env)"
A(r,'readers.cjs',38,'no',DN_L3+"; originalSuite()",[('C-189','yes',"assert.match(result.stdout, /^# pass [1-9]\\d*/m)")])
A(r,'readers.cjs',46,'no',DN_L3+"; discoveredSuite()",
  [('C-190','yes',"assert.ok(events.length > 0, ...); assert.ok(newTests.length > 0, 'npm test did not discover any new node:test cases under test/') (events from a custom reporter)"),
   ('U-12','yes',"assert.ok(events.length > 0 ...); assert.ok(executed.some(({ file }) => file.endsWith(path.join('test', 'api.test.js'))))")])
A(r,'runtime.cjs',52,'no',DN_L3,[('C-75','yes',"assert.match(suite.stdout + suite.stderr, /Subtest:|✔|✖/)")])
A(r,'scenarios.cjs',336,'no',DN_L3,[('U-12','no',"assert.equal(run.code, 0, tail(...)) for this run (the same test's second npm run, via discoveredSuite, has evidence assertions)")])

r='p3L-ticket-due-times-a'
DN_L4="support.cjs command() passes env: env({...npmEnvironment, ...settings}); env() = {...process.env} minus PORT,DATA_FILE,NOTIFY_FILE,DUE_TIMES,LOG_REQUESTS,MAX_BODY_BYTES,WORKER_INTERVAL_MS,NODE_OPTIONS,hours policy keys (not NODE_TEST_CONTEXT)"
A(r,'operations.cjs',10,'no',DN_L4+"; npmTest() helper",
  [('C-169','yes',"two npm runs: assert.ok(sources.some(([, contents]) => includesTitle(contents)), 'npm test did not name a new case') over `ok N -` lines; second run: assert.match(failure.stdout + failure.stderr, /acceptance failing probe/)")])
A(r,'operations.cjs',335,'no',DN_L4,[('C-168','no',"success(command(['--test', ...cases], ...)) (exit status 0 only)")])
A(r,'scenarios.cjs',370,'no',DN_L4,[('U-11','yes',"assert.ok(cases.some(line => /due|deadline|overdue/i.test(line)), 'new due-time cases ran') over /^ok \\d+ - / lines")])
A(r,'scenarios.cjs',379,'no',DN_L4,[('U-11','yes',"assert.notEqual(failing.status, 0); assert.match(failing.stdout + failing.stderr, /maintainer sees a regression/)")])

r='p3L-ticket-due-times-b'
A(r,'release.cjs',17,'yes',"support.cjs run() -> flags(): env built from an explicit allow-list {PATH, TMPDIR, TZ, npm_config_*, PORT, WORKER_INTERVAL_MS, DATA_FILE, ...overrides}, not spread from process.env, so NODE_TEST_CONTEXT is absent from the child (no explicit delete of it)",
  [('C-194','yes',"legacyTests(): assert.ok(shipped.size > 0, 'the legacy run did not report its tests'); assert.ok(running.has(name), 'legacy test did not pass under npm test: ' + name)"),
   ('C-195','yes',"assert.ok(discovered.size > 0); assert.ok(discovered.has(name), 'new case did not run and pass: ' + name); failingTestExits: assert.match(failed.stdout + failed.stderr, /acceptance runner sentinel/)"),
   ('C-196','no',"const output = await npmTest(s, root, files); exit(output) (exit status only; later assertions read test sources)"),
   ('C-197','yes',"assert.ok([...testNames(result)].some(name => /(?:1\\.4\\.0|rollback|base release)/i.test(name)))"),
   ('U-16','yes',"assert.ok(names.some(name => /due|deadline/i.test(name))); legacyTests; failingTestExits")])

# ---- reworded ----
r='p1R-stand-in-rules'
DN_R1="project-tests.cjs runProjectTests(): env = {...process.env, NODE_OPTIONS, RATCHET_TEST_EVIDENCE}; `delete env.NODE_TEST_CONTEXT;` before spawn (all calls go through runProjectTests)"
A(r,'orders.cjs',247,'yes',DN_R1,[('C-26','yes',"assertCombinedRun: assert.ok(meterCases.length >= 2, 'npm test did not run both existing meter cases.') (observed set written by a preload inside the child); assertOrderCoverage")])
A(r,'orders.cjs',304,'yes',DN_R1,[('U-5','yes',"assertCombinedRun(...): meterCases.length >= 2 and assertOrderCoverage")])
A(r,'project-tests.cjs',61,'yes',DN_R1+"; findOrderCoverage() helper",[('C-25','yes',"missingOrderCoverage(directRun.observed).length === 0, else assertOrderCoverage: assert.deepEqual(missing, [], 'No project node:test case exercised ...')")])
A(r,'project-tests.cjs',65,'yes',DN_R1+"; findOrderCoverage() helper",[('C-25','yes',"assertOrderCoverage({ observed: union of both runs }): assert.deepEqual(missing, [], ...)")])

r='p1R-ticket-assignment'
DN_R2="entrypoints.cjs suite(): env = settings({NODE_OPTIONS reporter, npm_config_update_notifier}); `delete env.NODE_TEST_CONTEXT;` (every call goes through suite())"
EV_R2="suite() itself asserts rows.length > 0 ('no node:test results from ...') over `acceptance-result` lines from a custom reporter in the child"
A(r,'entrypoints.cjs',130,'yes',DN_R2+"; baseRun() helper",[(i,'yes',EV_R2) for i in ['C-41','C-42','C-43','U-9']])
A(r,'entrypoints.cjs',137,'yes',DN_R2+"; changedTests() helper",[(i,'yes',EV_R2+"; changedTests: assert.ok(cases.length > 0, 'the new test files did not register any node:test cases')") for i in ['C-42','C-43','U-9']])
A(r,'entrypoints.cjs',156,'yes',DN_R2,[('C-41','yes',EV_R2+"; assert.ok(originalTests.length > 0)")])
A(r,'entrypoints.cjs',181,'yes',DN_R2,[('C-43','yes',EV_R2)])
A(r,'entrypoints.cjs',189,'yes',DN_R2,[('U-9','yes',EV_R2)])

r='p1R-ticket-due-times'
DN_R3="harness.cjs environment(): {...process.env, PORT, WORKER_INTERVAL_MS, ...} then `delete env[key]` for a list that includes 'NODE_TEST_CONTEXT' (command() always passes env: environment(env))"
A(r,'operators.cjs',184,'yes',DN_R3+"; runDeadlineSuite() helper",
  [('C-29','yes',"verifyDeadlineTests: assert.ok(results(actual.stdout) > results(previous.stdout), 'npm test emitted no additional node:test results')"),
   ('U-8','yes',"same helper with verifyExisting: true; also verifyOriginalResults (assert.ok(expected.length > 0, ...))")])
A(r,'operators.cjs',185,'yes',DN_R3+"; runDeadlineSuite() helper (baseline checkout run)",
  [('C-29','yes',"assert.ok(results(actual.stdout) > results(previous.stdout), ...) counts result lines of this run"),
   ('U-8','yes',"same; verifyOriginalResults: assert.ok(expected.length > 0, 'could not read the baseline node:test results')")])
A(r,'operators.cjs',201,'yes',DN_R3,[('C-30','yes',"verifyOriginalResults(actual, previous): assert.ok(expected.length > 0, 'could not read the baseline node:test results'); assert.ok(index >= 0, 'preexisting test did not pass under npm test: ...')")])
A(r,'operators.cjs',201,'yes',DN_R3,[('C-30','yes',"assert.ok(expected.length > 0, 'could not read the baseline node:test results')")],n=1)

r='p1S-ticket-assignment-high'
DN_S1="misc.check.js cleanEnv(): {...process.env} minus every key starting with 'NODE_TEST'"
A(r,'misc.check.js',112,'yes',DN_S1,[('C-31','yes',"assert.match(`${run.stdout}${run.stderr}`, /(pass|passed)[ :]+\\d+|# pass \\d+|ℹ pass \\d+/i)")])
A(r,'misc.check.js',138,'yes',DN_S1,[('C-32','no',"assert.equal(list.status, 0, ...) only")])
I(r,'lib.js',6)

r='p1S-ticket-assignment-medium'
A(r,'misc.test.js',18,'no',"spawnSync has no env option (child inherits process.env, including NODE_TEST_CONTEXT)",[('C-21','no',"assert.equal(r.status, 0, r.stdout.slice(-2000)) only")])
A(r,'misc.test.js',27,'yes',"env: (({ NODE_TEST_CONTEXT, ...e }) => e)(process.env)",[('C-22','yes',"assert.equal(r.status, 0, ...); assert.match(r.stdout, /assign/i) (text match on test-name words in the spec reporter output)")])

r='p3R-ticket-due-times-a'
A(r,'operations.cjs',46,'yes',"harness.cjs launch(): env = {...process.env, ..., NODE_TEST_CONTEXT: undefined, ...}; `for (const key of Object.keys(env)) if (env[key] === undefined) delete env[key];` before spawn; npmTest() helper (args = scripts.test === 'node --test' ? ['test','--','--test-concurrency=3'] : ['test'])",
  [('C-2','yes',"assert.ok(result.events.length > 0, result.diagnostic || 'npm test did not run') (events from a custom reporter in the child)"),
   ('C-33','yes',"checkOriginalSuite: assert.ok(expected.length > 0, 'no stock tests reported'); assert.deepEqual(summarize(current.events, files), expected, ...)"),
   ('C-34','yes',"checkAddedSuite: assert.ok(tests.length > 0, 'npm test reported no added node:test cases under test/')"),
   ('U-8','yes',"checkOriginalSuite(world, result); checkAddedSuite(result)")],
  pos=r"world\.launch\('npm', args")

r='p3R-ticket-due-times-b'
A(r,'operators.cjs',208,'yes',"support.cjs environment(): {...process.env} with every name matching /^(?:PORT|DATA_FILE|...|NODE_OPTIONS|NODE_TEST_CONTEXT|NODE_V8_COVERAGE|RATCHET_.*)$/ deleted; launch() passes environment({...})",
  [('U-6','yes',"assertAddedRan: assert.ok(loaded.has(file), file + ' did not run in npm test'); assert.ok(passing.some(line => line.includes(title)), 'npm test did not report a passing result for ' + title); assertOriginalRan")])

r='q-base-1'
A(r,'assign.test.js',526,'yes',"env = { ...process.env, PORT: '', ACC_INNER: '1' }; `delete env.NODE_TEST_CONTEXT;` passed as env",
  [('C-21','yes',"const m = /(?:# |ℹ )tests (\\d+)/.exec(r.stdout); assert.ok(m && Number(m[1]) > 0)")])

r='q-base-2'
DN_QB2="misc.accept.js cleanEnv(): { ...process.env, PORT: '' } with `delete e.NODE_TEST_CONTEXT`"
A(r,'misc.accept.js',46,'yes',DN_QB2,[('C-23','yes',"assert.match(r.stdout, /pass 1[0-9][0-9]/)")])
A(r,'misc.accept.js',61,'yes',DN_QB2,[('C-24','yes',"assert.ok(/assign/i.test(r.stdout), 'npm test output includes assignment tests') (word match on test names; exit status also asserted)")])
A(r,'misc.accept.js',145,'yes',DN_QB2,[('U-5','yes',"assert.match(r.stdout, /pass 1[0-9][0-9]/)")])

r='q-plan-1'
A(r,'rest.spec.js',154,'no',"spawnSync has no env option (inherits process.env, including NODE_TEST_CONTEXT)",[('C-19','no',"assert.equal(r.status, 0, r.stdout.slice(-2000)) only")])
A(r,'rest.spec.js',169,'no',"spawnSync has no env option (inherits process.env, including NODE_TEST_CONTEXT)",[('C-20','yes',"assert.ok(/assign/i.test(r.stdout), 'npm test output names assignment tests') (word match on test names; exit status also asserted)")])

r='q-plan-2'
DN_QP2="lib.js cleanEnv(): { ...process.env, ...extra } minus every key starting with 'NODE_TEST' (and LOG_REQUESTS)"
A(r,'checks-misc.js',21,'yes',DN_QP2,[('C-21','yes',"assert.match(r.stdout, /fail 0/)")])
A(r,'checks-misc.js',35,'yes',DN_QP2,[('C-22','yes',"assert.match(r.stdout, /fail 0/); const total = Number(/tests (\\d+)/.exec(r.stdout)[1]); assert.ok(total > oldTotal, ...)")])
A(r,'checks-misc.js',39,'yes',DN_QP2,[('C-22','yes',"const oldTotal = Number(/tests (\\d+)/.exec(old.stdout)[1]); assert.ok(total > oldTotal, ...)")])

r='q-spec-1'
A(r,'assign.spec.js',634,'no',"spawnSync has no env option (inherits process.env, including NODE_TEST_CONTEXT)",[('C-20','no',"assert.equal(r.status, 0, r.stdout.slice(-2000)) only")])
DN_QS1="local tap() helper: spawnSync(args[0], args.slice(1), { ..., env: (() => { const e = { ...process.env }; delete e.NODE_TEST_CONTEXT; return e; })() })"
A(r,'assign.spec.js',645,'yes',DN_QS1,[('C-21','yes',"const count = out => Number(/^# tests (\\d+)/m.exec(out)[1]); assert.ok(count(full.stdout) > count(base.stdout), ...)")])
A(r,'assign.spec.js',643,'yes',DN_QS1,[('C-21','yes',"assert.ok(count(full.stdout) > count(base.stdout), `npm test ran ${count(full.stdout)} tests, ...`)")],pos=r"tap\(\['npm', 'test'")

r='q-spec-2'
A(r,'npmtest.acc.js',15,'yes',"env: { ...process.env, NODE_TEST_CONTEXT: undefined } (spawnSync omits undefined env values)",[('C-22','no',"assert.equal(r.status, 0, ...) only")])

# ---- parallel ----
r='b1-due-times-a'
A(r,'adapter.cjs',322,'yes',"adapter.cjs run() -> envFor(): {...process.env, ...ENV} then `delete env[name]` for a list that includes 'NODE_TEST_CONTEXT'; suite(cwd,{report}) helper",
  [('C-2','no',"suite(checkout) with no reporter: execFileSync exit status only (throws on non-zero); output ignored"),
   ('C-33','yes',"suiteRuns: assert.ok(expected.length > 0, 'the original test suite reports executed node:test cases') (from a custom reporter); assert.deepEqual(unmatched(expected, actual), [], ...)"),
   ('C-34','yes',"assert.ok(unmatched(actual, expected).length > 0, 'npm test did not execute a new passing node:test case under test/')"),
   ('U-8','yes',"suiteRuns + assertExistingPassed + assertNewTestsPassed")])
r='b1-due-times-b'
A(r,'adapter.cjs',363,'yes',"adapter.cjs env(): {...process.env, npm_config_*} then `delete result[key]` for a list that includes 'NODE_TEST_CONTEXT'; suite(old) helper",
  [('C-33','yes',"verifyOriginalTests: assert.ok(expected.length > 0, 'the reporter must observe original passing node:test cases')"),
   ('C-34','yes',"newDueTimeTests: assert.ok(newCases.length > 0, 'npm test must execute added node:test cases from test/')"),
   ('U-7','yes',"newDueTimeTests(h, original, current); assert.equal(current.run.exit.code, 0, ...)")])

r='bs-loop'
A(r,'structure.cjs',62,'yes',"projectTests(): env = {...process.env, NODE_V8_COVERAGE}; `delete env.NODE_OPTIONS; delete env.NODE_TEST_CONTEXT;` passed to command()",
  [('C-23','yes',"assertRuleCoverage: assert(project.discovered.length, 'No test files under test/ were executed') (from V8 coverage files of the child)"),
   ('C-24','yes',"assertRunner: assert(totals && Number(totals[1]) > 0, 'node --test did not report any passing tests')"),
   ('U-4','yes',"assertRunner(project); assertRuleCoverage(...)")])

r='bs-blind'
A(r,'adapter.cjs',313,'no',"runRuleTests(): env = { ...process.env } (plus RATCHET_RULES_FILE/RATCHET_TRACE_FILE when tracing), passed to childProcess(); nothing deleted",
  [('C-23','yes',"assert.ok(run.events.some(event => event.kind === 'node:test' && event.file.startsWith(testDirectory)), ...) (trace written by a preload inside the child)"),
   ('C-24','yes',"assert.ok(run.cases.length, 'node --test must discover actual cases under test/.')"),
   ('U-4','yes',"assert.ok(run.cases.length, ...); assert.ok(run.events.some(event => event.kind === 'node:test' && ...))")],
  pos=r"childProcess\(t, process\.execPath, args")

r='gb-beside'
A(r,'runtime.cjs',298,'yes',"env = { ...process.env, NODE_V8_COVERAGE }; `delete env.NODE_TEST_CONTEXT;` passed to h.child('npm', ['test'], { cwd, env })",
  [('C-100','yes',"assert.match(npm.output, /(?:#|ℹ)\\s*tests\\s+[1-9]\\d*\\b|# pass\\s+[1-9]\\d*\\b/); assert.ok([...checks.keys()].some(name => /^test[\\\\/]/.test(name)), 'npm test executed tests under test/')")])

r='gb-blind'
A(r,'adapter.cjs',346,'no',"npmRuleTests(): env: { ...process.env, NODE_V8_COVERAGE: coverage }; processHandle spawns with those options unchanged; nothing deleted",
  [('C-100','yes',"assert.match(result.stdout + result.stderr, /\\b(?:ok\\s+\\d+|pass\\s+[1-9]\\d*)\\b/i, 'npm test reports passing Node tests'); assert.ok(...file.startsWith('test/') && functions.length)"),
   ('U-1','yes',"same assertions via s.ruleTests()")])
