javascript:(function() {
  var inputBox = document.getElementById("inputBox");
  if (inputBox == undefined) { 
  var htmlToInject = '<div style="background-color: rgba( 45,109,130, 1); color: white;  position: absolute; z-index: 1001; right: 10px; top: 10px; padding: 10px;">go to  <input type="text" id="inputBox" onkeydown="handleKeyPress(event)">  </div>';
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


  function wgs84_to_crs(x, y) {
    var data_proj =  viewer.scene.pointclouds[0].projection;
    proj4.defs("EPSG:3857","+proj=merc +a=6378137 +b=6378137 +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +wktext +no_defs +type=crs");
    /* TODO: add more CRSs */
    const sourceCRS = "+proj=longlat +datum=WGS84 +no_defs";
    const targetCRS = data_proj;

    const sourceProjection = proj4.Proj(sourceCRS);
    const targetProjection = proj4.Proj(targetCRS);

    const xy_proj = proj4.transform(sourceProjection, targetProjection, [x,y]);
    return xy_proj;
  }
  
  function goto_pasted(value) {
    console.log(value);
    var abz = value.split(',');
    var a = parseFloat(abz[0]);
    var b = parseFloat(abz[1]);
    var z = parseFloat(abz[2]);
    
    if (-180 < b && b < 180 && -90 < a && a < 90 ) { /* probably in WGS84 */
      var xy = wgs84_to_crs(b, a);
      var x = xy.x;
      var y = xy.y;
    }  else {
      var x = a;
      var y = b;
    }

  if (isNaN(z)) {
    var z = viewer.scene.view.position['z'] ;
  }
	viewer.scene.view.position.set(x, y, z);
}

window.goto_pasted = goto_pasted;

})();
