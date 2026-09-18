function doGet() {
  return HtmlService.createTemplateFromFile('Page').evaluate();
}

function include(name) {
  return HtmlService.createHtmlOutputFromFile(name).getContent();
}
