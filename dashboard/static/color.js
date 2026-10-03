let colorPicker;
const defaultColor = "#161b1f";

window.addEventListener("load", startup, false);

function startup() {
  colorPicker = document.querySelector("#color-picker");
  colorPicker.value = defaultColor;
  colorPicker.addEventListener("input", updateFirst, false);
  //colorPicker.addEventListener("change", updateAll, false);
  colorPicker.select();

  title_input = document.querySelector("#title_input");
  title_input.addEventListener("input", titleupdate, false);

  description_input = document.querySelector("#description_input");
  description_input.addEventListener("input", descriptionupdate, false);

  icon_input = document.querySelector("#icon_input");
  icon_input.addEventListener("input", iconupdate, false);

}
function updateFirst(event) {
  const p = document.getElementById("background");
  const title = document.getElementById("title");
  const description = document.getElementById("description");
  const link = document.getElementById("link");
  const value = document.getElementById("value");
  const color = event.target.value
  if (value) {
    value.textContent = color;
  }
  const r = parseInt(color.substr(1,2), 16)
  const g = parseInt(color.substr(3,2), 16)
  const b = parseInt(color.substr(5,2), 16)
    luma = (0.212 * r + 0.701 * g + 0.087 * b) / 255
    if (luma > 0.5) {
      title.className="titl black"
      description.className="desc black"
      link.className="link black"
    } else {
      title.className="titl white"
      description.className="desc white"
      link.className="link white"
    }
  if (p) {
    p.style.backgroundColor = event.target.value;
  }
}
function updateAll(event) {
  document.querySelectorAll("p").forEach((p) => {
    p.style.color = event.target.value;
  });
}

function titleupdate(event) {
  const title = document.getElementById("title");
  title.textContent = event.target.value
}

function descriptionupdate(event) {
  const description = document.getElementById("description");
  description.textContent = event.target.value
}


function iconupdate(event) {
  const icon = document.getElementById("icon")
  if (event.target.value.startsWith("di")) {
    url="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/"
    icon.src=url.concat(event.target.value.substr(3), ".png")
  } else if (event.target.value.startsWith("http")) {
    icon.src=event.target.value
  } else {
    url="/static/"
    icon.src=url.concat(event.target.value)
  }
}
