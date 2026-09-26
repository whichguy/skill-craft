function doGet() {
  return HtmlService.createTemplateFromFile('Page')
      .evaluate()
      .setTitle('Template fixture');
}

function include(name) {
  return HtmlService.createHtmlOutputFromFile(name).getContent();
}
