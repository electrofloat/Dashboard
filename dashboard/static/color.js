const defaultColor = "#161b1f";
const yamlKeywords = ["true", "false", "yes", "no", "on", "off", "null", "y", "n", "~"];

window.addEventListener("load", startup, false);

function startup() {
  const colorPicker = document.querySelector("#color-picker");
  colorPicker.value = defaultColor;
  colorPicker.addEventListener("input", colorUpdate, false);
  colorPicker.select();

  document.querySelector("#title_input").addEventListener("input", titleUpdate, false);
  document.querySelector("#description_input").addEventListener("input", descriptionUpdate, false);
  document.querySelector("#icon_input").addEventListener("input", iconUpdate, false);
  document.querySelector("#url_input").addEventListener("input", urlUpdate, false);
  document.querySelector("#copy").addEventListener("click", copyYaml, false);
  updateYaml();
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
  updateYaml();
}

function titleUpdate(event) {
  document.getElementById("title").textContent = event.target.value;
  updateYaml();
}

function descriptionUpdate(event) {
  document.getElementById("description").textContent = event.target.value;
  updateYaml();
}

// Same resolution rules as CommonTile.get_icon
function iconUpdate(event) {
  const icon = document.getElementById("icon");
  const value = event.target.value;
  icon.hidden = !value;
  if (!value) {
    icon.removeAttribute("src");
  } else if (value.startsWith("di")) {
    icon.src = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/" + value.substr(3) + ".png";
  } else if (value.startsWith("http")) {
    icon.src = value;
  } else {
    icon.src = "/static/userdata/icons/" + value;
  }
  updateYaml();
}

function urlUpdate(event) {
  const value = event.target.value.trim();
  if (/^https?:\/\//.test(value)) {
    document.getElementById("link").href = value;
  }
  updateYaml();
}

function yamlString(value) {
  const plain = /^[A-Za-z0-9][A-Za-z0-9 ._\/:-]*$/.test(value) &&
    !value.includes(": ") && !value.endsWith(":") && !value.endsWith(" ") &&
    !yamlKeywords.includes(value.toLowerCase()) && isNaN(Number(value));
  return plain ? value : JSON.stringify(value);
}

function updateYaml() {
  const field = id => document.getElementById(id).value.trim();
  const lines = ["- type: tile", "  title: " + yamlString(field("title_input") || "ExampleTitle")];
  if (field("description_input")) {
    lines.push("  description: " + yamlString(field("description_input")));
  }
  if (field("icon_input")) {
    lines.push("  icon: " + yamlString(field("icon_input")));
  }
  const color = document.getElementById("color-picker").value;
  if (color.toLowerCase() !== defaultColor) {
    lines.push("  background: " + JSON.stringify(color));
  }
  lines.push("  url: " + yamlString(field("url_input") || "https://app.example.org"));
  document.getElementById("yaml").textContent = lines.join("\n");
  document.getElementById("copy-status").textContent = "";
}

function copyYaml() {
  const text = document.getElementById("yaml").textContent;
  const status = document.getElementById("copy-status");
  const done = () => { status.textContent = "Copied"; };
  // The clipboard API is only available on https and localhost
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(done, () => copyBySelection(done));
  } else {
    copyBySelection(done);
  }
}

function copyBySelection(done) {
  const range = document.createRange();
  range.selectNodeContents(document.getElementById("yaml"));
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
  if (document.execCommand("copy")) {
    done();
  } else {
    document.getElementById("copy-status").textContent = "Press Ctrl+C to copy";
  }
}
