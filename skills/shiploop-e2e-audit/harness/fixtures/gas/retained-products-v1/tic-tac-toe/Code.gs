/**
 * Serve Index.html as a GAS web app. include() injects trusted HTML snippets
 * (JavaScript.html). Not deployed in this repository copy.
 */
function doGet() {
  return HtmlService.createTemplateFromFile('Index')
      .evaluate()
      .setTitle('Tic-Tac-Toe');
}

function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}
