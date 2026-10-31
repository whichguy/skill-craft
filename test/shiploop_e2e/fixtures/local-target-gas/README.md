# discount-shop (Google Apps Script)

A Google Apps Script project (appsscript.json, V8) that serves a small pricing web app. Its server code is src/*.js, and
every file there shares one global scope, as Apps Script runs them. The code runs from the deployment, not from this
checkout: `node scripts/deploy.js` pushes the project to the deployment (a stand-in for `clasp push`; `LOCAL_TARGET`
names the deployment's folder), and the tests in test/ load the server files from the deployment, as requests to the web
app would. `npm test` pushes and then runs node:test.
