javascript:(function() {
  var inputBox = document.getElementById("inputBox");
  if (inputBox == undefined) {
  var htmlToInject = '<div style="background-color: yellow;  position: absolute; z-index: 1001; right: 100px; top: 10px; padding: 10px;">Go to  <input type="text" id="inputBox" onkeydown="handleKeyPress(event)">  </div>';
  var bodyElement = document.querySelector("#potree_render_area");
  var tempElement = document.createElement('div');
  tempElement.innerHTML = htmlToInject;
  var injectedElement = tempElement.firstChild;
  bodyElement.appendChild(injectedElement);}

    function handleKeyPress(event) {
      if (event.keyCode === 13) { /* Check if Enter key is pressed */
        var inputBox = document.getElementById("inputBox");
        text = inputBox.value;
        if (text == undefined) { 
          throw Error('input box not found') ;
        }
        goto_pasted(text);
      }
	}

  window.handleKeyPress = handleKeyPress;

  
  function goto_pasted(value) {
	/* TODO: convert text from latlong to EPSG. proj4js comes with potree */
  console.log(value);
  var xyz = value.split(',');
  var x = parseFloat(xyz[0]);
  var y = parseFloat(xyz[1]);
  var z = parseFloat(xyz[2]);
  console.log(z);
  
  if (isNaN(z)) {
  var z = viewer.scene.view.position['z'] ;
  }
	viewer.scene.view.position.set(x, y, z);
}

  window.goto_pasted = goto_pasted;
})();
