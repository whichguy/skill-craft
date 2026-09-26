/** Serves the Battleship page. */
function doGet() {
  return HtmlService.createHtmlOutputFromFile('index').setTitle('Battleship');
}
