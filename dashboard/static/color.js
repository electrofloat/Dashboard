const defaultColor = "#161b1f";

window.addEventListener("load", startup, false);

function startup() {
  const colorPicker = document.querySelector("#color-picker");
  colorPicker.value = defaultColor;
  colorPicker.addEventListener("input", colorUpdate, false);
  colorPicker.select();

  document.querySelector("#title_input").addEventListener("input", titleUpdate, false);
  document.querySelector("#description_input").addEventListener("input", descriptionUpdate, false);
  document.querySelector("#icon_input").addEventListener("input", iconUpdate, false);
}

function colorUpdate(event) {
  const background = document.getElementById("background");
  const title = document.getElementById("title");
  const description = document.getElementById("description");
  const link = document.getElementById("link");
  const value = document.getElementById("value");
  const color = event.target.value;
  if (value) {
    value.textContent = color;
  }
  const r = parseInt(color.substr(1, 2), 16);
  const g = parseInt(color.substr(3, 2), 16);
  const b = parseInt(color.substr(5, 2), 16);
  // Same formula as CommonTile.get_foreground_color
  const luma = (0.212 * r + 0.701 * g + 0.087 * b) / 255;
  const foreground = luma > 0.5 ? "black" : "white";
  title.className = "titl " + foreground;
  description.className = "desc " + foreground;
  link.className = "link " + foreground;
  if (background) {
    background.style.backgroundColor = color;
  }
}

function titleUpdate(event) {
  document.getElementById("title").textContent = event.target.value;
}

function descriptionUpdate(event) {
  document.getElementById("description").textContent = event.target.value;
}

// Same resolution rules as CommonTile.get_icon
function iconUpdate(event) {
  const icon = document.getElementById("icon");
  const value = event.target.value;
  if (value.startsWith("di")) {
    icon.src = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/" + value.substr(3) + ".png";
  } else if (value.startsWith("http")) {
    icon.src = value;
  } else {
    icon.src = "/static/userdata/icons/" + value;
  }
}
